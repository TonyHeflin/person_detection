#!/usr/bin/env python3
import json, time, os, threading, io
import discord
from discord.ext import commands
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import paramiko
from imageai.Detection import ObjectDetection
from PIL import Image, ImageDraw
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
config_file = 'config.json'

def load_config():
    with open(config_file, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

def update_config(key, new_value):
    config = load_config()
    config[key] = new_value
    save_config(config)

def callback(status_message):
    #print(status_message)
    logging.info(status_message)
    

# Initialize the Discord bot
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load initial configuration from local file
with open("config.json", "r") as f:
    config = json.load(f)

# Watch for changes in the local config file and reload it into the global config object
class ConfigWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("config.json"):
            with open("config.json", "r") as f:
                global config
                config = json.load(f)
                logging.info("Reloaded configuration from config.json")

observer = Observer()
observer.schedule(ConfigWatcher(), ".", recursive=False)
observer.start()

def do_detection(file_name, buf):
    image = Image.open(buf)
    image.seek(0)

    detector = ObjectDetection()
    detector.setModelTypeAsYOLOv3()
    detector.setModelPath(config['detection_model'])
    detector.loadModel()
    detections = detector.detectObjectsFromImage(input_image=image, output_image_path='output.jpg', minimum_percentage_probability=config['detection_threshold'])

    # Draw bounding boxes around the detected objects
    draw = ImageDraw.Draw(image)
    for detection in detections:
        if detection["name"] == "person":
            name = detection["name"]
            box = detection["box_points"]
            draw.rectangle([(box[0], box[1]), (box[2], box[3])], outline="red", width=3)
            draw.text((box[0], box[1]-20), name, fill="red")
    
    #Convert image to buffer to send to discord
    img_io = io.BytesIO()
    image.save(img_io, 'JPEG', quality=100)
    img_io.seek(0)

    # Check if a person is detected
    person_detected = False
    for detection in detections:
        if detection["name"] == "person":
            logging.info('Motion: '+file_name)
            files = {"file": ("image.png", img_io)}
            data = {
                'content': "Motion: "+os.path.basename(file_name),
                'username': 'ImageAI Bot',
                }
            
            # Call the callback function if it was provided
            if callback is not None:
                callback(f"Discord message sent with image: {file_name}")

            # Send POST request to the webhook URL with the payload
            response = requests.post(config['discord_webhook'], files=files, data=data)
        else:
            logging.info('No Motion: '+file_name)
        break

# Check SFTP remote folder for image files on a different interval
def check_sftp_folder():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config["sftp_host"], port=config["sftp_port"], username=config["sftp_username"], password=config["sftp_password"])
    sftp = ssh.open_sftp()
    sftp.chdir(config["sftp_remote_path"])
    while True:
        if True:
            files = sftp.listdir()
            for file_name in files:
                if file_name.endswith(".jpg"):
                    logging.info('Found File: '+file_name)
                    # Test enabled in config
                    cam = next((camera for camera in config['cameras'] if camera['name'] == file_name.split('-')[0]), None)

                    # Check if the camera was found and is enabled
                    if cam is not None and cam['enabled']:
                        with io.BytesIO() as buf:
                            sftp.getfo(file_name, buf)
                            buf.seek(0)  # Reset buffer position to start
                            do_detection(file_name,buf)
                    else:
                        pass
                    # Delete remote file
                    sftp.remove(file_name)
        time.sleep(config["sftp_check_interval"])
        
# Start the SFTP folder check in a separate thread
sftp_thread = threading.Thread(target=check_sftp_folder)
sftp_thread.start()

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')

@bot.command()
async def delete(ctx, num=10):
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("This command can only be used in a text channel.")
        return
    num = min(num, 99)
    await ctx.channel.purge(limit=num)

@bot.command()
async def camera(ctx, *args):
    if len(args) == 0:
        await ctx.send("Usage: !camera status | camera_name [on/off]")
        return
    elif args[0] == "status":
        camera_statuses = [camera["name"] + ": " + str(camera["enabled"]) for camera in config["cameras"]]
        await ctx.send("Camera statuses:\n" + "\n".join(camera_statuses))
    else:
        camera_name = args[0]
        for camera in config["cameras"]:
            if camera["name"] == camera_name:
                if len(args) == 1:
                    await ctx.send("Camera " + camera_name + " is " + str(camera["enabled"]))
                else:
                    if args[1].lower() == "on":
                        camera["enabled"] = True
                        await ctx.send("Camera " + camera_name + " is now on")
                    elif args[1].lower() == "off":
                        camera["enabled"] = False
                        await ctx.send("Camera " + camera_name + " is now off")
                    else:
                        await ctx.send("Invalid status: " + args[1])
                save_config(config)
                return
        await ctx.send("Invalid camera: " + camera_name)

@bot.command()
async def update(ctx, key, *value):
    value = ' '.join(value)
    update_config(key, value)
    await ctx.send(f"Config updated: {key} = {value}")

# Run the bot
bot.run(config['discord_token'])

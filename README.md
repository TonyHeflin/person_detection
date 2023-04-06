# Pytorch Person Detection for Surviellance System

This is something I threw together. It is probably not the most effecient way to acom[plish tthe task but it works. 
There are bugs, uncaught exceptions and the possibility to open a space/time rift and destroy the universe. Use at your own risk.


## Details
This bot is designed to monitor a SFTP folder for image files and detect if a person is present in the image using ImageAI. If a person is detected, the bot sends a message with the image to a specified Discord channel. The bot also allows for the deletion of a specified number of messages in a text channel and the enabling/disabling of cameras.

To use the bot, the user must first create a config.json file containing the necessary information for the bot to function properly. This includes Discord bot token, webhook URL, SFTP server details, camera information, and detection model and threshold.

The bot has two additional commands: !delete and !camera. !delete can be used to delete a specified number of messages in a text channel, and !camera can be used to check the status of cameras or enable/disable specific cameras.

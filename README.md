## YiHack - Telegram bot

Inspired by: https://github.com/erer2001/Yi-Home_Telegram_Bot_Interface

- Received notification when a new motion is detected.
- Request a realtime snapshot.
- Download recorded video from the camera.

### Requirements
YiHome camera with one of the following custom firmware installed
- yi-hack-MStar - https://github.com/roleoroleo/yi-hack-MStar
- yi-hack-Allwinner - https://github.com/roleoroleo/yi-hack-Allwinner
- yi-hack-Allwinner-v2 - https://github.com/roleoroleo/yi-hack-Allwinner-v2
- yi-hack-v5 - https://github.com/alienatedsec/yi-hack-v5


Snapshot and MQTT futures must be enable.

### How to use
1. Install all the python requirements `pip install requirements`
2. Create a bot token and retrive your chat id (https://telegram.me/BotFather)
3. Copy settings.json.dist to settings.json and populate with your custom values (if your camera doesn't have a username or password you should remove the key from the json)
4. Run the script `python main.py`

Enjoy your bot!
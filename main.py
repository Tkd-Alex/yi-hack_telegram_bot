import asyncio
import json
import logging
import os
import re
import threading

import aiomqtt
from telegram import Bot, InputMediaVideo, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from YICamera import YICamera

for log_name in [
    "httpx",
]:
    logging.getLogger(log_name).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] [%(name)s] - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )
)

root_logger.addHandler(stream_handler)

# Global variable
SETTINGS = json.load(open(os.path.join(os.getcwd(), "settings.json"), encoding="utf-8"))
CAMERAS = {}


def is_authorized(chat_id: str) -> bool:
    return str(chat_id) in [
        str(_id) for _id in SETTINGS.get("telegram", {}).get("chat_ids", [])
    ]


async def callback_hello(update: Update, _) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    await update.message.reply_text(
        "<b>Allowed commands:</b>\n\n"
        + "\n".join(
            [
                f"- {c}"
                for c in [
                    "/cameras",
                    "/video",
                    "/snapshot",
                    "/eventsdir",
                    "/eventsfile",
                    "/last_video",
                ]
            ]
        ),
        parse_mode=ParseMode.HTML,
    )


async def callback_cameras(update: Update, _) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    await update.message.reply_text(
        "<b>Avaiable cameras:</b>\n\n"
        + "\n".join([f"- <code>{n}</code>" for n in CAMERAS]),
        parse_mode=ParseMode.HTML,
    )


async def callback_snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    if len(context.args) > 0:
        camera_name = context.args[0]
        if camera_name not in CAMERAS:
            await update.effective_message.reply_text(
                f"Camera: <code>{camera_name}</code> doesn't exist",
                parse_mode=ParseMode.HTML,
            )
        else:
            wait_message = await update.effective_message.reply_text("Please wait...")
            photo = CAMERAS[camera_name]["camera"].snapshot(res="hight", watermark="no")
            await update.message.reply_photo(photo, quote=True)
            await wait_message.delete()
    else:
        await update.effective_message.reply_text("Usage: snapshot <camera_name>")


async def callback_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    if len(context.args) > 1:
        camera_name = context.args[0]
        path = context.args[1]
        if camera_name not in CAMERAS:
            await update.effective_message.reply_text(
                f"Camera: <code>{camera_name}</code> doesn't exist",
                parse_mode=ParseMode.HTML,
            )
        else:
            wait_message = await update.effective_message.reply_text("Please wait...")
            video = CAMERAS[camera_name]["camera"].get_video(path)
            await update.message.reply_video(
                video,
                caption=f"<code>{path}</code>",
                parse_mode=ParseMode.HTML,
                quote=True,
            )
            await wait_message.delete()
    else:
        await update.effective_message.reply_text("Usage: video <camera_name> <path>")


async def callback_eventsfile(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    if len(context.args) > 1:
        camera_name = context.args[0]
        dirname = context.args[1]
        if camera_name not in CAMERAS:
            await update.effective_message.reply_text(
                f"Camera: <code>{camera_name}</code> doesn't exist",
                parse_mode=ParseMode.HTML,
            )
        else:
            wait_message = await update.effective_message.reply_text("Please wait...")
            eventsfile = CAMERAS[camera_name]["camera"].eventsfile(dirname)
            await update.message.reply_text(
                f"<b>Events eventsfile for: {eventsfile['date']}</b>\n\n"
                + "\n".join(
                    [
                        f'- {n["time"]}\n  {n["filename"]}\n  <code>{dirname}/{n["filename"]}</code>'
                        for n in eventsfile["records"][:20]
                    ]
                ),
                parse_mode=ParseMode.HTML,
            )
            await wait_message.delete()
    else:
        await update.effective_message.reply_text(
            "Usage: eventsfile <camera_name> <dirname>"
        )


async def callback_eventsdir(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    if len(context.args) > 0:
        camera_name = context.args[0]
        if camera_name not in CAMERAS:
            await update.effective_message.reply_text(
                f"Camera: <code>{camera_name}</code> doesn't exist",
                parse_mode=ParseMode.HTML,
            )
        else:
            # {{ "datetime": "Date: 2024-12-12 Time: 12:00", "dirname": "2024Y12M12D12H" }}
            wait_message = await update.effective_message.reply_text("Please wait...")
            eventsdir = CAMERAS[camera_name]["camera"].eventsdir()
            await update.message.reply_text(
                "<b>Events dir:</b>\n\n"
                + "\n".join(
                    [
                        f'- {n["datetime"]}\n  <code>{n["dirname"]}</code>'
                        for n in eventsdir[:20]
                    ]
                ),
                parse_mode=ParseMode.HTML,
            )
            await wait_message.delete()
    else:
        await update.effective_message.reply_text("Usage: eventsdir <camera_name>")


async def callback_last_video(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if is_authorized(update.message.from_user.id) is False:
        return

    if len(context.args) > 0:
        camera_name = context.args[0]
        if camera_name not in CAMERAS:
            await update.effective_message.reply_text(
                f"Camera: <code>{camera_name}</code> doesn't exist",
                parse_mode=ParseMode.HTML,
            )
        else:
            wait_message = await update.effective_message.reply_text("Please wait...")

            eventsdir = CAMERAS[camera_name]["camera"].eventsdir()
            last_event = eventsdir[0] if len(eventsdir) > 0 else None
            if last_event is not None:
                eventsfile = CAMERAS[camera_name]["camera"].eventsfile(
                    last_event["dirname"]
                )
                eventsfile = eventsfile.get("records", [])
                last_file = eventsfile[0] if len(eventsfile) > 0 else None
                if last_file is not None:
                    path = f"{last_event['dirname']}/{last_file['filename']}"
                    video = CAMERAS[camera_name]["camera"].get_video(path)
                    await update.message.reply_video(
                        video,
                        caption=f"<code>{path}</code>",
                        parse_mode=ParseMode.HTML,
                        quote=True,
                    )
                else:
                    await update.message.reply_text(
                        f"Last file for  <code>{camera_name}</code> not found",
                        parse_mode=ParseMode.HTML,
                    )
            else:
                await update.message.reply_text(
                    f"Last event for  <code>{camera_name}</code> not found",
                    parse_mode=ParseMode.HTML,
                )

            await wait_message.delete()
    else:
        await update.effective_message.reply_text("Usage: last_video <camera_name>")


async def fetch_motion_files(camera: YICamera, motion_data: dict):
    async with Bot(SETTINGS["telegram"]["bot_token"]) as bot:
        logger.info("Motion data is: %s", motion_data)
        files = motion_data.get("files", [])
        files = files[:4]  # list(set(files[:3] + files[-3:]))
        for chat_id in SETTINGS["telegram"]["chat_ids"]:
            message = await bot.send_message(
                chat_id,
                f"<b>Motion end</b>\n- Start: <code>{motion_data['start']}</code>\n- End: <code>{motion_data['end']}</code>\nFetching {len(files)} videos, please wait...",
                parse_mode=ParseMode.HTML,
            )
            motion_videos = [
                InputMediaVideo(
                    camera.get_video(fname),
                    caption=f"<code>{fname}</code>",
                    parse_mode=ParseMode.HTML,
                )
                for fname in files
            ]
            await message.reply_media_group(motion_videos, quote=True)


async def mqtt_subscribe(camera: YICamera):
    async with aiomqtt.Client(
        camera.mqtt_conf["MQTT_IP"],
        port=int(camera.mqtt_conf["MQTT_PORT"]),
        username=camera.mqtt_conf["MQTT_USER"],
        password=camera.mqtt_conf["MQTT_PASSWORD"],
    ) as client:
        await client.subscribe(f"{camera.mqtt_conf['MQTT_PREFIX']}/#")
        logger.info("Subscibed to: %s/#", camera.mqtt_conf["MQTT_PREFIX"])

        async for message in client.messages:
            logger.info(
                "Received message: %s, topic: %s, with QoS: %d",
                str(message.payload)[:150],
                message.topic.value,
                message.qos,
            )

            if re.match(r"yicam_[a-z]+/motion_files$", message.topic.value) is not None:
                motion_data = json.loads(message.payload.decode("utf-8"))
                threading.Thread(
                    target=asyncio.run,
                    args=(fetch_motion_files(camera, motion_data),),
                    daemon=False,
                ).start()

            elif (
                re.match(r"yicam_[a-z]+/motion_detection_image$", message.topic.value)
                is not None
            ):
                async with Bot(SETTINGS["telegram"]["bot_token"]) as bot:
                    for chat_id in SETTINGS["telegram"]["chat_ids"]:
                        await bot.send_photo(
                            chat_id, message.payload, caption="Motion detected!"
                        )


if __name__ == "__main__":
    for camera_setting in SETTINGS.get("cameras", []):
        c = YICamera(**camera_setting)
        t = threading.Thread(
            target=asyncio.run, args=(mqtt_subscribe(c),), daemon=False
        )

        if c.mqtt_enabled is True:
            t.start()

        CAMERAS[camera_setting["name"]] = {"camera": c, "mqtt_t": t}

    app = ApplicationBuilder().token(SETTINGS["telegram"]["bot_token"]).build()

    app.add_handler(CommandHandler(["help", "start"], callback_hello))
    app.add_handler(CommandHandler("cameras", callback_cameras))
    app.add_handler(CommandHandler("video", callback_video))
    app.add_handler(CommandHandler("snapshot", callback_snapshot))
    app.add_handler(CommandHandler("eventsdir", callback_eventsdir))
    app.add_handler(CommandHandler("eventsfile", callback_eventsfile))
    app.add_handler(CommandHandler("last_video", callback_last_video))
    app.run_polling()

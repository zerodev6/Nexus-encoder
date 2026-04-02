"""
Executes a queued encode task end-to-end:
  download → encode → upload → cleanup
"""

import asyncio
import os
import time
import logging
from pathlib import Path

from pyrogram import Client
from pyrogram.types import Message

from config import Config
from bot.database.mongo import get_user
from bot.utils.ffmpeg_utils import encode_video, take_screenshot
from bot.utils.transfer import download_media, upload_video, upload_document, download_url

logger = logging.getLogger("JobRunner")


async def run_task(bot: Client, userbot: Client | None, task: dict):
    chat_id     = task["chat_id"]
    user_id     = task["user_id"]
    source_type = task.get("source", "telegram")   # telegram | url | gdrive
    status_msg_id = task.get("status_msg_id")

    user_doc = await get_user(user_id)
    settings = user_doc.get("settings", {})

    # ── Retrieve status message ───────────────────────────────
    try:
        status_msg = await bot.get_messages(chat_id, status_msg_id)
    except Exception:
        status_msg = await bot.send_message(chat_id, "⚙️ Processing your file…")

    async def edit(text: str):
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass

    # ── Download ──────────────────────────────────────────────
    await edit("⬇️ <b>Downloading…</b>")
    dl_dir = Config.DOWNLOAD_DIR

    if source_type == "telegram":
        src_msg_id = task["src_msg_id"]
        src_msg = await bot.get_messages(chat_id, src_msg_id)
        local_path = await download_media(bot, src_msg, dl_dir, status_msg)

    elif source_type == "url":
        local_path = await download_url(task["url"], dl_dir, status_msg)

    elif source_type == "gdrive":
        from bot.utils.gdrive import download_gdrive
        local_path = await download_gdrive(task["url"], dl_dir, status_msg)

    else:
        await edit("❌ Unknown source type.")
        return

    if not local_path or not os.path.exists(local_path):
        await edit("❌ Download failed.")
        return

    # ── Encode ────────────────────────────────────────────────
    await edit("🎬 <b>Encoding…</b>")

    subtitle_path = task.get("subtitle_path")

    async def enc_progress(pct: float):
        from bot.utils.transfer import make_progress_text
        text = make_progress_text("🎬 Encoding", pct)
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass

    encoded = await encode_video(
        inp=local_path,
        out_dir=Config.ENCODE_DIR,
        settings=settings,
        subtitle_path=subtitle_path,
        progress_cb=enc_progress,
    )

    if not encoded:
        await edit("❌ Encoding failed. Check FFmpeg logs.")
        _cleanup(local_path)
        return

    # ── Custom filename ────────────────────────────────────────
    fname_template = settings.get("custom_fname", "")
    if fname_template:
        new_name = fname_template.replace("{original}", Path(local_path).stem)
        new_path = os.path.join(Config.ENCODE_DIR, new_name + Path(encoded).suffix)
        os.rename(encoded, new_path)
        encoded = new_path

    # ── Caption ────────────────────────────────────────────────
    caption = task.get("caption", Path(encoded).name)
    caption += f"\n\n<i>Encoded by @{Config.BOT_USERNAME}</i>"

    # ── Thumbnail ─────────────────────────────────────────────
    thumb = settings.get("thumbnail")  # could be a local path cached earlier

    # ── Upload ────────────────────────────────────────────────
    await edit("⬆️ <b>Uploading…</b>")

    send_as_doc = task.get("send_as_doc", False)
    uploader = userbot if userbot else bot

    if send_as_doc:
        await upload_document(uploader, chat_id, encoded, caption, status_msg)
    else:
        await upload_video(uploader, chat_id, encoded, caption, thumb, status_msg, reply_to=status_msg_id)

    await edit("✅ <b>Done!</b> File sent above.")

    # ── Cleanup ───────────────────────────────────────────────
    _cleanup(local_path)
    _cleanup(encoded)


def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

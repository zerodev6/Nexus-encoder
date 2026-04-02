"""
Subtitle attachment plugin.
Reply to a .ass or .srt file with /addsub, then reply to a video with /dl
and the subtitle will be applied per the sub_mode setting.
"""

import os
from pyrogram import Client, filters
from pyrogram.types import Message

from config import Config
from bot.utils.guards import require_subscription

# user_id -> local subtitle path
_sub_cache: dict[int, str] = {}


@Client.on_message(filters.command("addsub") & filters.private)
@require_subscription
async def addsub_handler(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.document:
        await message.reply("↩️ Reply to a subtitle file (.ass / .srt) with /addsub")
        return

    fname = target.document.file_name or ""
    if not (fname.endswith(".ass") or fname.endswith(".srt")):
        await message.reply("❌ Only .ass and .srt subtitles are supported.")
        return

    prog = await message.reply("⬇️ Downloading subtitle…")
    path = await client.download_media(target, file_name=Config.DOWNLOAD_DIR + "/")
    if not path:
        await prog.edit_text("❌ Failed to download subtitle.")
        return

    uid = message.from_user.id
    # Clean up old subtitle
    old = _sub_cache.pop(uid, None)
    if old and os.path.exists(old):
        os.remove(old)

    _sub_cache[uid] = path
    await prog.edit_text(
        f"✅ Subtitle <b>{fname}</b> attached!\n"
        "Now use /dl on your video to encode with this subtitle.\n"
        "Sub mode: set via /settings → Subs"
    )


@Client.on_message(filters.command("clearsub") & filters.private)
async def clearsub_handler(client: Client, message: Message):
    uid = message.from_user.id
    path = _sub_cache.pop(uid, None)
    if path and os.path.exists(path):
        os.remove(path)
    await message.reply("🗑 Subtitle cache cleared.")


def get_user_subtitle(user_id: int) -> str | None:
    return _sub_cache.get(user_id)

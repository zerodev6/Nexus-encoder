"""
Metadata plugin — edit title, author, language, comment for a video.
Uses pending-state pattern for multi-step input.
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

from config import Config
from bot.utils.guards import require_subscription
from bot.utils.ffmpeg_utils import set_metadata
from bot.utils.transfer import ProgressTracker, upload_video
import os

# user_id -> {field: value, ...}
_meta_state: dict[int, dict] = {}
# user_id -> local path of video to tag
_meta_file: dict[int, str] = {}

META_FIELDS = ["title", "artist", "comment", "language", "year"]


@Client.on_message(filters.command("setmeta") & filters.private)
@require_subscription
async def setmeta_cmd(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        await message.reply("↩️ Reply to a video/file with /setmeta")
        return

    prog = await message.reply("⬇️ Downloading for metadata edit…")
    path = await client.download_media(target, file_name=Config.DOWNLOAD_DIR + "/")
    if not path:
        await prog.edit_text("❌ Download failed.")
        return

    uid = message.from_user.id
    _meta_file[uid] = path
    _meta_state[uid] = {}

    kb = _meta_kb(uid)
    await prog.edit_text(
        "✏️ <b>Metadata Editor</b>\nTap a field to edit it:",
        reply_markup=kb,
    )


def _meta_kb(uid: int) -> InlineKeyboardMarkup:
    state = _meta_state.get(uid, {})
    rows = []
    for f in META_FIELDS:
        val = state.get(f, "")
        rows.append([Btn(f"✏️ {f.capitalize()}: {val or '(empty)'}", f"meta_edit_{f}")])
    rows.append([Btn("✅ Apply & Upload", "meta_apply"), Btn("❌ Cancel", "meta_cancel")])
    return InlineKeyboardMarkup(rows)


# Pending meta field input
_pending_meta_field: dict[int, str] = {}


@Client.on_callback_query(filters.regex(r"^meta_edit_(.+)$"))
async def meta_edit_field(client: Client, cb):
    uid = cb.from_user.id
    field = cb.matches[0].group(1)
    _pending_meta_field[uid] = field
    await cb.message.edit_text(f"✏️ Send the new value for <b>{field}</b>:")
    await cb.answer()


@Client.on_message(filters.private & ~filters.command([]))
async def meta_input_handler(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in _pending_meta_field:
        return False
    field = _pending_meta_field.pop(uid)
    _meta_state.setdefault(uid, {})[field] = message.text.strip()
    kb = _meta_kb(uid)
    await message.reply("✅ Updated! Tap another field or Apply.", reply_markup=kb)
    return True


@Client.on_callback_query(filters.regex("^meta_apply$"))
async def meta_apply(client: Client, cb):
    uid = cb.from_user.id
    if uid not in _meta_file:
        await cb.answer("Session expired.")
        return

    path = _meta_file.pop(uid)
    meta = _meta_state.pop(uid, {})

    from pathlib import Path
    out = path + "_tagged" + Path(path).suffix
    prog_msg = await cb.message.edit_text("🔄 Applying metadata…")

    ok = await set_metadata(path, out, meta)
    if not ok:
        await prog_msg.edit_text("❌ Metadata edit failed.")
        return

    await upload_video(client, cb.message.chat.id, out,
                       caption="✏️ Metadata edited", thumb=None, progress_msg=prog_msg)
    os.remove(path)
    os.remove(out)
    await cb.answer()


@Client.on_callback_query(filters.regex("^meta_cancel$"))
async def meta_cancel(client: Client, cb):
    uid = cb.from_user.id
    path = _meta_file.pop(uid, None)
    _meta_state.pop(uid, None)
    if path and os.path.exists(path):
        os.remove(path)
    await cb.message.edit_text("🛑 Metadata editing cancelled.")
    await cb.answer()

"""
Upload & encode plugin.
/dl  — encode a Telegram media file (reply or send)
/ddl — encode from direct URL
/gdl — encode from Google Drive URL
"""

import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

from config import Config
from bot.database.mongo import add_to_queue, get_user
from bot.utils.guards import require_subscription, is_admin
from bot.utils.keyboards import kb_upload_options


# ── /dl ───────────────────────────────────────────────────────
@Client.on_message(filters.command("dl") & filters.private)
@require_subscription
async def dl_handler(client: Client, message: Message):
    target = message.reply_to_message or message
    if not target or not target.media:
        await message.reply("↩️ Reply to a video/file with <code>/dl</code> to encode it.")
        return

    uid = message.from_user.id
    status_msg = await message.reply("⏳ Adding to queue…")
    priority = 1 if is_admin(uid) else 0

    caption = target.caption or (target.video.file_name if target.video else "")
    task = {
        "user_id":      uid,
        "chat_id":      message.chat.id,
        "source":       "telegram",
        "src_msg_id":   target.id,
        "status_msg_id": status_msg.id,
        "caption":      caption,
        "priority":     priority,
        "send_as_doc":  False,
    }
    tid = await add_to_queue(task)
    await status_msg.edit_text(
        f"✅ <b>Added to queue!</b>\nTask ID: <code>{tid}</code>\n"
        f"Your file will be processed shortly.",
        reply_markup=InlineKeyboardMarkup([[Btn("❌ Cancel", f"cancel_{tid}")]]),
    )


# ── /ddl ──────────────────────────────────────────────────────
@Client.on_message(filters.command("ddl") & filters.private)
@require_subscription
async def ddl_handler(client: Client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Usage: <code>/ddl https://example.com/video.mkv</code>")
        return

    url = parts[1].strip()
    uid = message.from_user.id
    status_msg = await message.reply("⏳ Adding to queue…")
    priority = 1 if is_admin(uid) else 0

    task = {
        "user_id":      uid,
        "chat_id":      message.chat.id,
        "source":       "url",
        "url":          url,
        "status_msg_id": status_msg.id,
        "caption":      url.split("/")[-1],
        "priority":     priority,
        "send_as_doc":  False,
    }
    tid = await add_to_queue(task)
    await status_msg.edit_text(
        f"✅ <b>Queued URL download!</b>\nTask ID: <code>{tid}</code>",
        reply_markup=InlineKeyboardMarkup([[Btn("❌ Cancel", f"cancel_{tid}")]]),
    )


# ── /gdl ──────────────────────────────────────────────────────
@Client.on_message(filters.command("gdl") & filters.private)
@require_subscription
async def gdl_handler(client: Client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Usage: <code>/gdl https://drive.google.com/...</code>")
        return

    url = parts[1].strip()
    if "drive.google.com" not in url:
        await message.reply("❌ That doesn't look like a Google Drive URL.")
        return

    uid = message.from_user.id
    status_msg = await message.reply("⏳ Adding to queue…")
    priority = 1 if is_admin(uid) else 0

    task = {
        "user_id":      uid,
        "chat_id":      message.chat.id,
        "source":       "gdrive",
        "url":          url,
        "status_msg_id": status_msg.id,
        "caption":      "GDrive file",
        "priority":     priority,
        "send_as_doc":  False,
    }
    tid = await add_to_queue(task)
    await status_msg.edit_text(
        f"✅ <b>Queued GDrive download!</b>\nTask ID: <code>{tid}</code>",
        reply_markup=InlineKeyboardMarkup([[Btn("❌ Cancel", f"cancel_{tid}")]]),
    )


# ── Cancel task callback ──────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^cancel_(.+)$"))
async def cancel_task_cb(client: Client, cb):
    task_id = cb.matches[0].group(1)
    from bot.database.mongo import cancel_task
    from bot.utils.scheduler import get_cancel_flag
    get_cancel_flag(task_id).set()
    await cancel_task(task_id)
    await cb.message.edit_text(f"🛑 Task <code>{task_id}</code> cancelled.")
    await cb.answer("Cancelled.")


# ── /queue command ────────────────────────────────────────────
@Client.on_message(filters.command("queue") & filters.private)
async def queue_status(client: Client, message: Message):
    from bot.database.mongo import queue_stats
    stats = await queue_stats()
    text = (
        "📋 <b>Queue Status</b>\n\n"
        f"⏳ Pending:    <b>{stats.get('pending', 0)}</b>\n"
        f"⚙️ Processing: <b>{stats.get('processing', 0)}</b>\n"
        f"✅ Done:       <b>{stats.get('done', 0)}</b>\n"
        f"❌ Failed:     <b>{stats.get('failed', 0)}</b>\n"
        f"🛑 Cancelled:  <b>{stats.get('cancelled', 0)}</b>"
    )
    await message.reply(text)

"""
Batch processing plugin.
/batch_start → collect files → /batch_end → enqueue all
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from bot.database.mongo import add_to_queue
from bot.utils.guards import require_subscription, is_admin

# user_id -> list of message ids
_batch_sessions: dict[int, list] = {}


@Client.on_message(filters.command("batch_start") & filters.private)
@require_subscription
async def batch_start(client: Client, message: Message):
    uid = message.from_user.id
    _batch_sessions[uid] = []
    await message.reply(
        "📦 <b>Batch mode started!</b>\n"
        "Now forward or send the files you want to encode.\n"
        "When done, send /batch_end\n"
        "Send /batch_cancel to abort."
    )


@Client.on_message(filters.private & ~filters.command([]))
async def batch_collect(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in _batch_sessions:
        return False
    if message.media:
        _batch_sessions[uid].append(message.id)
        await message.reply(
            f"➕ File added ({len(_batch_sessions[uid])} total). "
            "Send more or /batch_end to process."
        )
    return True


@Client.on_message(filters.command("batch_end") & filters.private)
async def batch_end(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in _batch_sessions or not _batch_sessions[uid]:
        await message.reply("❌ No batch session active or no files collected.")
        return

    msg_ids = _batch_sessions.pop(uid)
    priority = 1 if is_admin(uid) else 0
    chat_id = message.chat.id
    status_msg = await message.reply(f"⏳ Queuing {len(msg_ids)} files…")

    task_ids = []
    for mid in msg_ids:
        task = {
            "user_id":       uid,
            "chat_id":       chat_id,
            "source":        "telegram",
            "src_msg_id":    mid,
            "status_msg_id": status_msg.id,
            "caption":       f"Batch item {mid}",
            "priority":      priority,
            "send_as_doc":   False,
            "batch":         True,
        }
        tid = await add_to_queue(task)
        task_ids.append(tid)
        await asyncio.sleep(0.2)

    await status_msg.edit_text(
        f"✅ <b>{len(task_ids)} files</b> queued for encoding!\n"
        + "\n".join(f"• <code>{t}</code>" for t in task_ids[:10])
        + ("\n…" if len(task_ids) > 10 else "")
    )


@Client.on_message(filters.command("batch_cancel") & filters.private)
async def batch_cancel(client: Client, message: Message):
    uid = message.from_user.id
    _batch_sessions.pop(uid, None)
    await message.reply("🛑 Batch session cancelled.")

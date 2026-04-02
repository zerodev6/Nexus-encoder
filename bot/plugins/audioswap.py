"""
AudioSwap plugin — inspect and manipulate audio tracks via inline buttons.
"""

import json
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from bot.utils.ffmpeg_utils import probe
from bot.utils.keyboards import kb_audioswap
from bot.database.mongo import add_to_queue
from bot.utils.guards import require_subscription, is_admin

# user_id -> {"msg_id": int, "streams": list, "removed": set, "default": int}
_aswap_state: dict[int, dict] = {}


@Client.on_message(filters.command("audioswap") & filters.private)
@require_subscription
async def audioswap_start(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.media:
        await message.reply("↩️ Reply to a video file with /audioswap")
        return

    await message.reply("⬇️ Downloading to inspect audio streams…")
    # Download temporarily for probe
    from config import Config
    import os
    path = await client.download_media(target, file_name=Config.DOWNLOAD_DIR + "/")
    if not path:
        await message.reply("❌ Failed to download.")
        return

    info = await probe(path)
    streams = []
    for s in info.get("streams", []):
        if s.get("codec_type") == "audio":
            streams.append({
                "index":   s.get("index"),
                "lang":    s.get("tags", {}).get("language", "und"),
                "title":   s.get("tags", {}).get("title", ""),
                "default": s.get("disposition", {}).get("default", 0) == 1,
                "codec":   s.get("codec_name", ""),
            })

    if not streams:
        await message.reply("❌ No audio streams found.")
        os.remove(path)
        return

    uid = message.from_user.id
    _aswap_state[uid] = {
        "msg_id":  target.id,
        "path":    path,
        "streams": streams,
        "removed": set(),
        "default": next((s["index"] for s in streams if s["default"]), streams[0]["index"]),
    }

    await message.reply(
        f"🔊 <b>AudioSwap</b> — {len(streams)} audio track(s) found\n"
        "Use the buttons to set default or remove tracks.",
        reply_markup=kb_audioswap(streams),
    )


@Client.on_callback_query(filters.regex(r"^aswap_default_(\d+)$"))
async def aswap_set_default(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in _aswap_state:
        await cb.answer("Session expired.")
        return
    idx = int(cb.matches[0].group(1))
    _aswap_state[uid]["default"] = idx
    state = _aswap_state[uid]
    active = [s for s in state["streams"] if s["index"] not in state["removed"]]
    await cb.message.edit_reply_markup(kb_audioswap(active))
    await cb.answer(f"⭐ Stream {idx} set as default.")


@Client.on_callback_query(filters.regex(r"^aswap_remove_(\d+)$"))
async def aswap_remove(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in _aswap_state:
        await cb.answer("Session expired.")
        return
    idx = int(cb.matches[0].group(1))
    state = _aswap_state[uid]
    state["removed"].add(idx)
    active = [s for s in state["streams"] if s["index"] not in state["removed"]]
    if not active:
        await cb.message.edit_text("❌ Can't remove all audio streams.")
        state["removed"].discard(idx)
        return
    await cb.message.edit_reply_markup(kb_audioswap(active))
    await cb.answer(f"🗑 Stream {idx} removed.")


@Client.on_callback_query(filters.regex("^aswap_apply$"))
async def aswap_apply(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in _aswap_state:
        await cb.answer("Session expired.")
        return
    state = _aswap_state.pop(uid)

    active_indices = [s["index"] for s in state["streams"] if s["index"] not in state["removed"]]
    default_idx = state["default"]

    # Build audio_map: first the default track, then others
    ordered = sorted(active_indices, key=lambda i: (0 if i == default_idx else 1, i))
    audio_map = [f"0:a:{i}" for i in ordered]

    priority = 1 if is_admin(uid) else 0
    task = {
        "user_id":      uid,
        "chat_id":      cb.message.chat.id,
        "source":       "telegram",
        "src_msg_id":   state["msg_id"],
        "status_msg_id": cb.message.id,
        "audio_map":    audio_map,
        "priority":     priority,
        "send_as_doc":  False,
        "caption":      "AudioSwap result",
    }
    tid = await add_to_queue(task)
    await cb.message.edit_text(f"✅ <b>Queued with custom audio mapping!</b>\nTask: <code>{tid}</code>")
    await cb.answer()


@Client.on_callback_query(filters.regex("^aswap_cancel$"))
async def aswap_cancel(client: Client, cb: CallbackQuery):
    import os
    uid = cb.from_user.id
    state = _aswap_state.pop(uid, {})
    if state.get("path"):
        try:
            os.remove(state["path"])
        except Exception:
            pass
    await cb.message.edit_text("🛑 AudioSwap cancelled.")
    await cb.answer()

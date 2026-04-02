"""Settings plugin — full inline settings panel with callback handlers."""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from bot.database.mongo import get_user, update_user
from bot.utils.keyboards import (
    kb_main_settings, kb_codec, kb_preset, kb_resolution,
    kb_audio_codec, kb_container, kb_sub_mode, kb_wm_pos, kb_pixel_fmt,
)
from bot.utils.guards import require_subscription

# ── Pending state dict for multi-step inputs ──────────────────
# user_id -> {"action": str, "data": dict}
_pending: dict[int, dict] = {}


async def _settings_menu(message_or_cb, user_id: int, edit: bool = False):
    user = await get_user(user_id)
    s = user["settings"]
    text = (
        "⚙️ <b>Encoding Settings</b>\n\n"
        f"<b>Codec:</b> {s['codec']}  |  <b>Preset:</b> {s['preset']}\n"
        f"<b>CRF:</b> {s['crf']}  |  <b>Resolution:</b> {s['resolution']}\n"
        f"<b>PixFmt:</b> {s['pixel_fmt']}\n"
        f"<b>Audio:</b> {s['audio_codec']} @ {s['audio_br']}\n"
        f"<b>Container:</b> {s['container']}  |  <b>Subs:</b> {s['sub_mode']}\n"
        f"<b>Watermark:</b> {'✅ ' + s['watermark_text'] if s['watermark'] else '❌ off'}\n"
        f"<b>Custom filename:</b> {s['custom_fname'] or '(none)'}"
    )
    kb = kb_main_settings(s)
    if edit:
        await message_or_cb.edit_text(text, reply_markup=kb)
    else:
        await message_or_cb.reply(text, reply_markup=kb)


@Client.on_message(filters.command("settings") & filters.private)
@require_subscription
async def settings_cmd(client: Client, message: Message):
    await _settings_menu(message, message.from_user.id)


# ── Main settings callback ────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_main$"))
async def menu_main(client: Client, cb: CallbackQuery):
    await _settings_menu(cb.message, cb.from_user.id, edit=True)
    await cb.answer()


# ── Codec ─────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_codec$"))
async def menu_codec(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("🎥 <b>Choose Video Codec:</b>",
        reply_markup=kb_codec(user["settings"]["codec"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^codec_(.+)$"))
async def set_codec(client: Client, cb: CallbackQuery):
    codec = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.codec": codec})
    await menu_codec(client, cb)


# ── Preset ────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_preset$"))
async def menu_preset(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("⚡ <b>Choose FFmpeg Preset:</b>",
        reply_markup=kb_preset(user["settings"]["preset"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^preset_(.+)$"))
async def set_preset(client: Client, cb: CallbackQuery):
    preset = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.preset": preset})
    await menu_preset(client, cb)


# ── Resolution ────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_resolution$"))
async def menu_resolution(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("📐 <b>Choose Resolution:</b>",
        reply_markup=kb_resolution(user["settings"]["resolution"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^res_(.+)$"))
async def set_res(client: Client, cb: CallbackQuery):
    res = cb.matches[0].group(1)
    if res == "custom":
        _pending[cb.from_user.id] = {"action": "set_resolution"}
        await cb.message.edit_text("✏️ Send your custom resolution (e.g. <code>1280:720</code>):")
    else:
        await update_user(cb.from_user.id, {"settings.resolution": res})
        await menu_resolution(client, cb)
    await cb.answer()


# ── CRF ───────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^set_crf$"))
async def prompt_crf(client: Client, cb: CallbackQuery):
    _pending[cb.from_user.id] = {"action": "set_crf"}
    await cb.message.edit_text("🔢 Send CRF value (0–51). Lower = better quality.\nDefault: <b>23</b>")
    await cb.answer()


# ── Audio codec ───────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_audio$"))
async def menu_audio(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("🔊 <b>Choose Audio Codec:</b>",
        reply_markup=kb_audio_codec(user["settings"]["audio_codec"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^acodec_(.+)$"))
async def set_acodec(client: Client, cb: CallbackQuery):
    codec = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.audio_codec": codec})
    await menu_audio(client, cb)


# ── Container ─────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_container$"))
async def menu_container(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("📦 <b>Choose Container:</b>",
        reply_markup=kb_container(user["settings"]["container"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^cont_(.+)$"))
async def set_container(client: Client, cb: CallbackQuery):
    cont = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.container": cont})
    await menu_container(client, cb)


# ── Subtitle mode ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_subs$"))
async def menu_subs(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("💬 <b>Subtitle Mode:</b>",
        reply_markup=kb_sub_mode(user["settings"]["sub_mode"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^sub_(hardsub|softsub|none)$"))
async def set_sub_mode(client: Client, cb: CallbackQuery):
    mode = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.sub_mode": mode})
    await menu_subs(client, cb)


# ── Pixel format ──────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_pix$"))
async def menu_pix(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("🖼 <b>Choose Pixel Format:</b>",
        reply_markup=kb_pixel_fmt(user["settings"]["pixel_fmt"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^pix_(.+)$"))
async def set_pix(client: Client, cb: CallbackQuery):
    pix = cb.matches[0].group(1)
    await update_user(cb.from_user.id, {"settings.pixel_fmt": pix})
    await menu_pix(client, cb)


# ── Watermark ─────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^menu_watermark$"))
async def menu_watermark(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    s = user["settings"]
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton as B
    kb = InlineKeyboardMarkup([
        [B("🌊 Toggle On/Off", "wm_toggle")],
        [B("✏️ Set Text", "wm_set_text"), B("📍 Position", "wm_pos")],
        [B("⬅️ Back", "menu_main")],
    ])
    await cb.message.edit_text(
        f"🌊 <b>Watermark:</b> {'✅ On' if s['watermark'] else '❌ Off'}\n"
        f"Text: <code>{s['watermark_text']}</code>  Pos: <code>{s['watermark_pos']}</code>",
        reply_markup=kb,
    )
    await cb.answer()

@Client.on_callback_query(filters.regex("^wm_toggle$"))
async def wm_toggle(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    new = not user["settings"]["watermark"]
    await update_user(cb.from_user.id, {"settings.watermark": new})
    await menu_watermark(client, cb)

@Client.on_callback_query(filters.regex("^wm_set_text$"))
async def wm_set_text(client: Client, cb: CallbackQuery):
    _pending[cb.from_user.id] = {"action": "set_wm_text"}
    await cb.message.edit_text("✏️ Send the watermark text:")
    await cb.answer()

@Client.on_callback_query(filters.regex("^wm_pos$"))
async def wm_pos_menu(client: Client, cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    await cb.message.edit_text("📍 <b>Watermark Position:</b>",
        reply_markup=kb_wm_pos(user["settings"]["watermark_pos"]))
    await cb.answer()

@Client.on_callback_query(filters.regex(r"^wmpos_(.+)$"))
async def set_wm_pos(client: Client, cb: CallbackQuery):
    pos = cb.matches[0].group(1).replace("_", "-")
    await update_user(cb.from_user.id, {"settings.watermark_pos": pos})
    await wm_pos_menu(client, cb)


# ── Filename template ─────────────────────────────────────────
@Client.on_callback_query(filters.regex("^set_fname$"))
async def prompt_fname(client: Client, cb: CallbackQuery):
    _pending[cb.from_user.id] = {"action": "set_fname"}
    await cb.message.edit_text(
        "✏️ Send custom filename template.\n"
        "Use <code>{original}</code> for original name.\n"
        "Example: <code>Encoded_{original}_720p</code>"
    )
    await cb.answer()


# ── Reset ─────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^settings_reset$"))
async def settings_reset(client: Client, cb: CallbackQuery):
    from bot.database.mongo import _default_user
    defaults = _default_user(cb.from_user.id)["settings"]
    await update_user(cb.from_user.id, {"settings": defaults})
    await _settings_menu(cb.message, cb.from_user.id, edit=True)
    await cb.answer("✅ Settings reset to defaults.")


# ── Thumbnail ─────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^set_thumb$"))
async def prompt_thumb(client: Client, cb: CallbackQuery):
    _pending[cb.from_user.id] = {"action": "set_thumb"}
    await cb.message.edit_text("🖼 Send an image to use as thumbnail:")
    await cb.answer()


# ── Pending state handler ─────────────────────────────────────
@Client.on_message(filters.private & ~filters.command([]))
async def handle_pending(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in _pending:
        return False   # let other handlers process
    state = _pending.pop(uid)
    action = state["action"]

    if action == "set_crf":
        try:
            crf = int(message.text.strip())
            assert 0 <= crf <= 51
            await update_user(uid, {"settings.crf": crf})
            await message.reply(f"✅ CRF set to <b>{crf}</b>")
        except Exception:
            await message.reply("❌ Invalid CRF value (0–51).")

    elif action == "set_resolution":
        res = message.text.strip()
        await update_user(uid, {"settings.resolution": res})
        await message.reply(f"✅ Resolution set to <b>{res}</b>")

    elif action == "set_wm_text":
        text = message.text.strip()
        await update_user(uid, {"settings.watermark_text": text})
        await message.reply(f"✅ Watermark text set to <b>{text}</b>")

    elif action == "set_fname":
        fname = message.text.strip()
        await update_user(uid, {"settings.custom_fname": fname})
        await message.reply(f"✅ Filename template set to <code>{fname}</code>")

    elif action == "set_thumb" and message.photo:
        file_id = message.photo.file_id
        await update_user(uid, {"settings.thumbnail": file_id})
        await message.reply("✅ Custom thumbnail saved!")

    return True

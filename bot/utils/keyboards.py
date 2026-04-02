"""
All inline keyboard builders for MvxyBot.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn


# ── Codec menu ──────────────────────────────────────────────
def kb_codec(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    return InlineKeyboardMarkup([
        [Btn(mark("libx264"), "codec_libx264"),  Btn(mark("libx265"), "codec_libx265")],
        [Btn(mark("libvpx-vp9"), "codec_libvpx-vp9"), Btn("⬅️ Back", "menu_main")],
    ])


# ── Preset menu ─────────────────────────────────────────────
PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast",
           "medium", "slow", "slower", "veryslow"]

def kb_preset(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    rows = []
    row  = []
    for i, p in enumerate(PRESETS):
        row.append(Btn(mark(p), f"preset_{p}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([Btn("⬅️ Back", "menu_main")])
    return InlineKeyboardMarkup(rows)


# ── Resolution menu ─────────────────────────────────────────
RESOLUTIONS = ["1080p", "720p", "540p", "480p", "360p", "original", "custom"]

def kb_resolution(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    rows = []
    row  = []
    for i, r in enumerate(RESOLUTIONS):
        row.append(Btn(mark(r), f"res_{r}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([Btn("⬅️ Back", "menu_main")])
    return InlineKeyboardMarkup(rows)


# ── Audio codec menu ─────────────────────────────────────────
AUDIO_CODECS = ["aac", "ac3", "opus", "mp3", "flac", "copy"]

def kb_audio_codec(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    rows = []
    row  = []
    for c in AUDIO_CODECS:
        row.append(Btn(mark(c), f"acodec_{c}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([Btn("⬅️ Back", "menu_main")])
    return InlineKeyboardMarkup(rows)


# ── Container menu ────────────────────────────────────────────
def kb_container(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    return InlineKeyboardMarkup([
        [Btn(mark("mkv"), "cont_mkv"), Btn(mark("mp4"), "cont_mp4"), Btn(mark("avi"), "cont_avi")],
        [Btn("⬅️ Back", "menu_main")],
    ])


# ── Subtitle mode menu ────────────────────────────────────────
def kb_sub_mode(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    return InlineKeyboardMarkup([
        [Btn(mark("hardsub"), "sub_hardsub"), Btn(mark("softsub"), "sub_softsub"), Btn(mark("none"), "sub_none")],
        [Btn("⬅️ Back", "menu_main")],
    ])


# ── Watermark position menu ───────────────────────────────────
POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]

def kb_wm_pos(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    rows = [[Btn(mark(p), f"wmpos_{p.replace('-','_')}")] for p in POSITIONS]
    rows.append([Btn("⬅️ Back", "menu_watermark")])
    return InlineKeyboardMarkup(rows)


# ── Pixel format ──────────────────────────────────────────────
def kb_pixel_fmt(current: str) -> InlineKeyboardMarkup:
    def mark(v): return f"✅ {v}" if current == v else v
    return InlineKeyboardMarkup([
        [Btn(mark("yuv420p"), "pix_yuv420p"), Btn(mark("yuv420p10le"), "pix_yuv420p10le")],
        [Btn("⬅️ Back", "menu_main")],
    ])


# ── Main settings menu ────────────────────────────────────────
def kb_main_settings(s: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn(f"🎥 Codec: {s['codec']}", "menu_codec"),
         Btn(f"⚡ Preset: {s['preset']}", "menu_preset")],
        [Btn(f"📐 Res: {s['resolution']}", "menu_resolution"),
         Btn(f"🔢 CRF: {s['crf']}", "set_crf")],
        [Btn(f"🔊 Audio: {s['audio_codec']}", "menu_audio"),
         Btn(f"📦 Container: {s['container']}", "menu_container")],
        [Btn(f"🖼 Pixel fmt: {s['pixel_fmt']}", "menu_pix"),
         Btn(f"💬 Subs: {s['sub_mode']}", "menu_subs")],
        [Btn(f"🌊 Watermark: {'on' if s['watermark'] else 'off'}", "menu_watermark"),
         Btn("✏️ Filename", "set_fname")],
        [Btn("🖼 Set Thumbnail", "set_thumb"),  Btn("🔄 Reset", "settings_reset")],
    ])


# ── Upload options after encode ───────────────────────────────
def kb_upload_options() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn("📹 Send as Video", "upload_video"), Btn("📄 Send as Doc", "upload_doc")],
        [Btn("❌ Cancel", "task_cancel")],
    ])


# ── Cancel button ─────────────────────────────────────────────
def kb_cancel(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[Btn("❌ Cancel", f"cancel_{task_id}")]])


# ── AudioSwap menu ────────────────────────────────────────────
def kb_audioswap(streams: list[dict]) -> InlineKeyboardMarkup:
    """streams: list of {index, title, lang, default}"""
    rows = []
    for s in streams:
        label = f"[{s['index']}] {s.get('lang','?')} {s.get('title','')} {'⭐' if s.get('default') else ''}"
        rows.append([
            Btn(label,                    f"aswap_info_{s['index']}"),
            Btn("⭐ Default",              f"aswap_default_{s['index']}"),
            Btn("🗑 Remove",               f"aswap_remove_{s['index']}"),
        ])
    rows.append([Btn("✅ Apply & Encode", "aswap_apply"), Btn("❌ Cancel", "aswap_cancel")])
    return InlineKeyboardMarkup(rows)

"""Start, help, and welcome plugin."""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton as Btn

from config import Config
from bot.database.mongo import get_user
from bot.utils.guards import require_subscription

WELCOME_TEXT = """
<b>⚡ MvxyBot — Mirror Nexus</b>

An all-in-one Telegram encoder, converter & media toolkit.

<b>Quick Commands:</b>
• /dl — Encode a Telegram file
• /ddl — Download & encode from URL
• /batch — Batch process files
• /settings — Encoding preferences
• /audioswap — Manage audio tracks
• /status — Server status
• /speedtest — Speed test
• /help — Full command list

<i>Developer: {dev} | Updates: {ch}</i>
""".format(dev=Config.DEV_USERNAME, ch=Config.UPDATE_CHANNEL)

HELP_TEXT = """
<b>📖 MvxyBot Help</b>

<b>Upload & Download</b>
• /dl — Send a video/file, then reply with /dl to encode
• /ddl &lt;url&gt; — Direct link download
• /gdl &lt;gdrive_url&gt; — Google Drive download
• /batch — Batch mode (send multiple files, /batch_start / /batch_end)

<b>Encoding</b>
• /settings — Open settings panel (codec, preset, CRF, resolution…)
• /setcrf &lt;value&gt; — Set CRF (0–51, lower = better quality)
• /setpreset &lt;name&gt; — Set FFmpeg preset
• /setres &lt;res&gt; — e.g. 720p, 1080p, original

<b>Audio</b>
• /audioswap — Reorder / set default / remove audio tracks
• /setaudio &lt;codec&gt; — aac | ac3 | opus | mp3

<b>Subtitles</b>
• /setsub hardsub|softsub|none
• /addsub — Reply to .ass/.srt file to attach subtitles

<b>Watermark</b>
• /setwm on|off — Toggle watermark
• /setwmtext &lt;text&gt; — Watermark text
• /setwmpos — Choose position

<b>Metadata & Rename</b>
• /setmeta — Edit title / author / language
• /setfname &lt;template&gt; — e.g. {original}_encoded

<b>Queue</b>
• /queue — Your queue status
• /cancel — Cancel your active task

<b>Extras</b>
• /speedtest — Internet speed
• /status — CPU / RAM / Disk
• /thumb — Set custom thumbnail (reply to image)

<b>Admin Only</b>
• /broadcast &lt;text&gt;
• /stats
• /cancel_all
"""


@Client.on_message(filters.command("start") & filters.private)
@require_subscription
async def start_handler(client: Client, message: Message):
    await get_user(message.from_user.id)   # ensure user exists
    kb = InlineKeyboardMarkup([
        [Btn("⚙️ Settings", "menu_main"),      Btn("❓ Help", "show_help")],
        [Btn("📢 Updates", url=Config.UPDATE_CHANNEL)],
    ])
    await message.reply_photo(
        photo="https://telegra.ph/file/mvxy-banner.jpg",
        caption=WELCOME_TEXT,
        reply_markup=kb,
    ) if False else await message.reply(WELCOME_TEXT, reply_markup=kb)
    # Note: replace the above with an actual banner photo URL if desired


@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply(HELP_TEXT)


@Client.on_callback_query(filters.regex("^show_help$"))
async def show_help_cb(client: Client, cb):
    await cb.message.edit_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup([
        [Btn("⬅️ Back", "back_start")]
    ]))
    await cb.answer()


@Client.on_callback_query(filters.regex("^back_start$"))
async def back_start_cb(client: Client, cb):
    kb = InlineKeyboardMarkup([
        [Btn("⚙️ Settings", "menu_main"), Btn("❓ Help", "show_help")],
        [Btn("📢 Updates", url=Config.UPDATE_CHANNEL)],
    ])
    await cb.message.edit_text(WELCOME_TEXT, reply_markup=kb)
    await cb.answer()

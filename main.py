"""
╔══════════════════════════════════════╗
║         MvxyBot  •  Mirror Nexus     ║
║   Telegram Encoder Bot by @Venuboyy  ║
║   Updates → https://t.me/zerodev2   ║
╚══════════════════════════════════════╝
"""

import asyncio
import logging
import os

from pyrogram import Client
from pyrogram.enums import ParseMode

from config import Config
from bot.database.mongo import init_db
from bot.utils.scheduler import start_queue_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MvxyBot")

# ── Create required directories ──────────────────────────────
for d in (Config.DOWNLOAD_DIR, Config.ENCODE_DIR, Config.THUMB_DIR):
    os.makedirs(d, exist_ok=True)


# ── Bot client ───────────────────────────────────────────────
bot = Client(
    "MvxyBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins={"root": "bot/plugins"},
    parse_mode=ParseMode.HTML,
)

# ── Userbot client (4 GB uploads) ───────────────────────────
userbot: Client | None = None
if Config.SESSION_STRING:
    userbot = Client(
        "MvxyUserbot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.SESSION_STRING,
    )


async def main():
    await init_db()
    logger.info("✅ MongoDB connected")

    await bot.start()
    logger.info("✅ Bot started")

    if userbot:
        await userbot.start()
        logger.info("✅ Userbot started (4 GB mode active)")

    start_queue_worker(bot, userbot)
    logger.info("✅ Queue worker started")

    logger.info("🚀 MvxyBot is running …")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

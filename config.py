import os
from dotenv import load_dotenv

load_dotenv("config.env")

class Config:
    # ── Telegram ──────────────────────────────────────────────
    API_ID          = int(os.environ.get("API_ID", 0))
    API_HASH        = os.environ.get("API_HASH", "")
    BOT_TOKEN       = os.environ.get("BOT_TOKEN", "")
    SESSION_STRING  = os.environ.get("SESSION_STRING", "")   # Userbot (4 GB uploads)
    OWNER_ID        = int(os.environ.get("OWNER_ID", 0))
    ADMIN_IDS       = list(map(int, os.environ.get("ADMIN_IDS", "").split() if os.environ.get("ADMIN_IDS") else []))

    # ── MongoDB ───────────────────────────────────────────────
    MONGO_URI       = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME         = os.environ.get("DB_NAME", "mvxybot")

    # ── Google Drive ──────────────────────────────────────────
    GDRIVE_CREDS    = os.environ.get("GDRIVE_CREDS", "")     # base64-encoded credentials.json
    GDRIVE_FOLDER   = os.environ.get("GDRIVE_FOLDER", "")

    # ── Queue / Concurrency ────────────────────────────────────
    MAX_CONCURRENT  = int(os.environ.get("MAX_CONCURRENT", 3))

    # ── Bot identity ─────────────────────────────────────────
    BOT_USERNAME    = os.environ.get("BOT_USERNAME", "MvxyBot")
    DEV_USERNAME    = "@Venuboyy"
    UPDATE_CHANNEL  = "https://t.me/zerodev2"

    # ── Paths ─────────────────────────────────────────────────
    DOWNLOAD_DIR    = os.environ.get("DOWNLOAD_DIR", "/tmp/mvxy/downloads")
    ENCODE_DIR      = os.environ.get("ENCODE_DIR",   "/tmp/mvxy/encoded")
    THUMB_DIR       = os.environ.get("THUMB_DIR",    "/tmp/mvxy/thumbs")

    # ── Limits ────────────────────────────────────────────────
    MAX_FILE_SIZE   = 4 * 1024 * 1024 * 1024   # 4 GB (userbot)
    BOT_FILE_SIZE   = 2 * 1024 * 1024 * 1024   # 2 GB (bot)

    # ── Force-Subscribe ───────────────────────────────────────
    FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "")  # e.g. @zerodev2

    # ── Watermark defaults ────────────────────────────────────
    DEFAULT_WATERMARK_TEXT  = os.environ.get("DEFAULT_WATERMARK_TEXT", "MvxyBot")
    DEFAULT_WATERMARK_POS   = "bottom-right"   # top-left | top-right | bottom-left | bottom-right | center

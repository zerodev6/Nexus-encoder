"""Transfer helpers: download from Telegram, upload to Telegram, progress bars."""

import asyncio
import os
import time
from pathlib import Path

from pyrogram import Client
from pyrogram.types import Message

from config import Config


# ── Progress bar ─────────────────────────────────────────────

def _bar(pct: float, width: int = 12) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _size_str(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def make_progress_text(action: str, pct: float, speed: float = 0, eta: int = 0) -> str:
    bar = _bar(pct)
    spd = _size_str(int(speed)) + "/s" if speed else ""
    eta_s = f"{eta}s" if eta else ""
    return (
        f"<b>{action}</b>\n"
        f"<code>[{bar}]</code> <b>{pct:.1f}%</b>\n"
        f"{'⚡ ' + spd if spd else ''}"
        f"{'  ⏳ ' + eta_s if eta_s else ''}"
    )


class ProgressTracker:
    """Callable progress object that throttles Telegram edits."""

    def __init__(
        self,
        message: Message,
        action: str = "Processing",
        update_interval: float = 3.0,
    ):
        self._msg   = message
        self._action = action
        self._interval = update_interval
        self._last  = 0.0
        self._start = time.time()
        self._total = 0
        self._done  = 0

    async def __call__(self, current: int, total: int):
        self._done  = current
        self._total = total
        now = time.time()
        if now - self._last < self._interval:
            return
        self._last = now
        elapsed = max(now - self._start, 0.001)
        speed = current / elapsed
        remaining = total - current
        eta = int(remaining / speed) if speed > 0 else 0
        pct = current / total * 100 if total else 0
        text = make_progress_text(self._action, pct, speed, eta)
        try:
            await self._msg.edit_text(text)
        except Exception:
            pass

    async def set_pct(self, pct: float):
        """For FFmpeg progress (already a percentage)."""
        now = time.time()
        if now - self._last < self._interval:
            return
        self._last = now
        elapsed = max(now - self._start, 0.001)
        text = make_progress_text(self._action, pct)
        try:
            await self._msg.edit_text(text)
        except Exception:
            pass


# ── Download from Telegram ────────────────────────────────────

async def download_media(
    client: Client,
    message: Message,
    dest_dir: str,
    progress_msg: Message,
) -> str | None:
    tracker = ProgressTracker(progress_msg, "⬇️ Downloading")
    path = await client.download_media(
        message,
        file_name=dest_dir + "/",
        progress=tracker,
    )
    return path


# ── Upload to Telegram ────────────────────────────────────────

async def upload_video(
    client: Client,
    chat_id: int,
    path: str,
    caption: str,
    thumb: str | None,
    progress_msg: Message,
    reply_to: int | None = None,
) -> Message | None:
    from bot.utils.ffmpeg_utils import probe, take_screenshot

    tracker = ProgressTracker(progress_msg, "⬆️ Uploading")

    # Generate thumb if not provided
    if not thumb or not os.path.exists(thumb):
        thumb_path = path + ".thumb.jpg"
        if not await take_screenshot(path, thumb_path):
            thumb_path = None
    else:
        thumb_path = thumb

    info = await probe(path)
    duration = int(float(info.get("format", {}).get("duration", 0)))
    width = height = 0
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            width  = s.get("width", 0)
            height = s.get("height", 0)
            break

    size = os.path.getsize(path)
    use_userbot = size > Config.BOT_FILE_SIZE

    uploader = client  # default: bot
    if use_userbot:
        from main import userbot
        if userbot:
            uploader = userbot

    msg = await uploader.send_video(
        chat_id      = chat_id,
        video        = path,
        caption      = caption,
        thumb        = thumb_path,
        duration     = duration,
        width        = width,
        height       = height,
        supports_streaming = True,
        reply_to_message_id = reply_to,
        progress     = tracker,
    )
    return msg


async def upload_document(
    client: Client,
    chat_id: int,
    path: str,
    caption: str,
    progress_msg: Message,
    reply_to: int | None = None,
) -> Message | None:
    tracker = ProgressTracker(progress_msg, "⬆️ Uploading")
    size = os.path.getsize(path)
    use_userbot = size > Config.BOT_FILE_SIZE
    uploader = client
    if use_userbot:
        from main import userbot
        if userbot:
            uploader = userbot
    return await uploader.send_document(
        chat_id, path,
        caption=caption,
        reply_to_message_id=reply_to,
        progress=tracker,
    )


# ── DDL download (aiohttp) ────────────────────────────────────

async def download_url(url: str, dest: str, progress_msg: Message) -> str | None:
    import aiohttp
    tracker = ProgressTracker(progress_msg, "⬇️ Downloading URL")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            total = int(resp.headers.get("Content-Length", 0))
            fname = url.split("/")[-1].split("?")[0] or "file"
            path  = os.path.join(dest, fname)
            done  = 0
            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(512 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    await tracker(done, total)
    return path

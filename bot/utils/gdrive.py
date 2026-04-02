"""Google Drive download via google-auth / googleapiclient."""

import base64
import json
import os
import re

from config import Config


def _get_file_id(url: str) -> str | None:
    """Extract GDrive file ID from various link formats."""
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"open\?id=([a-zA-Z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


async def download_gdrive(url: str, dest_dir: str, progress_msg) -> str | None:
    import asyncio
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io

    file_id = _get_file_id(url)
    if not file_id:
        return None

    if not Config.GDRIVE_CREDS:
        return None

    creds_json = base64.b64decode(Config.GDRIVE_CREDS).decode()
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # Get filename
    meta = service.files().get(fileId=file_id, fields="name,size").execute()
    filename = meta.get("name", file_id)
    total    = int(meta.get("size", 0))
    dest_path = os.path.join(dest_dir, filename)

    request = service.files().get_media(fileId=file_id)
    buf = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(buf, request, chunksize=8 * 1024 * 1024)

    done = False
    while not done:
        status, done = await asyncio.to_thread(downloader.next_chunk)
        if status and total and progress_msg:
            pct = status.progress() * 100
            try:
                from bot.utils.transfer import make_progress_text
                await progress_msg.edit_text(make_progress_text("⬇️ GDrive", pct))
            except Exception:
                pass

    buf.close()
    return dest_path

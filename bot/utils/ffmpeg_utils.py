"""
FFmpeg wrapper — encoding, conversion, watermark, subtitles, metadata.
All functions are async; they stream stderr for progress callbacks.
"""

import asyncio
import os
import re
import shutil
from pathlib import Path
from typing import Callable, Awaitable

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

ProgressCB = Callable[[float], Awaitable[None]]   # percent 0-100


# ────────────────────────────────────────────────────────────
#  Probe
# ────────────────────────────────────────────────────────────

async def probe(path: str) -> dict:
    """Return ffprobe JSON for *path*."""
    import json
    proc = await asyncio.create_subprocess_exec(
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return json.loads(out)


async def get_duration(path: str) -> float:
    """Total duration in seconds."""
    info = await probe(path)
    return float(info.get("format", {}).get("duration", 0))


# ────────────────────────────────────────────────────────────
#  Build FFmpeg command
# ────────────────────────────────────────────────────────────

def _build_encode_cmd(
    inp: str,
    out: str,
    settings: dict,
    subtitle_path: str | None = None,
    audio_map: list[str] | None = None,
) -> list[str]:
    cmd = [FFMPEG, "-y", "-i", inp]

    # ── Subtitle source ──────────────────────────────────────
    if subtitle_path:
        cmd += ["-i", subtitle_path]

    cmd += ["-map", "0:v:0"]   # video stream

    # ── Audio mapping ────────────────────────────────────────
    if audio_map:
        for a in audio_map:
            cmd += ["-map", a]
    else:
        cmd += ["-map", "0:a?"]

    # ── Subtitle output mapping ──────────────────────────────
    sub_mode = settings.get("sub_mode", "none")
    if sub_mode == "softsub" and subtitle_path:
        cmd += ["-map", "1:s?", "-map", "0:s?"]

    # ── Video codec ──────────────────────────────────────────
    codec    = settings.get("codec", "libx264")
    preset   = settings.get("preset", "medium")
    crf      = settings.get("crf", 23)
    pix_fmt  = settings.get("pixel_fmt", "yuv420p")
    cmd += ["-c:v", codec, "-preset", preset, "-crf", str(crf), "-pix_fmt", pix_fmt]

    # ── Resolution ───────────────────────────────────────────
    res = settings.get("resolution", "original")
    scale_map = {
        "1080p": "1920:1080", "720p": "1280:720",
        "540p": "960:540",    "480p": "854:480",
        "360p": "640:360",
    }
    if res in scale_map:
        w, h = scale_map[res].split(":")
        cmd += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"]
    elif res not in ("original", ""):
        # custom e.g. "1280:720"
        cmd += ["-vf", f"scale={res}"]

    # ── Audio codec ───────────────────────────────────────────
    a_codec = settings.get("audio_codec", "aac")
    a_br    = settings.get("audio_br", "128k")
    a_sr    = settings.get("audio_sr", "")
    a_ch    = settings.get("audio_channels", "")
    cmd += ["-c:a", a_codec, "-b:a", a_br]
    if a_sr:
        cmd += ["-ar", a_sr]
    if a_ch:
        cmd += ["-ac", a_ch]

    # ── Hardsub via ASS filter ───────────────────────────────
    if sub_mode == "hardsub" and subtitle_path:
        # Escape path for ffmpeg filter
        safe = subtitle_path.replace("\\", "/").replace(":", "\\:")
        # Append to existing vf or create new
        vf_idx = None
        for i, v in enumerate(cmd):
            if v == "-vf":
                vf_idx = i + 1
                break
        if vf_idx:
            cmd[vf_idx] += f",ass={safe}"
        else:
            cmd += ["-vf", f"ass={safe}"]

    # ── Watermark ────────────────────────────────────────────
    if settings.get("watermark"):
        _apply_watermark(cmd, settings)

    # ── Subtitle stream codec ────────────────────────────────
    if sub_mode == "softsub":
        cmd += ["-c:s", "copy"]

    # ── Container ─────────────────────────────────────────────
    container = settings.get("container", "mkv")
    out_path = str(Path(out).with_suffix(f".{container}"))
    cmd.append(out_path)
    return cmd, out_path


def _apply_watermark(cmd: list, settings: dict):
    text = settings.get("watermark_text", "MvxyBot")
    pos  = settings.get("watermark_pos", "bottom-right")
    pos_map = {
        "top-left":     "10:10",
        "top-right":    "main_w-text_w-10:10",
        "bottom-left":  "10:main_h-text_h-10",
        "bottom-right": "main_w-text_w-10:main_h-text_h-10",
        "center":       "(main_w-text_w)/2:(main_h-text_h)/2",
    }
    xy = pos_map.get(pos, "main_w-text_w-10:main_h-text_h-10")
    drawtext = (
        f"drawtext=text='{text}'"
        f":fontsize=28:fontcolor=white@0.7"
        f":x={xy.split(':')[0]}:y={xy.split(':')[1]}"
        f":shadowcolor=black@0.5:shadowx=1:shadowy=1"
    )
    # Append to existing -vf
    for i, v in enumerate(cmd):
        if v == "-vf":
            cmd[i + 1] += f",{drawtext}"
            return
    cmd += ["-vf", drawtext]


# ────────────────────────────────────────────────────────────
#  Run with progress
# ────────────────────────────────────────────────────────────

async def run_ffmpeg(
    cmd: list[str],
    duration: float,
    progress_cb: ProgressCB | None = None,
) -> bool:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    time_re = re.compile(r"time=(\d+):(\d+):([\d.]+)")
    async for line in proc.stderr:
        line = line.decode(errors="ignore")
        m = time_re.search(line)
        if m and duration > 0 and progress_cb:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            elapsed = h * 3600 + mi * 60 + s
            pct = min(elapsed / duration * 100, 100)
            await progress_cb(pct)
    await proc.wait()
    return proc.returncode == 0


# ────────────────────────────────────────────────────────────
#  Public encode function
# ────────────────────────────────────────────────────────────

async def encode_video(
    inp: str,
    out_dir: str,
    settings: dict,
    subtitle_path: str | None = None,
    audio_map: list[str] | None = None,
    progress_cb: ProgressCB | None = None,
) -> str | None:
    base = Path(inp).stem + "_encoded"
    out  = os.path.join(out_dir, base)
    cmd, out_path = _build_encode_cmd(inp, out, settings, subtitle_path, audio_map)
    duration = await get_duration(inp)
    ok = await run_ffmpeg(cmd, duration, progress_cb)
    return out_path if ok and os.path.exists(out_path) else None


# ────────────────────────────────────────────────────────────
#  Audio extraction / conversion
# ────────────────────────────────────────────────────────────

async def extract_audio(inp: str, out: str, codec: str = "aac", bitrate: str = "192k") -> bool:
    cmd = [FFMPEG, "-y", "-i", inp, "-vn", "-c:a", codec, "-b:a", bitrate, out]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()
    return proc.returncode == 0


# ────────────────────────────────────────────────────────────
#  Metadata editing
# ────────────────────────────────────────────────────────────

async def set_metadata(inp: str, out: str, meta: dict) -> bool:
    """meta keys: title, artist, comment, year, etc."""
    cmd = [FFMPEG, "-y", "-i", inp, "-c", "copy"]
    for k, v in meta.items():
        cmd += ["-metadata", f"{k}={v}"]
    cmd.append(out)
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()
    return proc.returncode == 0


# ────────────────────────────────────────────────────────────
#  Screenshot / thumbnail
# ────────────────────────────────────────────────────────────

async def take_screenshot(inp: str, out: str, time: float = 5.0) -> bool:
    cmd = [FFMPEG, "-y", "-ss", str(time), "-i", inp, "-vframes", "1", "-q:v", "2", out]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()
    return proc.returncode == 0 and os.path.exists(out)

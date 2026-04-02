"""Admin-only commands."""

import asyncio
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message

from bot.utils.guards import admin_only
from bot.database.mongo import get_global_stats, cancel_all_tasks, get_db


@Client.on_message(filters.command("stats") & filters.private)
@admin_only
async def stats_cmd(client: Client, message: Message):
    stats = await get_global_stats()
    cpu   = psutil.cpu_percent(interval=0.5)
    ram   = psutil.virtual_memory()
    disk  = psutil.disk_usage("/")

    text = (
        "📊 <b>MvxyBot Stats</b>\n\n"
        f"👤 <b>Users:</b> {stats['users']}\n"
        f"✅ <b>Jobs done:</b> {stats['done']}\n"
        f"⏳ <b>Pending:</b> {stats['pending']}\n\n"
        f"🖥 <b>CPU:</b> {cpu}%\n"
        f"🧠 <b>RAM:</b> {ram.used // 1024**2} MB / {ram.total // 1024**2} MB "
        f"({ram.percent}%)\n"
        f"💾 <b>Disk:</b> {disk.used // 1024**3} GB / {disk.total // 1024**3} GB "
        f"({disk.percent}%)"
    )
    await message.reply(text)


@Client.on_message(filters.command("status") & filters.private)
async def status_cmd(client: Client, message: Message):
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    text = (
        "🖥 <b>Server Status</b>\n\n"
        f"CPU:  <b>{cpu}%</b>\n"
        f"RAM:  <b>{ram.percent}%</b>  "
        f"({ram.used // 1024**2}/{ram.total // 1024**2} MB)\n"
        f"Disk: <b>{disk.percent}%</b>  "
        f"({disk.used // 1024**3}/{disk.total // 1024**3} GB)"
    )
    await message.reply(text)


@Client.on_message(filters.command("broadcast") & filters.private)
@admin_only
async def broadcast_cmd(client: Client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Usage: /broadcast <message>")
        return

    text    = parts[1]
    db      = get_db()
    total   = 0
    failed  = 0

    prog = await message.reply("📢 Broadcasting…")
    async for user in db.users.find({}, {"user_id": 1}):
        uid = user["user_id"]
        try:
            await client.send_message(uid, text)
            total += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await prog.edit_text(f"✅ Broadcast complete.\nSent: <b>{total}</b>  Failed: <b>{failed}</b>")


@Client.on_message(filters.command("cancel_all") & filters.private)
@admin_only
async def cancel_all_cmd(client: Client, message: Message):
    await cancel_all_tasks()
    await message.reply("🛑 All pending/processing tasks cancelled.")


@Client.on_message(filters.command("speedtest") & filters.private)
async def speedtest_cmd(client: Client, message: Message):
    prog = await message.reply("⚡ Running speed test…")
    try:
        import speedtest as st
        def run():
            s = st.Speedtest(secure=True)
            s.get_best_server()
            s.download()
            s.upload()
            return s.results.dict()

        results = await asyncio.to_thread(run)
        dl = results["download"] / 1_000_000
        ul = results["upload"] / 1_000_000
        ping = results["ping"]
        isp  = results.get("client", {}).get("isp", "?")

        await prog.edit_text(
            "⚡ <b>Speed Test Results</b>\n\n"
            f"⬇️ Download: <b>{dl:.2f} Mbps</b>\n"
            f"⬆️ Upload:   <b>{ul:.2f} Mbps</b>\n"
            f"🏓 Ping:     <b>{ping:.1f} ms</b>\n"
            f"🌐 ISP:      <b>{isp}</b>"
        )
    except ImportError:
        await prog.edit_text("❌ speedtest-cli not installed. Run: pip install speedtest-cli")
    except Exception as e:
        await prog.edit_text(f"❌ Speed test failed: {e}")

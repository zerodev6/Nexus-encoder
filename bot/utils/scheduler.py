"""
Async queue worker — pulls tasks from MongoDB and dispatches encode jobs.
"""

import asyncio
import logging
import os

from pyrogram import Client

from config import Config
from bot.database.mongo import next_pending_task, complete_task

logger = logging.getLogger("Scheduler")

_semaphore: asyncio.Semaphore | None = None
_worker_task: asyncio.Task | None = None

# In-memory cancel flags: task_id -> asyncio.Event
_cancel_flags: dict[str, asyncio.Event] = {}


def get_cancel_flag(task_id: str) -> asyncio.Event:
    if task_id not in _cancel_flags:
        _cancel_flags[task_id] = asyncio.Event()
    return _cancel_flags[task_id]


def start_queue_worker(bot: Client, userbot: Client | None):
    global _semaphore, _worker_task
    _semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT)
    _worker_task = asyncio.create_task(_queue_loop(bot, userbot))


async def _queue_loop(bot: Client, userbot: Client | None):
    while True:
        task = await next_pending_task()
        if task:
            asyncio.create_task(_dispatch(bot, userbot, task))
        else:
            await asyncio.sleep(2)


async def _dispatch(bot: Client, userbot: Client | None, task: dict):
    task_id = str(task["_id"])
    async with _semaphore:
        try:
            from bot.utils.job_runner import run_task
            await run_task(bot, userbot, task)
            await complete_task(task_id, success=True)
        except asyncio.CancelledError:
            await complete_task(task_id, success=False)
        except Exception as e:
            logger.exception("Task %s failed: %s", task_id, e)
            await complete_task(task_id, success=False)
        finally:
            _cancel_flags.pop(task_id, None)

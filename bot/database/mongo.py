"""MongoDB async layer using motor."""

import motor.motor_asyncio
from config import Config

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_db = None


async def init_db():
    global _client, _db
    _client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
    _db = _client[Config.DB_NAME]
    # Indexes
    await _db.users.create_index("user_id", unique=True)
    await _db.queue.create_index([("status", 1), ("priority", -1), ("created_at", 1)])


def get_db():
    return _db


# ── User helpers ─────────────────────────────────────────────

async def get_user(user_id: int) -> dict:
    doc = await _db.users.find_one({"user_id": user_id})
    if not doc:
        doc = _default_user(user_id)
        await _db.users.insert_one(doc)
    return doc


async def update_user(user_id: int, data: dict):
    await _db.users.update_one({"user_id": user_id}, {"$set": data}, upsert=True)


def _default_user(user_id: int) -> dict:
    from config import Config
    return {
        "user_id": user_id,
        "settings": {
            "codec":       "libx264",
            "preset":      "medium",
            "crf":         23,
            "resolution":  "original",
            "pixel_fmt":   "yuv420p",   # yuv420p10le for 10-bit
            "audio_codec": "aac",
            "audio_br":    "128k",
            "container":   "mkv",
            "watermark":   False,
            "watermark_text": Config.DEFAULT_WATERMARK_TEXT,
            "watermark_pos":  Config.DEFAULT_WATERMARK_POS,
            "sub_mode":    "softsub",   # hardsub | softsub | none
            "custom_fname": "",
            "thumbnail":   None,        # file_id of custom thumb
        },
        "stats": {"encoded": 0, "uploaded_bytes": 0},
        "banned": False,
    }


# ── Queue helpers ─────────────────────────────────────────────

async def add_to_queue(task: dict) -> str:
    from datetime import datetime
    task["status"]     = "pending"
    task["created_at"] = datetime.utcnow()
    result = await _db.queue.insert_one(task)
    return str(result.inserted_id)


async def next_pending_task() -> dict | None:
    return await _db.queue.find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing"}},
        sort=[("priority", -1), ("created_at", 1)],
    )


async def complete_task(task_id, success: bool = True):
    from bson import ObjectId
    status = "done" if success else "failed"
    await _db.queue.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": status}})


async def cancel_task(task_id):
    from bson import ObjectId
    await _db.queue.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "cancelled"}})


async def cancel_all_tasks():
    await _db.queue.update_many({"status": {"$in": ["pending", "processing"]}}, {"$set": {"status": "cancelled"}})


async def queue_stats() -> dict:
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    result = {}
    async for doc in _db.queue.aggregate(pipeline):
        result[doc["_id"]] = doc["count"]
    return result


# ── Global stats ─────────────────────────────────────────────

async def get_global_stats() -> dict:
    users   = await _db.users.count_documents({})
    pending = await _db.queue.count_documents({"status": "pending"})
    done    = await _db.queue.count_documents({"status": "done"})
    return {"users": users, "pending": pending, "done": done}

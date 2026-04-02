"""Decorators and helpers for force-subscribe and admin checks."""

from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from config import Config


def is_admin(user_id: int) -> bool:
    return user_id == Config.OWNER_ID or user_id in Config.ADMIN_IDS


async def check_subscription(client: Client, user_id: int) -> bool:
    """Return True if user is subscribed to FORCE_SUB_CHANNEL (or if not set)."""
    if not Config.FORCE_SUB_CHANNEL:
        return True
    try:
        member = await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        from pyrogram.enums import ChatMemberStatus
        return member.status not in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
            ChatMemberStatus.RESTRICTED,
        )
    except Exception:
        return False


def require_subscription(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if not await check_subscription(client, message.from_user.id):
            await message.reply(
                f"⚠️ You must join <a href='https://t.me/{Config.FORCE_SUB_CHANNEL.lstrip('@')}'>our channel</a> "
                f"before using this bot.",
                disable_web_page_preview=True,
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper


def admin_only(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            await message.reply("🚫 Admin only command.")
            return
        return await func(client, message, *args, **kwargs)
    return wrapper

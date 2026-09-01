import html
import re
from typing import List, Dict, Tuple, Optional, Any
from telegram import Bot
from telegram.constants import ChatMemberStatus
from config import FORCE_SUB_CHANNELS, is_admin, logger


def parse_channel_target(channel_str: str) -> Any:
    """Normalize channel identifier into int (if ID) or @username."""
    cleaned = channel_str.strip()
    # Check if numeric chat ID (e.g. -100123456789 or 123456789)
    if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
        return int(cleaned)
    # Check if t.me link
    if "t.me/" in cleaned:
        match = re.search(r"t\.me/([a-zA-Z0-9_+]+)", cleaned)
        if match:
            username = match.group(1)
            if not username.startswith("+") and not username.startswith("joinchat"):
                return f"@{username}"
            return cleaned  # private invite link
    # If username without @
    if not cleaned.startswith("@") and not cleaned.startswith("http"):
        return f"@{cleaned}"
    return cleaned


async def check_channel_membership(
    bot: Bot,
    user_id: int,
    raw_channel: str
) -> Tuple[bool, str, str]:
    """
    Check if a user is a member of a given channel.
    
    Returns:
        (is_member, display_title, invite_link)
    """
    target = parse_channel_target(raw_channel)
    display_title = str(raw_channel)
    invite_link = ""

    # Determine default link if possible
    if isinstance(target, str) and target.startswith("@"):
        invite_link = f"https://t.me/{target[1:]}"
        display_title = target
    elif isinstance(target, str) and target.startswith("http"):
        invite_link = target
    elif isinstance(target, int):
        invite_link = f"https://t.me/c/{str(abs(target))[3:] if str(abs(target)).startswith('100') else abs(target)}"

    try:
        chat = await bot.get_chat(chat_id=target)
        display_title = chat.title or (f"@{chat.username}" if chat.username else display_title)
        
        # Prefer username link or existing invite link
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            invite_link = chat.invite_link
        elif not invite_link.startswith("http"):
            try:
                invite_link = await bot.export_chat_invite_link(chat_id=chat.id)
            except Exception:
                pass

        member = await bot.get_chat_member(chat_id=chat.id, user_id=user_id)
        
        # Active statuses
        allowed_statuses = {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        }

        if member.status in allowed_statuses:
            return True, display_title, invite_link
        elif member.status == ChatMemberStatus.RESTRICTED:
            # Check if user is still a member of the chat
            if getattr(member, "is_member", False):
                return True, display_title, invite_link

        # If status is LEFT, BANNED, etc.
        return False, display_title, invite_link

    except Exception as e:
        logger.warning(f"Error checking membership for user {user_id} in {raw_channel}: {e}")
        err_msg = str(e).lower()
        if "user not found" in err_msg or "participant" in err_msg or "left" in err_msg:
            return False, display_title, invite_link
        logger.error(f"Cannot verify force sub channel {raw_channel}. Ensure bot is added as admin to this channel.")
        return True, display_title, invite_link


async def get_unsubscribed_channels(bot: Bot, user_id: int) -> List[Dict[str, str]]:
    """
    Get all configured force subscribe channels that the user hasn't joined.
    Admins automatically bypass force subscription.
    """
    if not FORCE_SUB_CHANNELS:
        return []
    
    if is_admin(user_id):
        return []

    unsubscribed: List[Dict[str, str]] = []

    for raw_channel in FORCE_SUB_CHANNELS:
        is_member, title, link = await check_channel_membership(bot, user_id, raw_channel)
        if not is_member:
            unsubscribed.append({
                "channel": raw_channel,
                "title": title,
                "url": link if link else "https://t.me/"
            })

    return unsubscribed


def get_force_sub_message(user_first_name: str = "", channels: Optional[List[Dict[str, str]]] = None) -> str:
    """Generate force subscription required message matching design."""
    return (
        "👋 <b>Welcome!</b>\n\n"
        "⚠️ <b>To use this bot, you must join our official channel(s) first.</b>\n\n"
        "Please click the button(s) below to join all channels, then tap '🔄 I Have Joined (Verify)' to continue!"
    )

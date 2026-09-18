from __future__ import annotations
import html
import re
from typing import Dict, Tuple, Optional, List, Any
from telegram import User, InlineKeyboardButton, InlineKeyboardMarkup


def format_welcome_message(template: str, user: User, chat_title: str) -> str:
    """Format welcome message template with user and chat metadata."""
    first_name = user.first_name or "there"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user.username else first_name
    mention = f"<a href=\"tg://user?id={user.id}\">{html.escape(full_name)}</a>"

    replacements: Dict[str, str] = {
        "{name}": html.escape(full_name),
        "{first_name}": html.escape(first_name),
        "{last_name}": html.escape(last_name),
        "{username}": html.escape(username),
        "{mention}": mention,
        "{chat_title}": html.escape(chat_title),
        "{user_id}": str(user.id),
    }

    formatted = template
    for key, val in replacements.items():
        formatted = formatted.replace(key, val)

    return formatted


def _clean_and_validate_url(raw_url: str) -> str:
    """Validate and format button URL."""
    raw_url = raw_url.strip().strip("{}").strip()
    if not raw_url:
        return "https://t.me"
    if raw_url.startswith("@"):
        return f"https://t.me/{raw_url[1:]}"
    if raw_url.startswith("t.me/"):
        return f"https://{raw_url}"
    if raw_url.startswith(("http://", "https://", "tg://")):
        return raw_url
    if "." in raw_url and not raw_url.startswith("/"):
        return f"https://{raw_url}"
    return f"https://t.me/{raw_url}"


def parse_buttons_and_clean_text(
    raw_text: str,
    user: User,
    chat_title: str
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Extracts custom inline buttons from the text and returns (cleaned_text, inline_keyboard).
    
    Supported button formats:
    - [Button Text] - {https://link.com}
    - [Button Text] - {channel_username}
    - [Button Text - https://link.com]
    - [Button Text - @username]
    - [Button Text | https://link.com]
    - [Btn 1] - {link1} | [Btn 2] - {link2}
    - [Btn 1 - https://link1.com | Btn 2 - https://link2.com]
    """
    if not raw_text:
        return "", None

    # Replace user variables first
    first_name = user.first_name or "there"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user.username else first_name
    mention = f"<a href=\"tg://user?id={user.id}\">{html.escape(full_name)}</a>"

    var_map = {
        "{name}": html.escape(full_name),
        "{first_name}": html.escape(first_name),
        "{last_name}": html.escape(last_name),
        "{username}": html.escape(username),
        "{mention}": mention,
        "{chat_title}": html.escape(chat_title),
        "{user_id}": str(user.id),
    }

    lines = raw_text.splitlines()
    cleaned_lines: List[str] = []
    keyboard_rows: List[List[InlineKeyboardButton]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        # Format 1: [Button Name] - {link/username} or [Btn 1] - {link1} | [Btn 2] - {link2}
        pattern_outside = r"\[([^\]]+)\]\s*(?:[-|:]|->)?\s*\{([^}]+)\}"
        matches_outside = re.findall(pattern_outside, stripped)
        if matches_outside:
            row: List[InlineKeyboardButton] = []
            for btn_txt, btn_raw_url in matches_outside:
                clean_url = _clean_and_validate_url(btn_raw_url)
                clean_btn_text = btn_txt.strip()
                for k, v in var_map.items():
                    clean_btn_text = clean_btn_text.replace(k, v)
                clean_btn_text = re.sub(r"<[^>]+>", "", clean_btn_text)
                row.append(InlineKeyboardButton(text=clean_btn_text, url=clean_url))
            if row:
                keyboard_rows.append(row)
                continue

        # Format 2: [Button Name] - link or [Button Name] - @username
        outside_plain = re.match(r"^\[([^\]]+)\]\s*(?:[-|:]|->)\s*(\S+)", stripped)
        if outside_plain:
            btn_txt = outside_plain.group(1).strip()
            raw_url = outside_plain.group(2).strip()
            clean_url = _clean_and_validate_url(raw_url)
            clean_btn_text = btn_txt.strip()
            for k, v in var_map.items():
                clean_btn_text = clean_btn_text.replace(k, v)
            clean_btn_text = re.sub(r"<[^>]+>", "", clean_btn_text)
            keyboard_rows.append([InlineKeyboardButton(text=clean_btn_text, url=clean_url)])
            continue

        # Format 3: [Button Name - https://link] or [Btn 1 - link1 | Btn 2 - link2]
        bracket_blocks = re.findall(r"\[([^\[\]]+)\]", stripped)
        if bracket_blocks:
            row: List[InlineKeyboardButton] = []
            is_button_line = False

            for block in bracket_blocks:
                sub_items = [block]
                if " | " in block:
                    sub_items = block.split(" | ")
                elif " || " in block:
                    sub_items = block.split(" || ")

                for item in sub_items:
                    pair = re.split(r"\s+(?:[-|:]|->)\s+", item.strip(), maxsplit=1)
                    if len(pair) == 2:
                        btn_text = pair[0].strip()
                        raw_url = pair[1].strip()
                        clean_url = _clean_and_validate_url(raw_url)
                        is_button_line = True
                        clean_btn_text = btn_text
                        for k, v in var_map.items():
                            clean_btn_text = clean_btn_text.replace(k, v)
                        clean_btn_text = re.sub(r"<[^>]+>", "", clean_btn_text)
                        row.append(InlineKeyboardButton(text=clean_btn_text, url=clean_url))

            if is_button_line and row:
                keyboard_rows.append(row)
                continue

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    for k, v in var_map.items():
        cleaned_text = cleaned_text.replace(k, v)

    inline_kb = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
    return cleaned_text, inline_kb


def get_add_to_channel_url(bot_username: str) -> str:
    """Return link to add bot as admin in a channel."""
    return f"https://t.me/{bot_username}?startchannel=true&admin=invite_users+manage_chat"


def get_add_to_group_url(bot_username: str) -> str:
    """Return link to add bot as admin in a group."""
    return f"https://t.me/{bot_username}?startgroup=true&admin=invite_users+manage_chat"


async def send_safe_welcome_dm(
    bot,
    user_id: int,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None
) -> bool:
    """Send welcome DM safely with automatic media error and HTML parsing fallback."""
    import telegram.error
    from config import logger

    if not text or not text.strip():
        text = "👋 Welcome aboard! Your request has been approved. ✨"

    # 1. Try sending with media (photo/video/animation) if configured
    if media_file_id and media_type in ("photo", "video", "animation"):
        try:
            if media_type == "photo":
                try:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    return True
                except telegram.error.BadRequest:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=media_file_id,
                        caption=text,
                        reply_markup=keyboard
                    )
                    return True
            elif media_type == "video":
                try:
                    await bot.send_video(
                        chat_id=user_id,
                        video=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    return True
                except telegram.error.BadRequest:
                    await bot.send_video(
                        chat_id=user_id,
                        video=media_file_id,
                        caption=text,
                        reply_markup=keyboard
                    )
                    return True
            elif media_type == "animation":
                try:
                    await bot.send_animation(
                        chat_id=user_id,
                        animation=media_file_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    return True
                except telegram.error.BadRequest:
                    await bot.send_animation(
                        chat_id=user_id,
                        animation=media_file_id,
                        caption=text,
                        reply_markup=keyboard
                    )
                    return True
        except telegram.error.Forbidden:
            logger.debug(f"Could not send DM to user {user_id} (user hasn't started bot or blocked it).")
            return False
        except Exception as media_err:
            logger.warning(f"Media sending failed ({media_err}), falling back to text message for user {user_id}")

    # 2. Text message fallback (or primary if no media)
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
        return True
    except telegram.error.BadRequest:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to send plain text welcome DM to {user_id}: {e}")
            return False
    except telegram.error.Forbidden:
        logger.debug(f"Could not send DM to user {user_id} (user hasn't started bot or blocked it).")
        return False
    except Exception as e:
        logger.warning(f"Failed to send welcome DM to {user_id}: {e}")
        return False


async def can_user_manage_chat(bot, chat_id: int, user_id: int) -> bool:
    """
    Check if a user is authorized to manage a specific chat.
    Allowed if:
    1. The user is a configured bot superadmin (is_admin(user_id)).
    2. The chat's owner_id in the database matches user_id.
    3. The chat is unassigned or legacy, and Telegram confirms the user is creator/admin.
       In this case, ownership is auto-linked in the database.
    """
    from config import is_admin
    from database.db import get_chat, set_chat_owner

    if is_admin(user_id):
        return True

    chat_data = await get_chat(chat_id)
    if not chat_data:
        return False

    # Direct match in database
    if chat_data.get("owner_id") == user_id:
        return True

    # If owner_id is set to another user, check if this user is a Telegram chat admin/creator
    if chat_data.get("owner_id") is not None and chat_data.get("owner_id") != user_id:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["creator", "administrator"]:
                return True
        except Exception:
            pass
        return False

    # If owner_id is None (unassigned / legacy chat)
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ["creator", "administrator"]:
            await set_chat_owner(chat_id, user_id)
            return True
    except Exception:
        pass

    return False


async def get_user_manageable_chats(bot, user_id: int, is_superadmin_view: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve chats that the given user owns or manages.
    If is_superadmin_view is True, returns all chats in the database.
    Otherwise:
    - Returns all chats where owner_id == user_id.
    - For any unassigned chats (owner_id IS NULL), checks if user is admin in Telegram.
      If so, claims them and includes them in the list.
    """
    from database.db import get_all_chats, get_chats_by_owner, get_unassigned_chats, set_chat_owner

    if is_superadmin_view:
        return await get_all_chats()

    # 1. Fetch chats assigned to this user
    user_chats = await get_chats_by_owner(user_id)
    existing_chat_ids = {c["chat_id"] for c in user_chats}

    # 2. Check unassigned chats to see if this user is their admin/creator
    unassigned = await get_unassigned_chats()
    for chat in unassigned:
        chat_id = chat["chat_id"]
        if chat_id in existing_chat_ids:
            continue
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["creator", "administrator"]:
                await set_chat_owner(chat_id, user_id)
                chat["owner_id"] = user_id
                user_chats.append(chat)
                existing_chat_ids.add(chat_id)
        except Exception:
            pass

    return user_chats



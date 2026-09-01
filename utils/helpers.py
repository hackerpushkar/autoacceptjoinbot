import html
import re
from typing import Dict, Tuple, Optional, List
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


def parse_buttons_and_clean_text(
    raw_text: str,
    user: User,
    chat_title: str
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Extracts custom inline buttons from the text and returns (cleaned_text, inline_keyboard).
    
    Supported button formats:
    - [Button Text - https://link.com]
    - [Button Text | https://link.com]
    - [Button Text: https://link.com]
    - [Btn 1 - https://link1.com][Btn 2 - https://link2.com]
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

        # Check if line contains button markers inside brackets
        # Case 1: [Btn 1 - Link1][Btn 2 - Link2] or [Btn 1 - Link1] | [Btn 2 - Link2]
        bracket_blocks = re.findall(r"\[([^\[\]]+)\]", stripped)
        if bracket_blocks:
            row: List[InlineKeyboardButton] = []
            is_button_line = False

            for block in bracket_blocks:
                # Inside a bracket block, check if there are pipe-separated sub-buttons: "Btn 1 - URL1 | Btn 2 - URL2"
                # But careful: URL could have query params without spaces around pipe
                sub_items = [block]
                if " | " in block:
                    sub_items = block.split(" | ")
                elif " || " in block:
                    sub_items = block.split(" || ")

                for item in sub_items:
                    # Match "Button Text - URL" or "Button Text : URL" or "Button Text -> URL"
                    pair = re.split(r"\s+(?:[-|:]|->)\s+", item.strip(), maxsplit=1)
                    if len(pair) == 2:
                        btn_text, btn_url = pair[0].strip(), pair[1].strip()
                        # Check if URL looks like a URL / link
                        if btn_url.startswith(("http://", "https://", "tg://", "t.me/")):
                            is_button_line = True
                            # Apply variable replacements to button text
                            clean_btn_text = btn_text
                            for k, v in var_map.items():
                                clean_btn_text = clean_btn_text.replace(k, v)
                            clean_btn_text = re.sub(r"<[^>]+>", "", clean_btn_text)

                            clean_url = btn_url
                            if clean_url.startswith("t.me/"):
                                clean_url = "https://" + clean_url

                            row.append(InlineKeyboardButton(text=clean_btn_text, url=clean_url))

            if is_button_line and row:
                keyboard_rows.append(row)
            else:
                cleaned_lines.append(line)
        else:
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


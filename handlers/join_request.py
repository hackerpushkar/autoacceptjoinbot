import telegram.error
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from config import logger, DEFAULT_WELCOME_MESSAGE
from database.db import (
    add_or_update_user,
    add_or_update_chat,
    get_chat,
    log_join_request
)
from utils.helpers import format_welcome_message


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming ChatJoinRequest updates to auto-approve users."""
    join_request = update.chat_join_request
    if not join_request:
        return

    chat = join_request.chat
    user = join_request.from_user

    logger.info(f"Received join request from {user.id} (@{user.username or 'no_user'}) for chat {chat.id} ({chat.title})")

    # 1. Update database records
    await add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    await add_or_update_chat(chat.id, chat.title or "Untitled Chat", chat.type)

    # 2. Check chat settings
    chat_data = await get_chat(chat.id)
    auto_accept = chat_data.get("auto_accept", 1) if chat_data else 1
    welcome_enabled = chat_data.get("welcome_enabled", 1) if chat_data else 1
    custom_welcome = chat_data.get("custom_welcome_message") if chat_data else None

    if auto_accept == 0:
        logger.info(f"Auto-accept is disabled for chat {chat.id}. Skipping approval.")
        return

    # 3. Approve join request
    try:
        await context.bot.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        await log_join_request(user.id, chat.id, status="approved")
        logger.info(f"Successfully approved join request for {user.id} in chat {chat.id}")
    except telegram.error.Forbidden:
        logger.error(f"Failed to approve {user.id}: Bot lacks admin rights in chat {chat.id}")
        return
    except telegram.error.TelegramError as e:
        logger.error(f"Telegram error while approving join request for {user.id}: {e}")
        return

    # 4. Send Welcome Direct Message (if enabled)
    if welcome_enabled == 1:
        welcome_template = custom_welcome if custom_welcome else DEFAULT_WELCOME_MESSAGE
        media_file_id = chat_data.get("custom_welcome_media") if chat_data else None
        media_type = chat_data.get("custom_welcome_media_type") if chat_data else None

        welcome_text, welcome_keyboard = parse_buttons_and_clean_text(
            raw_text=welcome_template,
            user=user,
            chat_title=chat.title or "our community"
        )

        try:
            if media_file_id and media_type == "photo":
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media_file_id,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=welcome_keyboard
                )
            elif media_file_id and media_type == "video":
                await context.bot.send_video(
                    chat_id=user.id,
                    video=media_file_id,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=welcome_keyboard
                )
            elif media_file_id and media_type == "animation":
                await context.bot.send_animation(
                    chat_id=user.id,
                    animation=media_file_id,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=welcome_keyboard
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=welcome_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=welcome_keyboard
                )
            logger.info(f"Sent welcome DM (with buttons/media) to user {user.id}")
        except telegram.error.Forbidden:
            logger.debug(f"Could not send DM to {user.id} (user has not started bot or blocked it).")
        except telegram.error.TelegramError as e:
            logger.warning(f"Failed to send welcome DM to {user.id}: {e}")


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added or updated as admin in channels/groups."""
    chat_member = update.my_chat_member
    if not chat_member:
        return

    chat = chat_member.chat
    new_status = chat_member.new_chat_member.status

    if new_status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        logger.info(f"Bot was added/promoted as admin in {chat.type} '{chat.title}' ({chat.id})")
        await add_or_update_chat(chat.id, chat.title or "Untitled Chat", chat.type)
    elif new_status in [ChatMember.LEFT, ChatMember.BANNED]:
        logger.info(f"Bot was removed from {chat.type} '{chat.title}' ({chat.id})")

import os
import html
import telegram.error
from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import logger, DEFAULT_WELCOME_MESSAGE
from database.db import (
    add_or_update_user,
    add_or_update_chat,
    delete_chat,
    get_chat,
    log_join_request,
    add_delayed_approval
)
from utils.helpers import parse_buttons_and_clean_text, format_welcome_message, send_safe_welcome_dm
from utils.force_sub import check_channel_membership
from keyboards.inline import get_channel_force_join_request_keyboard


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

    # 2.5 Check per-chat force join requirement
    force_sub_enabled = chat_data.get("force_sub_enabled", 0) if chat_data else 0
    force_sub_channels = chat_data.get("force_sub_channels") if chat_data else None

    if force_sub_enabled == 1 and force_sub_channels:
        channel_list = [c.strip() for c in force_sub_channels.split(",") if c.strip()]
        unsubscribed = []
        for raw_ch in channel_list:
            is_m, title, link = await check_channel_membership(context.bot, user.id, raw_ch)
            if not is_m:
                unsubscribed.append({
                    "channel": raw_ch,
                    "title": title,
                    "url": link if link else "https://t.me/"
                })

        if unsubscribed:
            logger.info(f"User {user.id} has not joined {len(unsubscribed)} required channels for chat {chat.id}. Sending force join DM.")
            chat_name = chat.title or "our channel"
            force_text = (
                f"⚠️ <b>Action Required to Join {html.escape(chat_name)}!</b>\n\n"
                f"To be accepted into <b>{html.escape(chat_name)}</b>, you must first join our partner channel(s) below:\n\n"
                f"👉 <i>Please join all channels below and tap <b>'🔄 Verify & Join'</b> to get approved automatically!</i>"
            )
            force_keyboard = get_channel_force_join_request_keyboard(chat.id, unsubscribed, bot_username=context.bot.username)
            has_custom_media = bool(chat_data and chat_data.get("custom_welcome_media"))
            banner_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "force_join_banner.png")

            try:
                if has_custom_media and os.path.exists(banner_path):
                    with open(banner_path, "rb") as banner_file:
                        await context.bot.send_photo(
                            chat_id=user.id,
                            photo=banner_file,
                            caption=force_text,
                            parse_mode="HTML",
                            reply_markup=force_keyboard
                        )
                else:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=force_text,
                        parse_mode="HTML",
                        reply_markup=force_keyboard
                    )
                logger.info(f"Sent force join DM (with_banner={has_custom_media}) to user {user.id} for chat {chat.id}")
            except telegram.error.Forbidden:
                logger.debug(f"Could not deliver force join DM to {user.id} (user has not started bot).")
            except Exception as e:
                logger.warning(f"Error sending force join DM to {user.id}: {e}")

            # If Send Only mode is active, schedule delayed auto-approval
            if chat_data and chat_data.get("send_only_enabled") == 1:
                delay_sec = chat_data.get("send_only_delay", 86400)
                await add_delayed_approval(chat_id=chat.id, user_id=user.id, delay_seconds=delay_sec)
                logger.info(f"Scheduled Send Only delayed approval for user {user.id} in chat {chat.id} in {delay_sec}s")

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

        sent = await send_safe_welcome_dm(
            bot=context.bot,
            user_id=user.id,
            text=welcome_text,
            keyboard=welcome_keyboard,
            media_file_id=media_file_id,
            media_type=media_type
        )
        if sent:
            logger.info(f"Sent welcome DM (with buttons/media) to user {user.id}")
        else:
            logger.debug(f"Could not deliver welcome DM to user {user.id} (user may not have started bot).")


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added or updated as admin in channels/groups."""
    chat_member = update.my_chat_member
    if not chat_member:
        return

    chat = chat_member.chat
    new_status = chat_member.new_chat_member.status

    if new_status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        owner_user = chat_member.from_user
        owner_id = owner_user.id if owner_user else None
        logger.info(f"Bot was added/promoted as admin in {chat.type} '{chat.title}' ({chat.id}) by user {owner_id}")
        await add_or_update_chat(chat.id, chat.title or "Untitled Chat", chat.type, owner_id=owner_id)

        if owner_user:
            await add_or_update_user(owner_user.id, owner_user.username, owner_user.first_name, owner_user.last_name)
            try:
                msg = (
                    f"🎉 <b>Bot Connected Successfully!</b>\n\n"
                    f"I am now active in: <b>{html.escape(chat.title or 'your chat')}</b>\n"
                    f"Auto-accept is <b>Enabled 🟢</b> by default.\n\n"
                    f"You can configure settings, welcome messages, and force join anytime by clicking below:"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Configure Chat", callback_data=f"chat_detail:{chat.id}")],
                    [InlineKeyboardButton("📊 My Channels", callback_data="nav_channels")]
                ])
                await context.bot.send_message(chat_id=owner_user.id, text=msg, parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                logger.debug(f"Could not send DM to chat owner {owner_user.id}: {e}")

    elif new_status in [ChatMember.LEFT, ChatMember.BANNED]:
        logger.info(f"Bot was removed from {chat.type} '{chat.title}' ({chat.id})")
        await delete_chat(chat.id)

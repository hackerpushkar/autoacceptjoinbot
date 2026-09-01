import html
import telegram.error
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from telegram.ext import ContextTypes
from config import is_admin, ADMIN_IDS, logger, DEFAULT_WELCOME_MESSAGE
from database.db import (
    add_or_update_user,
    get_chat,
    log_join_request,
    mark_delayed_approval_completed
)
from keyboards.inline import (
    get_start_keyboard,
    get_help_keyboard,
    get_back_to_help_keyboard,
    get_back_to_start_keyboard,
    get_about_keyboard,
    get_more_info_keyboard,
    get_developer_info_keyboard,
    get_gift_keyboard,
    get_info_subpage_keyboard,
    get_force_sub_keyboard,
    get_channel_force_join_request_keyboard
)
from utils.force_sub import (
    get_unsubscribed_channels,
    get_force_sub_message,
    check_channel_membership
)
from utils.helpers import parse_buttons_and_clean_text, send_safe_welcome_dm


def get_start_text(user_first_name: str, bot_username: str) -> str:
    """Generate rich formatted start text."""
    safe_name = html.escape(user_first_name or "there")
    return (
        f"👋 <b>Welcome, {safe_name}!</b>\n\n"
        f"🤖 I am the <b>Telegram Auto-Accept Join Request Bot</b>.\n\n"
        f"✨ <b>What I do:</b>\n"
        f"• ⚡ <b>Instant Auto-Approval</b>: Automatically accept join requests for your channels & groups.\n"
        f"• 💌 <b>Personalized Welcome DMs</b>: Send direct messages with custom formatting to every joining member.\n"
        f"• 📊 <b>Live Analytics</b>: Monitor acceptance metrics, member counts, and active chats.\n"
        f"• ⚙️ <b>Granular Controls</b>: Configure auto-accept and welcome messages individually per channel.\n\n"
        f"🚀 <i>Tap a button below to get started!</i>"
    )


async def send_channel_welcome_for_user(bot, user, chat_id: int) -> bool:
    """Send channel owner's customized welcome message with media and buttons to user."""
    chat_data = await get_chat(chat_id)
    chat_title = chat_data.get("title") if (chat_data and chat_data.get("title")) else "our channel"
    welcome_template = (chat_data.get("custom_welcome_message") if chat_data else None) or DEFAULT_WELCOME_MESSAGE
    media_file_id = chat_data.get("custom_welcome_media") if chat_data else None
    media_type = chat_data.get("custom_welcome_media_type") if chat_data else None

    welcome_text, welcome_keyboard = parse_buttons_and_clean_text(
        raw_text=welcome_template,
        user=user,
        chat_title=chat_title
    )

    return await send_safe_welcome_dm(
        bot=bot,
        user_id=user.id,
        text=welcome_text,
        keyboard=welcome_keyboard,
        media_file_id=media_file_id,
        media_type=media_type
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with channel deep-link support."""
    user = update.effective_user
    if not user:
        return

    # Always register/update user in the DB (grows userbase for future broadcasts)
    await add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    bot_username = context.bot.username or "Bot"
    user_is_admin = is_admin(user.id)

    # Check for Channel Deep-Link payload (e.g. welcome_<chat_id>, chat_<chat_id>, start_<chat_id>, c_<chat_id>, test_<chat_id>)
    if context.args and len(context.args) > 0:
        arg = context.args[0].strip()
        chat_id = None
        for prefix in ("welcome_", "chat_", "start_", "test_", "c_"):
            if arg.startswith(prefix):
                try:
                    chat_id = int(arg[len(prefix):])
                    break
                except ValueError:
                    pass
        if chat_id is None:
            try:
                chat_id = int(arg)
            except ValueError:
                chat_id = None

        if chat_id is not None:
            # Bypass global force-sub on initial channel greeting and deliver the channel's custom welcome message
            sent = await send_channel_welcome_for_user(context.bot, user, chat_id)
            if sent:
                logger.info(f"Delivered channel welcome DM for chat {chat_id} to user {user.id} via deep-link '{arg}'")
                return
            else:
                logger.warning(f"Could not deliver channel welcome DM for chat {chat_id} to user {user.id}")
                return

    # Check Global Force Subscription for standard start
    unsubscribed = await get_unsubscribed_channels(context.bot, user.id)
    if unsubscribed:
        text = get_force_sub_message(user.first_name, unsubscribed)
        keyboard = get_force_sub_keyboard(unsubscribed)
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    text = get_start_text(user.first_name, bot_username)
    keyboard = get_start_keyboard(bot_username, is_user_admin=user_is_admin)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📚 <b>Setup & Help Center</b>\n\n"
        "Follow these 3 easy steps to enable auto-accept for your Channel or Group:\n\n"
        "1️⃣ <b>Add Bot as Administrator</b>: Give permission to <i>Invite Users via Link</i>.\n"
        "2️⃣ <b>Create Join Request Link</b>: Enable <i>'Request Admin Approval'</i> on your invite link.\n"
        "3️⃣ <b>Done!</b>: Any user clicking that link will be instantly approved.\n\n"
        "Select a topic below for detailed instructions:"
    )
    keyboard = get_help_keyboard()

    if update.message:
        await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(help_text, reply_markup=keyboard, parse_mode="HTML")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command."""
    bot_username = context.bot.username or "Bot"
    about_text = (
        "ℹ️ <b>About Auto-Accept Bot</b>\n\n"
        "• <b>Version:</b> 2.0.0 (High Performance Async)\n"
        "• <b>Engine:</b> Python Telegram Bot API & Telethon MTProto\n"
        "• <b>Capabilities:</b> Real-time Join Request Approval, Custom Welcome DMs, SQLite Database, MTProto Backlog Engine, Admin Analytics.\n\n"
        "🛡️ <i>Fast, reliable, and designed to scale seamlessly with large communities.</i>"
    )
    keyboard = get_about_keyboard(bot_username)

    if update.message:
        await update.message.reply_text(about_text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(about_text, reply_markup=keyboard, parse_mode="HTML")


async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle navigation callbacks for regular users."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    user = query.from_user
    if user:
        await add_or_update_user(user.id, user.username, user.first_name, user.last_name)

    bot_username = context.bot.username or "Bot"
    user_is_admin = is_admin(user.id) if user else False

    if data == "verify_force_sub":
        unsubscribed = await get_unsubscribed_channels(context.bot, user.id)
        if unsubscribed:
            await query.answer(
                "⚠️ You haven't joined all required channels yet!\n\nPlease join and click Verify again.",
                show_alert=True
            )
            text = get_force_sub_message(user.first_name, unsubscribed)
            keyboard = get_force_sub_keyboard(unsubscribed)
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
            return
        else:
            await query.answer("🎉 Verification successful! Welcome aboard.")
            text = get_start_text(user.first_name, bot_username)
            keyboard = get_start_keyboard(bot_username, is_user_admin=user_is_admin)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            return

    elif data.startswith("verify_chat_join:"):
        chat_id = int(data.split(":")[1])
        await add_or_update_user(user.id, user.username, user.first_name, user.last_name)
        chat_data = await get_chat(chat_id)
        if not chat_data:
            await query.answer("Chat configuration not found.", show_alert=True)
            return

        force_sub_channels = chat_data.get("force_sub_channels") or ""
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
            await query.answer(
                "⚠️ You haven't joined all required channels yet!\n\nPlease join all channels below and tap Verify & Join again.",
                show_alert=True
            )
            chat_name = chat_data.get("title") or "our channel"
            force_text = (
                f"⚠️ <b>Action Required to Join {html.escape(chat_name)}!</b>\n\n"
                f"To be accepted into <b>{html.escape(chat_name)}</b>, you must first join our partner channel(s) below:\n\n"
                f"👉 <i>Please join all channels below and tap <b>'🔄 Verify & Join'</b> to get approved automatically!</i>"
            )
            keyboard = get_channel_force_join_request_keyboard(chat_id, unsubscribed, bot_username=bot_username)
            try:
                if query.message and query.message.photo:
                    await query.edit_message_caption(force_text, reply_markup=keyboard, parse_mode="HTML")
                else:
                    await query.edit_message_text(force_text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
            return
        else:
            # 1. Approve user's join request in the channel
            try:
                await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user.id)
                await log_join_request(user.id, chat_id, status="approved")
                await mark_delayed_approval_completed(chat_id=chat_id, user_id=user.id, status="approved_manual")
                logger.info(f"Approved join request on verify for user {user.id} in chat {chat_id}")
            except Exception as e:
                logger.warning(f"Failed to approve join request on verify for user {user.id} in chat {chat_id}: {e}")

            chat_title = chat_data.get("title") or "our community"

            # 2. Action 1: Edit the force message in-place to confirm approval
            thank_you_text = (
                f"✅ <b>Thank you for joining our partner channels!</b>\n\n"
                f"🎉 Your request to join <b>{html.escape(chat_title)}</b> has been approved! Welcome aboard. ✨"
            )
            try:
                if query.message and query.message.photo:
                    await query.edit_message_caption(caption=thank_you_text, parse_mode="HTML", reply_markup=None)
                elif query.message:
                    await query.edit_message_text(text=thank_you_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=None)
            except Exception as e:
                logger.warning(f"Could not edit force prompt to thank you message: {e}")

            # 3. Action 2: Start bot & dispatch channel owner's custom welcome message
            sent = await send_channel_welcome_for_user(context.bot, user, chat_id)

            if not sent:
                # If cannot deliver in DM (e.g. cold user), redirect user to bot DM via deep-link
                try:
                    await query.answer(url=f"https://t.me/{bot_username}?start=welcome_{chat_id}")
                    return
                except Exception:
                    pass

            try:
                await query.answer("🎉 Verified! Request approved and welcome message delivered ✨", show_alert=False)
            except Exception:
                pass
            return

    elif data.startswith("test_autostart:"):
        chat_id_str = data.split(":", 1)[1] if ":" in data else ""
        target_chat_id = None
        if chat_id_str:
            try:
                target_chat_id = int(chat_id_str)
            except ValueError:
                target_chat_id = None

        await add_or_update_user(user.id, user.username, user.first_name, user.last_name)

        if target_chat_id:
            chat_data = await get_chat(target_chat_id)
            chat_title = chat_data.get("title") if (chat_data and chat_data.get("title")) else "our channel"
            welcome_template = (chat_data.get("custom_welcome_message") if chat_data else None) or DEFAULT_WELCOME_MESSAGE
            media_file_id = chat_data.get("custom_welcome_media") if chat_data else None
            media_type = chat_data.get("custom_welcome_media_type") if chat_data else None

            welcome_text, welcome_keyboard = parse_buttons_and_clean_text(
                raw_text=welcome_template,
                user=user,
                chat_title=chat_title
            )

            is_photo_msg = bool(query.message and query.message.photo)
            edited = False
            if query.message:
                if is_photo_msg and not media_file_id:
                    try:
                        await query.edit_message_caption(caption=welcome_text, parse_mode="HTML", reply_markup=welcome_keyboard)
                        edited = True
                    except Exception:
                        pass
                elif not is_photo_msg and not media_file_id:
                    try:
                        await query.edit_message_text(text=welcome_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=welcome_keyboard)
                        edited = True
                    except Exception:
                        pass

            if not edited:
                sent = await send_safe_welcome_dm(
                    bot=context.bot,
                    user_id=user.id,
                    text=welcome_text,
                    keyboard=welcome_keyboard,
                    media_file_id=media_file_id,
                    media_type=media_type
                )
                if not sent:
                    # User hasn't started bot in DM yet -> use Telegram's official URL redirect answer
                    bot_user = context.bot.username or "Bot"
                    try:
                        await query.answer(url=f"https://t.me/{bot_user}?start=welcome_{target_chat_id}")
                        return
                    except Exception:
                        pass

            try:
                await query.answer("🚀 Access Granted! Welcome aboard ✨", show_alert=False)
            except Exception:
                pass
        else:
            try:
                await query.answer()
            except Exception:
                pass
            text = get_start_text(user.first_name, bot_username)
            keyboard = get_start_keyboard(bot_username, is_user_admin=user_is_admin)
            try:
                await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send start message on test_autostart: {e}")
        return

    await query.answer()

    if data == "nav_start":
        unsubscribed = await get_unsubscribed_channels(context.bot, user.id)
        if unsubscribed:
            text = get_force_sub_message(user.first_name, unsubscribed)
            keyboard = get_force_sub_keyboard(unsubscribed)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            return

        text = get_start_text(user.first_name, bot_username)
        keyboard = get_start_keyboard(bot_username, is_user_admin=user_is_admin)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


    elif data == "nav_help":
        await help_command(update, context)

    elif data == "nav_about":
        await about_command(update, context)

    elif data == "about_more_info":
        text = (
            "ℹ️ <b>More Information</b>\n\n"
            "Select an option below to learn more about the developers, administrators, or share the bot:"
        )
        await query.edit_message_text(text, reply_markup=get_more_info_keyboard(bot_username), parse_mode="HTML")

    elif data == "info_developer":
        dev_username = "pushkarsingh0911"
        dev_email = "spushkar812@gmail.com"
        dev_role = "Founder of Digital Quests"
        dev_name = "Pushkar Singh"
        dev_bio = dev_role

        try:
            dev_chat = await context.bot.get_chat(f"@{dev_username}")
            if dev_chat:
                first = html.escape(dev_chat.first_name or "")
                last = html.escape(dev_chat.last_name or "")
                resolved_name = f"{first} {last}".strip()
                if resolved_name:
                    dev_name = resolved_name
                if getattr(dev_chat, "bio", None):
                    dev_bio = f"{dev_role} • {html.escape(dev_chat.bio)}"
        except Exception as e:
            logger.debug(f"Could not fetch developer Telegram profile dynamically: {e}")

        text = (
            "👨‍💻 <b>Developer Information</b>\n\n"
            f"👤 <b>Name:</b> <a href=\"https://t.me/{dev_username}\">{dev_name}</a>\n"
            f"🏷️ <b>Username:</b> @{dev_username}\n"
            f"💼 <b>Role:</b> {dev_role}\n"
            f"📧 <b>Email:</b> <code>{dev_email}</code>\n"
            f"📝 <b>Bio:</b> {dev_bio}\n\n"
            f"💬 <i>Feel free to get in touch for custom bot development, integrations, or support!</i>"
        )
        await query.edit_message_text(text, reply_markup=get_developer_info_keyboard(), parse_mode="HTML")

    elif data == "info_gift":
        text = (
            "🎁 <b>Special Gift For You!</b>\n\n"
            "🚀 <b>Want To Make Your Own Auto-Accept Bot?</b>\n\n"
            "Build and deploy your own high-speed Telegram Join Request Bot in seconds with ready-to-use templates — no coding required!\n\n"
            "Would you like to get your bot template now?"
        )
        await query.edit_message_text(text, reply_markup=get_gift_keyboard(), parse_mode="HTML")

    elif data == "info_admin":
        admin_cards = []
        for admin_id in ADMIN_IDS:
            try:
                admin_chat = await context.bot.get_chat(admin_id)
                first_name = html.escape(admin_chat.first_name or "")
                last_name = html.escape(admin_chat.last_name or "")
                full_name = f"{first_name} {last_name}".strip() or "Administrator"
                username_str = f"@{admin_chat.username}" if admin_chat.username else "No username"
                bio = html.escape(admin_chat.bio) if getattr(admin_chat, "bio", None) else "No bio provided"
                contact_link = f"https://t.me/{admin_chat.username}" if admin_chat.username else f"tg://user?id={admin_id}"

                card = (
                    f"👤 <b>Name:</b> <a href=\"{contact_link}\">{full_name}</a>\n"
                    f"🏷️ <b>Username:</b> {username_str}\n"
                    f"🆔 <b>ID:</b> <code>{admin_id}</code>\n"
                    f"📝 <b>Bio:</b> {bio}"
                )
                admin_cards.append(card)
            except Exception as e:
                logger.debug(f"Could not fetch full admin details for {admin_id}: {e}")
                card = (
                    f"👤 <b>Administrator</b>\n"
                    f"🆔 <b>ID:</b> <code>{admin_id}</code>\n"
                    f"🔗 <b>Profile:</b> <a href=\"tg://user?id={admin_id}\">Direct Contact</a>"
                )
                admin_cards.append(card)

        if not admin_cards:
            text = (
                "👑 <b>Admin Information</b>\n\n"
                "ℹ️ No administrators are currently configured."
            )
        else:
            joined_cards = "\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join(admin_cards)
            text = (
                "👑 <b>Admin Information</b>\n\n"
                f"{joined_cards}"
            )

        await query.edit_message_text(text, reply_markup=get_info_subpage_keyboard(), parse_mode="HTML")

    elif data == "help_step_admin":
        text = (
            "🔑 <b>Step 1: Admin Permissions</b>\n\n"
            "1. Open your Channel or Group info page in Telegram.\n"
            "2. Go to <b>Administrators</b> ➔ <b>Add Administrator</b>.\n"
            "3. Search for this bot and add it.\n"
            "4. Make sure to turn <b>ON</b> the following permission:\n"
            "   ✅ <b>Invite Users via Link / Add Members</b>\n"
            "   ✅ <b>Manage Join Requests</b>\n\n"
            "<i>(Other permissions like Post Messages can remain off if not required)</i>"
        )
        await query.edit_message_text(text, reply_markup=get_back_to_help_keyboard(), parse_mode="HTML")

    elif data == "help_step_link":
        text = (
            "🔗 <b>Step 2: Create a Join Request Invite Link</b>\n\n"
            "1. Open your Channel or Group settings.\n"
            "2. Navigate to <b>Invite Links</b> ➔ <b>Create a New Link</b>.\n"
            "3. Enable the toggle switch: <b>'Request Admin Approval'</b> (or <i>'Approve New Members'</i>).\n"
            "4. Copy your newly created invite link and share it anywhere!\n\n"
            "Whenever someone clicks this link, Telegram creates a join request, which this bot approves instantly."
        )
        await query.edit_message_text(text, reply_markup=get_back_to_help_keyboard(), parse_mode="HTML")

    elif data == "help_step_dm":
        text = (
            "💬 <b>Step 3: Custom Welcome Direct Messages</b>\n\n"
            "You can configure a customized DM that users receive upon approval.\n\n"
            "<b>Supported Placeholders:</b>\n"
            "• <code>{name}</code> - Full name of the user\n"
            "• <code>{first_name}</code> - First name\n"
            "• <code>{username}</code> - @username\n"
            "• <code>{mention}</code> - Clickable user mention link\n"
            "• <code>{chat_title}</code> - Name of the channel/group\n"
            "• <code>{user_id}</code> - User's Telegram ID\n\n"
            "You can manage this from <b>'My Channels'</b> or via the <code>/settings</code> command."
        )
        await query.edit_message_text(text, reply_markup=get_back_to_help_keyboard(), parse_mode="HTML")

    elif data == "help_step_faq":
        text = (
            "❓ <b>Frequently Asked Questions (FAQ)</b>\n\n"
            "<b>Q: Why didn't a user receive the Welcome DM?</b>\n"
            "A: Telegram privacy limits bots from initiating DMs if the user has strict privacy settings or has never clicked /start in the bot before.\n\n"
            "<b>Q: Will the bot approve existing requests?</b>\n"
            "A: The bot approves new incoming requests in real-time as they arrive.\n\n"
            "<b>Q: Can I turn off welcome messages?</b>\n"
            "A: Yes! You can toggle welcome DMs on/off per channel in the settings menu."
        )
        await query.edit_message_text(text, reply_markup=get_back_to_help_keyboard(), parse_mode="HTML")

import html
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
import telegram.error
from config import is_admin, logger, DEFAULT_WELCOME_MESSAGE
from database.db import (
    get_analytics,
    get_all_chats,
    get_chat,
    toggle_chat_auto_accept,
    toggle_chat_welcome,
    set_chat_custom_welcome,
    get_all_user_ids
)
from keyboards.inline import (
    get_admin_main_keyboard,
    get_channels_keyboard,
    get_chat_settings_keyboard,
    get_chat_welcome_menu_keyboard,
    get_approve_pending_confirm_keyboard,
    get_broadcast_confirm_keyboard,
    get_back_to_start_keyboard,
    get_stats_keyboard
)
from utils.helpers import parse_buttons_and_clean_text
from services.backlog_cleaner import (
    is_backlog_engine_available,
    get_pending_requests_count,
    approve_all_pending_requests
)

# Conversation States
WAITING_WELCOME_MSG = 1
WAITING_BROADCAST_MSG = 2


# ==========================================
# COMMAND HANDLERS
# ==========================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        text = "⛔ <b>Access Denied</b>: This command is reserved for Bot Administrators."
        if update.message:
            await update.message.reply_text(text, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.answer("Access Denied", show_alert=True)
        return

    text = (
        "⚙️ <b>Admin Control Panel</b>\n\n"
        "Welcome to the master control dashboard. Choose an option below to manage bot settings, monitor channels, or view metrics."
    )
    keyboard = get_admin_main_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command or callback."""
    user = update.effective_user
    if not user:
        return

    stats = await get_analytics()

    text = (
        "📊 <b>Bot Live Analytics</b>\n\n"
        f"⚡ <b>Total Requests Approved:</b> <code>{stats['total_approved']:,}</code>\n"
        f"📅 <b>Approved Today:</b> <code>{stats['today_approved']:,}</code>\n"
        f"📢 <b>Monitored Chats/Channels:</b> <code>{stats['total_chats']:,}</code>\n"
        f"👥 <b>Total Registered Users:</b> <code>{stats['total_users']:,}</code>\n\n"
        f"🟢 <b>Bot Status:</b> Operational & Polling"
    )

    keyboard = get_stats_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /channels command or callback."""
    user = update.effective_user
    if not user:
        return

    chats = await get_all_chats()
    if not chats:
        text = (
            "📋 <b>Monitored Channels & Groups</b>\n\n"
            "No channels or groups have been connected yet.\n\n"
            "👉 <i>Add the bot as an Administrator in your Channel/Group to get started!</i>"
        )
        keyboard = get_back_to_start_keyboard()
    else:
        text = (
            f"📋 <b>Monitored Channels & Groups</b> ({len(chats)} total)\n\n"
            "🟢 = Auto-Accept ON | 🔴 = Auto-Accept OFF\n"
            "Select a chat below to configure its settings:"
        )
        keyboard = get_channels_keyboard(chats, page=0)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==========================================
# VIEW BUILDERS
# ==========================================

def build_chat_settings_view(chat_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Generate text and keyboard for main chat settings view."""
    chat_id = chat_data["chat_id"]
    title = chat_data.get("title") or f"Chat {chat_id}"
    auto_accept = chat_data.get("auto_accept", 1) == 1
    welcome_enabled = chat_data.get("welcome_enabled", 1) == 1
    auto_status = "🟢 Enabled" if auto_accept else "🔴 Disabled"
    welcome_status = "🟢 Enabled" if welcome_enabled else "🔴 Disabled"

    text = (
        f"⚙️ <b>Settings for:</b> {html.escape(title)}\n"
        f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n"
        f"🏷️ <b>Type:</b> {chat_data.get('chat_type', 'channel').capitalize()}\n\n"
        f"• <b>Auto-Accept Requests:</b> {auto_status}\n"
        f"• <b>Welcome Direct Message:</b> {welcome_status}\n\n"
        f"👉 <i>Click <b>'Manage Welcome Message'</b> below to customize text, attach images, or add buttons.</i>"
    )
    keyboard = get_chat_settings_keyboard(
        chat_id=chat_id,
        auto_accept=auto_accept
    )
    return text, keyboard


def build_chat_welcome_menu_view(chat_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Generate text and keyboard for dedicated welcome message manager."""
    chat_id = chat_data["chat_id"]
    title = chat_data.get("title") or f"Chat {chat_id}"
    welcome_enabled = chat_data.get("welcome_enabled", 1) == 1
    welcome_status = "🟢 Enabled" if welcome_enabled else "🔴 Disabled"
    custom_msg = chat_data.get("custom_welcome_message")
    custom_media = chat_data.get("custom_welcome_media_type")

    media_tag = f" <i>[Attached {custom_media.capitalize()} 🖼️]</i>" if custom_media else ""
    msg_preview = html.escape(custom_msg) + media_tag if custom_msg else f"<i>(Using Default Welcome Message)</i>{media_tag}"

    text = (
        f"💌 <b>Manage Welcome Message</b>\n\n"
        f"📢 <b>Channel:</b> {html.escape(title)}\n"
        f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n\n"
        f"• <b>Welcome DM Status:</b> {welcome_status}\n"
        f"• <b>Current Welcome Message:</b>\n{msg_preview}\n\n"
        f"👇 <i>Choose an action below:</i>"
    )
    keyboard = get_chat_welcome_menu_keyboard(
        chat_id=chat_id,
        welcome_enabled=welcome_enabled
    )
    return text, keyboard


# ==========================================
# CALLBACK HANDLER
# ==========================================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin-specific callbacks."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    user = query.from_user

    if data == "nav_admin_panel":
        await query.answer()
        await admin_command(update, context)

    elif data == "admin_stats":
        await query.answer()
        await stats_command(update, context)

    elif data == "nav_channels":
        await query.answer()
        await channels_command(update, context)

    elif data.startswith("channels_page:"):
        await query.answer()
        page = int(data.split(":")[1])
        chats = await get_all_chats()
        text = (
            f"📋 <b>Monitored Channels & Groups</b> ({len(chats)} total)\n\n"
            "🟢 = Auto-Accept ON | 🔴 = Auto-Accept OFF\n"
            "Select a chat below to configure its settings:"
        )
        try:
            await query.edit_message_text(text, reply_markup=get_channels_keyboard(chats, page=page), parse_mode="HTML")
        except telegram.error.BadRequest:
            pass

    elif data.startswith("chat_detail:"):
        await query.answer()
        chat_id = int(data.split(":")[1])
        chat_data = await get_chat(chat_id)
        if not chat_data:
            await query.answer("Chat not found in database.", show_alert=True)
            return

        text, keyboard = build_chat_settings_view(chat_data)
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except telegram.error.BadRequest:
            pass

    elif data.startswith("chat_welcome_menu:"):
        await query.answer()
        chat_id = int(data.split(":")[1])
        chat_data = await get_chat(chat_id)
        if not chat_data:
            await query.answer("Chat not found in database.", show_alert=True)
            return

        text, keyboard = build_chat_welcome_menu_view(chat_data)
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except telegram.error.BadRequest:
            pass

    elif data.startswith("chat_toggle_auto:"):
        chat_id = int(data.split(":")[1])
        new_state = await toggle_chat_auto_accept(chat_id)
        chat_data = await get_chat(chat_id)
        if chat_data:
            text, keyboard = build_chat_settings_view(chat_data)
            status_text = "Auto-Accept: ON ✅" if new_state else "Auto-Accept: OFF ❌"
            await query.answer(status_text)
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            except telegram.error.BadRequest:
                pass

    elif data.startswith("chat_toggle_welcome:"):
        chat_id = int(data.split(":")[1])
        new_state = await toggle_chat_welcome(chat_id)
        chat_data = await get_chat(chat_id)
        if chat_data:
            text, keyboard = build_chat_welcome_menu_view(chat_data)
            status_text = "Welcome DM: ON ✅" if new_state else "Welcome DM: OFF ❌"
            await query.answer(status_text)
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            except telegram.error.BadRequest:
                pass

    elif data.startswith("chat_preview_welcome:"):
        chat_id = int(data.split(":")[1])
        chat_data = await get_chat(chat_id)
        if not chat_data:
            await query.answer("Chat not found.", show_alert=True)
            return

        welcome_template = chat_data.get("custom_welcome_message") or DEFAULT_WELCOME_MESSAGE
        media_file_id = chat_data.get("custom_welcome_media")
        media_type = chat_data.get("custom_welcome_media_type")

        preview_text, preview_kb = parse_buttons_and_clean_text(
            raw_text=welcome_template,
            user=user,
            chat_title=chat_data.get("title") or "Sample Channel"
        )

        try:
            if media_file_id and media_type == "photo":
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media_file_id,
                    caption=f"👁️ <b>[Live Preview of Welcome DM]</b>\n\n{preview_text}",
                    parse_mode="HTML",
                    reply_markup=preview_kb
                )
            elif media_file_id and media_type == "video":
                await context.bot.send_video(
                    chat_id=user.id,
                    video=media_file_id,
                    caption=f"👁️ <b>[Live Preview of Welcome DM]</b>\n\n{preview_text}",
                    parse_mode="HTML",
                    reply_markup=preview_kb
                )
            elif media_file_id and media_type == "animation":
                await context.bot.send_animation(
                    chat_id=user.id,
                    animation=media_file_id,
                    caption=f"👁️ <b>[Live Preview of Welcome DM]</b>\n\n{preview_text}",
                    parse_mode="HTML",
                    reply_markup=preview_kb
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"👁️ <b>[Live Preview of Welcome DM]</b>\n\n{preview_text}",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=preview_kb
                )
            await query.answer("Preview sent above! 👁️")
        except Exception as e:
            logger.error(f"Error sending preview: {e}")
            await query.answer("Failed to send preview. Check bot permissions.", show_alert=True)

    elif data.startswith("chat_reset_welcome:"):
        chat_id = int(data.split(":")[1])
        await set_chat_custom_welcome(chat_id, None, None, None)
        chat_data = await get_chat(chat_id)
        if chat_data:
            text, keyboard = build_chat_welcome_menu_view(chat_data)
            await query.answer("Welcome message & media reset to default! ✅", show_alert=True)
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            except telegram.error.BadRequest:
                pass

    elif data.startswith("chat_prompt_pending:"):
        chat_id = int(data.split(":")[1])
        chat_data = await get_chat(chat_id)
        if not chat_data:
            await query.answer("Chat not found.", show_alert=True)
            return

        title = chat_data.get("title") or f"Chat {chat_id}"

        if not is_backlog_engine_available():
            text = (
                f"⚡ <b>Approve Past / Pending Requests</b>\n\n"
                f"📢 <b>Channel:</b> {html.escape(title)}\n\n"
                f"To approve pending requests that existed <i>before</i> adding the bot, MTProto credentials are required.\n\n"
                f"<b>Quick Setup (2 minutes):</b>\n"
                f"1. Get free <code>TELEGRAM_API_ID</code> & <code>TELEGRAM_API_HASH</code> from <a href=\"https://my.telegram.org\">my.telegram.org</a>.\n"
                f"2. Run <code>python services/session_generator.py</code> in your terminal.\n"
                f"3. Paste the generated <code>SESSION_STRING</code> into your <code>.env</code> file.\n"
                f"4. Restart the bot!\n\n"
                f"<i>(Live real-time approvals for new requests work without this!)</i>"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Chat Settings", callback_data=f"chat_detail:{chat_id}")]
            ])
            await query.answer()
            try:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)
            except telegram.error.BadRequest:
                pass
            return

        await query.answer("Checking pending requests...")
        count = await get_pending_requests_count(chat_id)
        count_display = f"<code>{count}</code>" if count > 0 else "<i>Scanning channel...</i>"

        text = (
            f"⚡ <b>Approve All Pending Requests</b>\n\n"
            f"📢 <b>Channel:</b> {html.escape(title)}\n"
            f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n\n"
            f"⏳ <b>Pending Requests Found:</b> {count_display}\n\n"
            f"Are you sure you want to approve all backlog join requests for this channel now?"
        )
        keyboard = get_approve_pending_confirm_keyboard(chat_id)
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except telegram.error.BadRequest:
            pass

    elif data.startswith("chat_exec_pending:"):
        chat_id = int(data.split(":")[1])
        chat_data = await get_chat(chat_id)
        title = chat_data.get("title") if chat_data else f"Chat {chat_id}"

        await query.answer("🚀 Starting batch approvals...")
        await query.edit_message_text(
            f"⏳ <b>Approving backlog requests for '{html.escape(title)}'...</b>\n\nPlease wait while requests are processed.",
            parse_mode="HTML"
        )

        last_update = [0.0]

        async def on_progress(current, total):
            now = asyncio.get_event_loop().time()
            if now - last_update[0] >= 1.5:
                last_update[0] = now
                try:
                    await query.edit_message_text(
                        f"⚡ <b>Approving Backlog Requests...</b>\n\n"
                        f"📢 <b>Channel:</b> {html.escape(title)}\n"
                        f"• Processed: <code>{current} / {total}</code>\n\n"
                        f"<i>Please do not close the bot. Processing with anti-flood protection...</i>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        res = await approve_all_pending_requests(
            chat_id=chat_id,
            bot_context=context,
            progress_callback=on_progress
        )

        if "error" in res and res.get("approved", 0) == 0:
            summary = (
                f"❌ <b>Batch Approval Notice</b>\n\n"
                f"📢 <b>Channel:</b> {html.escape(title)}\n"
                f"• Error details: <code>{html.escape(str(res['error']))}</code>\n\n"
                f"Ensure the MTProto account has Admin rights to Invite Users in this channel."
            )
        else:
            summary = (
                f"✅ <b>Batch Approval Completed!</b>\n\n"
                f"📢 <b>Channel:</b> {html.escape(title)}\n"
                f"• <b>Approved & Added:</b> <code>{res.get('approved', 0)}</code>\n"
                f"• <b>Failed / Expired:</b> <code>{res.get('failed', 0)}</code>\n"
                f"• <b>Total Processed:</b> <code>{res.get('total', 0)}</code>\n\n"
                f"All pending requests have been approved!"
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Chat Settings", callback_data=f"chat_detail:{chat_id}")]
        ])
        try:
            await query.edit_message_text(summary, reply_markup=keyboard, parse_mode="HTML")
        except telegram.error.BadRequest:
            pass


# ==========================================
# CUSTOM WELCOME DM CONVERSATION (MEDIA & BUTTONS)
# ==========================================

async def prompt_custom_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to input custom welcome message text, image, and inline buttons."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()

    chat_id = int(query.data.split(":")[1])
    context.user_data["edit_chat_id"] = chat_id

    text = (
        "✏️ <b>Set Custom Welcome Message</b>\n\n"
        "Send your new welcome message now! You can send <b>Text Only</b> or <b>Attach an Image / GIF</b> with a caption.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>1. Dynamic Placeholders:</b>\n"
        "• <code>{name}</code> - Full name of the member\n"
        "• <code>{first_name}</code> - First name\n"
        "• <code>{username}</code> - @username\n"
        "• <code>{mention}</code> - Clickable mention\n"
        "• <code>{chat_title}</code> - Channel/Group Title\n"
        "• <code>{user_id}</code> - User Telegram ID\n\n"
        "🔘 <b>2. Adding Inline Buttons:</b>\n"
        "Add button links anywhere in your text using this syntax:\n"
        "• Single button:\n"
        "  <code>[👉 Join VIP - https://t.me/yourchannel]</code>\n"
        "• Multiple buttons in same row:\n"
        "  <code>[🌐 Website - https://mysite.com | 💬 Support - https://t.me/support]</code>\n\n"
        "🖼️ <b>3. Adding an Image / Video:</b>\n"
        "Simply send a photo in this chat and write your welcome text + buttons in the <b>Caption</b>!\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Send /cancel to abort.</i>"
    )
    await query.edit_message_text(text, parse_mode="HTML")
    return WAITING_WELCOME_MSG


async def save_custom_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save custom welcome text, image/media, and buttons received from user."""
    chat_id = context.user_data.get("edit_chat_id")
    msg = update.message
    if not chat_id or not msg:
        return ConversationHandler.END

    raw_text = ""
    media_file_id = None
    media_type = None

    if msg.photo:
        media_file_id = msg.photo[-1].file_id
        media_type = "photo"
        raw_text = msg.caption or ""
    elif msg.video:
        media_file_id = msg.video.file_id
        media_type = "video"
        raw_text = msg.caption or ""
    elif msg.animation:
        media_file_id = msg.animation.file_id
        media_type = "animation"
        raw_text = msg.caption or ""
    elif msg.text:
        raw_text = msg.text

    await set_chat_custom_welcome(
        chat_id=chat_id,
        message=raw_text if raw_text else None,
        media_file_id=media_file_id,
        media_type=media_type
    )

    media_info = f" with attached {media_type} 🖼️" if media_type else ""
    success_text = (
        f"✅ <b>Custom Welcome Message successfully saved for Chat ID <code>{chat_id}</code>{media_info}!</b>\n\n"
        f"New members joining this chat will now automatically receive this custom welcome DM with your configured buttons and media."
    )

    await msg.reply_text(
        success_text,
        parse_mode="HTML",
        reply_markup=get_back_to_start_keyboard()
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel active conversation."""
    if update.message:
        await update.message.reply_text("❌ Operation cancelled.", reply_markup=get_back_to_start_keyboard())
    elif update.callback_query:
        await update.callback_query.answer("Cancelled")
        await update.callback_query.edit_message_text("❌ Operation cancelled.", reply_markup=get_back_to_start_keyboard())
    return ConversationHandler.END


# ==========================================
# BROADCAST SYSTEM CONVERSATION
# ==========================================

async def prompt_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin for broadcast text."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "📢 <b>Broadcast Announcement</b>\n\n"
        "Please send the message you want to broadcast to all registered bot users.\n\n"
        "You can send text with HTML formatting or media with caption.\n"
        "<i>Send /cancel to abort.</i>"
    )

    if query:
        await query.edit_message_text(text, parse_mode="HTML")
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML")

    return WAITING_BROADCAST_MSG


async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast message, show preview, and ask for confirmation."""
    msg = update.message
    if not msg:
        return ConversationHandler.END

    context.user_data["broadcast_msg_id"] = msg.message_id
    context.user_data["broadcast_from_chat_id"] = msg.chat_id

    total_users = await get_all_user_ids()
    preview_prompt = (
        f"📢 <b>Broadcast Preview</b>\n\n"
        f"Target Audience: <b>{len(total_users)}</b> registered users.\n\n"
        f"Are you sure you want to broadcast this message?"
    )

    await msg.reply_text(preview_prompt, reply_markup=get_broadcast_confirm_keyboard(), parse_mode="HTML")
    return ConversationHandler.END


async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast the message to all registered users."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user_ids = await get_all_user_ids()
    from_chat_id = context.user_data.get("broadcast_from_chat_id")
    msg_id = context.user_data.get("broadcast_msg_id")

    if not from_chat_id or not msg_id:
        await query.edit_message_text("❌ No message found to broadcast.", reply_markup=get_back_to_start_keyboard())
        return

    await query.edit_message_text(f"🚀 Broadcasting message to {len(user_ids)} users... Please wait.")

    success_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=msg_id
            )
            success_count += 1
            await asyncio.sleep(0.05)
        except (telegram.error.Forbidden, telegram.error.TelegramError):
            fail_count += 1

    summary = (
        f"✅ <b>Broadcast Completed!</b>\n\n"
        f"• <b>Delivered Successfully:</b> {success_count}\n"
        f"• <b>Failed / Blocked:</b> {fail_count}\n"
        f"• <b>Total Targeted:</b> {len(user_ids)}"
    )
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=summary,
        reply_markup=get_back_to_start_keyboard(),
        parse_mode="HTML"
    )

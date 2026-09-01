import html
from telegram import Update
from telegram.ext import ContextTypes
from config import is_admin, logger
from database.db import add_or_update_user
from keyboards.inline import (
    get_start_keyboard,
    get_help_keyboard,
    get_back_to_help_keyboard,
    get_back_to_start_keyboard,
    get_about_keyboard,
    get_force_sub_keyboard
)
from utils.force_sub import (
    get_unsubscribed_channels,
    get_force_sub_message
)


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    if not user:
        return

    await add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    bot_username = context.bot.username or "Bot"
    user_is_admin = is_admin(user.id)

    # Check Global Force Subscription
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
    bot_username = context.bot.username or "Bot"
    user_is_admin = is_admin(user.id)

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

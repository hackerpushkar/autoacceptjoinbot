import sys
import asyncio
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ChatMemberHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from config import BOT_TOKEN, logger
from database.db import init_db
from services.delayed_approvals import start_delayed_approvals_worker
from handlers.join_request import handle_join_request, handle_my_chat_member
from handlers.user import (
    start_command,
    help_command,
    about_command,
    user_callback_handler
)
from handlers.admin import (
    admin_command,
    stats_command,
    channels_command,
    admin_callback_handler,
    prompt_custom_welcome,
    save_custom_welcome,
    prompt_force_sub_channels,
    save_force_sub_channels,
    prompt_broadcast,
    preview_broadcast,
    execute_broadcast,
    cancel_conversation,
    WAITING_WELCOME_MSG,
    WAITING_BROADCAST_MSG,
    WAITING_FORCESUB_CHANNELS
)


async def post_init(application):
    """Post initialization: set bot commands and initialize DB."""
    # 1. Initialize SQLite database
    await init_db()

    # 2. Start Delayed Approvals Background Worker
    start_delayed_approvals_worker(application.bot, interval_seconds=30)

    # 3. Register Bot Commands in Telegram UI
    commands = [
        BotCommand("start", "Start the bot & open main menu"),
        BotCommand("help", "Setup instructions & tutorials"),
        BotCommand("channels", "View and manage connected channels"),
        BotCommand("stats", "Live approval statistics & metrics"),
        BotCommand("admin", "Admin control panel"),
        BotCommand("about", "About this bot")
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully in Telegram menu.")
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")


async def error_handler(update, context):
    """Log uncaught errors gracefully."""
    logger.error(f"Uncaught exception occurred: {context.error}", exc_info=context.error)


def main():
    """Main entrypoint for running the bot."""
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error(
            "\n" + "=" * 65 + "\n"
            "❌ ERROR: BOT_TOKEN is missing or not configured!\n"
            "Please create a .env file (or edit .env) and set:\n"
            "BOT_TOKEN=your_telegram_bot_token\n"
            "ADMIN_IDS=your_telegram_user_id\n"
            "=" * 65
        )
        sys.exit(1)

    logger.info("Initializing Telegram Auto Accept Bot...")

    # Build Application
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Error Handler
    app.add_error_handler(error_handler)

    # 1. Join Request and Member update handlers
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # 2. Conversation Handlers
    # Custom Welcome DM Conversation
    welcome_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(prompt_custom_welcome, pattern=r"^chat_edit_welcome:")],
        states={
            WAITING_WELCOME_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, save_custom_welcome)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")
        ],
        per_chat=True
    )
    app.add_handler(welcome_conv_handler)

    # Custom Force Join Channels Conversation
    forcesub_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(prompt_force_sub_channels, pattern=r"^chat_edit_forcesub:")],
        states={
            WAITING_FORCESUB_CHANNELS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_force_sub_channels)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")
        ],
        per_chat=True
    )
    app.add_handler(forcesub_conv_handler)

    # Broadcast Conversation
    broadcast_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", prompt_broadcast),
            CallbackQueryHandler(prompt_broadcast, pattern="^admin_broadcast_prompt$")
        ],
        states={
            WAITING_BROADCAST_MSG: [
                MessageHandler(filters.ALL & ~filters.COMMAND, preview_broadcast)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern="^broadcast_cancel$")
        ],
        per_chat=True
    )
    app.add_handler(broadcast_conv_handler)

    # Broadcast confirmation callbacks
    app.add_handler(CallbackQueryHandler(execute_broadcast, pattern="^broadcast_confirm$"))
    app.add_handler(CallbackQueryHandler(cancel_conversation, pattern="^broadcast_cancel$"))

    # 3. Standard Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("channels", channels_command))

    # 4. User and Admin Callback Query Handlers
    user_patterns = r"^(nav_start|nav_help|nav_about|about_more_info|info_developer|info_admin|info_gift|help_step_admin|help_step_link|help_step_dm|help_step_faq|verify_force_sub|verify_chat_join:|test_autostart:)"
    app.add_handler(CallbackQueryHandler(user_callback_handler, pattern=user_patterns))


    admin_patterns = r"^(nav_admin_panel|admin_stats|nav_channels|channels_page:|chat_detail:|chat_welcome_menu:|chat_toggle_auto:|chat_toggle_welcome:|chat_preview_welcome:|chat_reset_welcome:|chat_forcesub_menu:|chat_toggle_forcesub:|chat_reset_forcesub:|chat_sendonly_menu:|chat_toggle_sendonly:|chat_set_sendonly_delay:|chat_prompt_pending:|chat_exec_pending:)"
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=admin_patterns))

    # Start polling
    logger.info("Bot is starting polling loop... Ready to accept join requests!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

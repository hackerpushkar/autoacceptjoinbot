import asyncio
import telegram.error
from telegram import Bot
from config import logger, DEFAULT_WELCOME_MESSAGE
from database.db import (
    get_due_delayed_approvals,
    mark_delayed_approval_completed,
    get_chat,
    log_join_request
)
from utils.helpers import parse_buttons_and_clean_text, send_safe_welcome_dm

_worker_task: asyncio.Task = None
_is_running: bool = False


async def process_due_delayed_approvals(bot: Bot):
    """Process all pending delayed approvals that have reached their trigger time."""
    due_items = await get_due_delayed_approvals()
    if not due_items:
        return

    logger.info(f"Processing {len(due_items)} due delayed join approvals...")

    for item in due_items:
        chat_id = item["chat_id"]
        user_id = item["user_id"]

        try:
            # 1. Approve the join request
            await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            await mark_delayed_approval_completed(chat_id=chat_id, user_id=user_id, status="approved_delayed")
            await log_join_request(user_id=user_id, chat_id=chat_id, status="approved")
            logger.info(f"Approved delayed join request for user {user_id} in chat {chat_id}")

            # 2. Optionally deliver Welcome DM if enabled
            chat_data = await get_chat(chat_id)
            if chat_data and chat_data.get("welcome_enabled", 1) == 1:
                chat_title = chat_data.get("title") or "our channel"
                custom_welcome = chat_data.get("custom_welcome_message")
                welcome_template = custom_welcome if custom_welcome else DEFAULT_WELCOME_MESSAGE
                media_file_id = chat_data.get("custom_welcome_media")
                media_type = chat_data.get("custom_welcome_media_type")

                # Mock user object for variable parsing
                class _SimpleUser:
                    def __init__(self, uid):
                        self.id = uid
                        self.first_name = "there"
                        self.last_name = ""
                        self.username = None

                welcome_text, welcome_keyboard = parse_buttons_and_clean_text(
                    raw_text=welcome_template,
                    user=_SimpleUser(user_id),
                    chat_title=chat_title
                )

                await send_safe_welcome_dm(
                    bot=bot,
                    user_id=user_id,
                    text=welcome_text,
                    keyboard=welcome_keyboard,
                    media_file_id=media_file_id,
                    media_type=media_type
                )
        except telegram.error.BadRequest as e:
            # Join request expired or already approved
            logger.debug(f"Delayed approval failed for user {user_id} in {chat_id} (expired/already approved): {e}")
            await mark_delayed_approval_completed(chat_id=chat_id, user_id=user_id, status="expired")
        except telegram.error.Forbidden as e:
            logger.debug(f"Bot lacks permissions to approve join request in chat {chat_id}: {e}")
            await mark_delayed_approval_completed(chat_id=chat_id, user_id=user_id, status="error_forbidden")
        except Exception as e:
            logger.warning(f"Unexpected error in delayed approval for user {user_id} in chat {chat_id}: {e}")
            await mark_delayed_approval_completed(chat_id=chat_id, user_id=user_id, status="error")


async def delayed_approvals_loop(bot: Bot, interval_seconds: int = 30):
    """Continuous background loop checking and executing delayed approvals."""
    global _is_running
    _is_running = True
    logger.info("Delayed approvals background worker started.")

    while _is_running:
        try:
            await process_due_delayed_approvals(bot)
        except Exception as e:
            logger.error(f"Error in delayed approvals worker loop: {e}")
        await asyncio.sleep(interval_seconds)


def start_delayed_approvals_worker(bot: Bot, interval_seconds: int = 30) -> asyncio.Task:
    """Start the background worker task."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(delayed_approvals_loop(bot, interval_seconds))
    return _worker_task


def stop_delayed_approvals_worker():
    """Stop the background worker."""
    global _is_running, _worker_task
    _is_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        _worker_task = None

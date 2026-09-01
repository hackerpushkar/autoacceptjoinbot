import asyncio
from typing import Dict, Any, Optional, Callable
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import (
    GetChatInviteImportersRequest,
    HideChatJoinRequestRequest,
    HideAllChatJoinRequestsRequest
)
from telethon.errors import FloodWaitError
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, SESSION_STRING, logger
from database.db import log_join_request, add_or_update_user, get_chat
from utils.helpers import parse_buttons_and_clean_text

_telethon_client: Optional[TelegramClient] = None


def is_backlog_engine_available() -> bool:
    """Check if MTProto credentials are configured for backlog approvals."""
    return bool(TELEGRAM_API_ID and TELEGRAM_API_HASH and SESSION_STRING)


async def get_mtproto_client() -> Optional[TelegramClient]:
    """Get or initialize the shared Telethon MTProto client."""
    global _telethon_client
    if not is_backlog_engine_available():
        return None

    if _telethon_client is None:
        _telethon_client = TelegramClient(
            StringSession(SESSION_STRING),
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH
        )

    if not _telethon_client.is_connected():
        await _telethon_client.connect()

    return _telethon_client


async def get_pending_requests_count(chat_id: int) -> int:
    """Fetch total count of pending join requests for a given channel."""
    client = await get_mtproto_client()
    if not client:
        return 0

    try:
        peer = await client.get_input_entity(chat_id)
        result = await client(GetChatInviteImportersRequest(
            peer=peer,
            requested=True,
            limit=1,
            offset_date=None,
            offset_user=await client.get_input_entity("me")
        ))
        return getattr(result, "count", len(getattr(result, "importers", [])))
    except Exception as e:
        logger.warning(f"Could not fetch pending requests count for {chat_id}: {e}")
        return 0


async def approve_all_pending_requests(
    chat_id: int,
    bot_context=None,
    progress_callback: Optional[Callable[[int, int], Any]] = None
) -> Dict[str, Any]:
    """
    Approve all existing/backlog join requests in a channel.
    Optionally dispatches Welcome DM if bot_context is provided.
    """
    client = await get_mtproto_client()
    if not client:
        return {"approved": 0, "failed": 0, "total": 0, "error": "MTProto credentials not configured."}

    approved_count = 0
    failed_count = 0
    total_processed = 0

    chat_data = await get_chat(chat_id)
    welcome_enabled = chat_data.get("welcome_enabled", 1) if chat_data else 1
    custom_welcome = chat_data.get("custom_welcome_message") if chat_data else None
    media_file_id = chat_data.get("custom_welcome_media") if chat_data else None
    media_type = chat_data.get("custom_welcome_media_type") if chat_data else None
    chat_title = chat_data.get("title") if chat_data else "Community"

    try:
        peer = await client.get_input_entity(chat_id)

        # 1. Attempt bulk approval via HideAllChatJoinRequestsRequest
        try:
            await client(HideAllChatJoinRequestsRequest(
                peer=peer,
                approved=True
            ))
            logger.info(f"Successfully executed bulk HideAllChatJoinRequests for {chat_id}")
        except Exception as bulk_err:
            logger.debug(f"HideAllChatJoinRequests fallback to individual approvals: {bulk_err}")

        # 2. Iterate to process, log, and send Welcome DMs
        offset_date = None
        offset_user = await client.get_input_entity("me")

        while True:
            try:
                res = await client(GetChatInviteImportersRequest(
                    peer=peer,
                    requested=True,
                    limit=50,
                    offset_date=offset_date,
                    offset_user=offset_user
                ))
            except FloodWaitError as fw:
                logger.warning(f"FloodWait encountered: sleeping {fw.seconds} seconds.")
                await asyncio.sleep(fw.seconds)
                continue
            except Exception as req_err:
                logger.error(f"Error fetching join requests chunk: {req_err}")
                break

            importers = getattr(res, "importers", [])
            if not importers:
                break

            for imp in importers:
                user_id = imp.user_id
                total_processed += 1

                try:
                    await client(HideChatJoinRequestRequest(
                        peer=peer,
                        user_id=user_id,
                        approved=True
                    ))
                    approved_count += 1

                    # Log into SQLite DB
                    await log_join_request(user_id, chat_id, status="approved")
                    await add_or_update_user(user_id, None, None, None)

                    # Send Welcome DM if enabled
                    if welcome_enabled and bot_context:
                        try:
                            from types import SimpleNamespace
                            mock_u = SimpleNamespace(
                                id=user_id,
                                first_name="Member",
                                last_name="",
                                username=""
                            )
                            w_text, w_kb = parse_buttons_and_clean_text(
                                raw_text=custom_welcome or "Welcome to {chat_title}!",
                                user=mock_u,
                                chat_title=chat_title
                            )
                            if media_file_id and media_type == "photo":
                                await bot_context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=media_file_id,
                                    caption=w_text,
                                    parse_mode="HTML",
                                    reply_markup=w_kb
                                )
                            else:
                                await bot_context.bot.send_message(
                                    chat_id=user_id,
                                    text=w_text,
                                    parse_mode="HTML",
                                    reply_markup=w_kb
                                )
                        except Exception:
                            pass

                    if progress_callback:
                        total_expected = getattr(res, "count", total_processed)
                        await progress_callback(approved_count, total_expected)

                    await asyncio.sleep(0.05)

                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Could not approve request for {user_id}: {e}")

            # Pagination
            last_imp = importers[-1]
            offset_date = last_imp.date
            offset_user = await client.get_input_entity(last_imp.user_id)

    except Exception as e:
        logger.error(f"General error in approve_all_pending_requests for {chat_id}: {e}")
        return {"approved": approved_count, "failed": failed_count, "total": total_processed, "error": str(e)}

    return {
        "approved": approved_count,
        "failed": failed_count,
        "total": total_processed
    }

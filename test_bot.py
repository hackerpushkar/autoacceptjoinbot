import asyncio
import os
import unittest
from types import SimpleNamespace

# Set test environment
os.environ["DATABASE_PATH"] = "test_database.sqlite3"
os.environ["BOT_TOKEN"] = "123456789:TEST_MOCK_TOKEN_FOR_TESTING"
os.environ["ADMIN_IDS"] = "999888777"

import config
from database.db import (
    init_db,
    add_or_update_user,
    get_total_users_count,
    get_all_user_ids,
    add_or_update_chat,
    get_chat,
    get_all_chats,
    toggle_chat_auto_accept,
    toggle_chat_welcome,
    set_chat_custom_welcome,
    log_join_request,
    get_analytics
)
from utils.helpers import (
    format_welcome_message,
    parse_buttons_and_clean_text,
    get_add_to_channel_url,
    get_add_to_group_url
)
from keyboards.inline import (
    get_start_keyboard,
    get_channels_keyboard,
    get_chat_settings_keyboard,
    get_chat_welcome_menu_keyboard,
    get_approve_pending_confirm_keyboard,
    get_force_sub_keyboard
)
from services.backlog_cleaner import is_backlog_engine_available
from utils.force_sub import (
    parse_channel_target,
    get_force_sub_message,
    check_channel_membership,
    get_unsubscribed_channels
)
from telegram.constants import ChatMemberStatus


class TestBotComponents(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()

    async def asyncTearDown(self):
        if os.path.exists("test_database.sqlite3"):
            try:
                os.remove("test_database.sqlite3")
            except Exception:
                pass

    async def test_database_user_operations(self):
        await add_or_update_user(1001, "johndoe", "John", "Doe")
        count = await get_total_users_count()
        self.assertEqual(count, 1)

        user_ids = await get_all_user_ids()
        self.assertIn(1001, user_ids)

    async def test_database_chat_operations(self):
        await add_or_update_chat(-100123456789, "My Crypto Channel", "channel")
        chat = await get_chat(-100123456789)
        self.assertIsNotNone(chat)
        self.assertEqual(chat["title"], "My Crypto Channel")
        self.assertEqual(chat["auto_accept"], 1)

        # Toggle auto accept
        new_state = await toggle_chat_auto_accept(-100123456789)
        self.assertFalse(new_state)

        # Toggle welcome
        new_welcome_state = await toggle_chat_welcome(-100123456789)
        self.assertFalse(new_welcome_state)

        # Custom welcome message with media
        await set_chat_custom_welcome(-100123456789, "Welcome to VIP {name}!", media_file_id="AgACAgIAAxkBAAI...", media_type="photo")
        updated_chat = await get_chat(-100123456789)
        self.assertEqual(updated_chat["custom_welcome_message"], "Welcome to VIP {name}!")
        self.assertEqual(updated_chat["custom_welcome_media"], "AgACAgIAAxkBAAI...")
        self.assertEqual(updated_chat["custom_welcome_media_type"], "photo")

    async def test_analytics_and_join_logging(self):
        await log_join_request(1001, -100123456789, "approved")
        stats = await get_analytics()
        self.assertGreaterEqual(stats["total_approved"], 1)

    def test_helpers_formatting(self):
        mock_user = SimpleNamespace(
            id=12345,
            first_name="Alice",
            last_name="Smith",
            username="alice_tg"
        )
        template = "Hello {name}, welcome to {chat_title}! Your username is {username}."
        formatted = format_welcome_message(template, mock_user, "Premium Signals")
        self.assertIn("Alice Smith", formatted)
        self.assertIn("Premium Signals", formatted)
        self.assertIn("@alice_tg", formatted)

    def test_button_parsing(self):
        mock_user = SimpleNamespace(
            id=12345,
            first_name="Alice",
            last_name="Smith",
            username="alice_tg"
        )
        raw_text = (
            "Welcome {name} to {chat_title}!\n\n"
            "[👉 Join VIP Channel - https://t.me/vipchannel]\n"
            "[🌐 Website - https://example.com | 💬 Support - https://t.me/support]"
        )
        clean_text, kb = parse_buttons_and_clean_text(raw_text, mock_user, "Alpha Traders")
        
        self.assertEqual(clean_text, "Welcome Alice Smith to Alpha Traders!")
        self.assertIsNotNone(kb)
        self.assertEqual(len(kb.inline_keyboard), 2)
        # First row: 1 button
        self.assertEqual(len(kb.inline_keyboard[0]), 1)
        self.assertEqual(kb.inline_keyboard[0][0].text, "👉 Join VIP Channel")
        self.assertEqual(kb.inline_keyboard[0][0].url, "https://t.me/vipchannel")
        # Second row: 2 buttons
        self.assertEqual(len(kb.inline_keyboard[1]), 2)
        self.assertEqual(kb.inline_keyboard[1][0].text, "🌐 Website")
        self.assertEqual(kb.inline_keyboard[1][1].text, "💬 Support")

    def test_url_helpers(self):
        ch_url = get_add_to_channel_url("TestAcceptBot")
        gp_url = get_add_to_group_url("TestAcceptBot")
        self.assertIn("startchannel=true", ch_url)
        self.assertIn("startgroup=true", gp_url)

    def test_keyboards_builder(self):
        start_kb = get_start_keyboard("TestAcceptBot", is_user_admin=True)
        self.assertIsNotNone(start_kb)

        channels_kb = get_channels_keyboard([{"chat_id": 1, "title": "Test Ch", "auto_accept": 1}])
        self.assertIsNotNone(channels_kb)

        settings_kb = get_chat_settings_keyboard(123, True)
        self.assertIsNotNone(settings_kb)

        welcome_menu_kb = get_chat_welcome_menu_keyboard(123, True)
        self.assertIsNotNone(welcome_menu_kb)

        pending_confirm_kb = get_approve_pending_confirm_keyboard(123)
        self.assertIsNotNone(pending_confirm_kb)

        # Force sub keyboard test
        channels = [
            {"title": "Channel 1", "url": "https://t.me/ch1"},
            {"title": "Channel 2", "url": "https://t.me/ch2"}
        ]
        fs_kb = get_force_sub_keyboard(channels)
        self.assertIsNotNone(fs_kb)
        self.assertEqual(len(fs_kb.inline_keyboard), 3)
        self.assertEqual(fs_kb.inline_keyboard[0][0].text, "📢 Join Channel 1")
        self.assertEqual(fs_kb.inline_keyboard[1][0].text, "📢 Join Channel 2")
        self.assertEqual(fs_kb.inline_keyboard[2][0].callback_data, "verify_force_sub")

    def test_force_sub_helpers(self):
        self.assertEqual(parse_channel_target("-100123456789"), -100123456789)
        self.assertEqual(parse_channel_target("@mychannel"), "@mychannel")
        self.assertEqual(parse_channel_target("mychannel"), "@mychannel")
        self.assertEqual(parse_channel_target("https://t.me/mychannel"), "@mychannel")

        msg = get_force_sub_message("Alice", [{"title": "My Channel", "url": "https://t.me/mychannel"}])
        self.assertIn("Alice", msg)
        self.assertIn("Subscription Required", msg)
        self.assertIn("My Channel", msg)
        self.assertIn("Verify / I Joined", msg)

    def test_backlog_engine_status(self):
        # Should return boolean without crashing
        status = is_backlog_engine_available()
        self.assertIsInstance(status, bool)

    async def test_force_sub_membership_mock(self):
        from unittest.mock import AsyncMock, MagicMock
        
        # Test bot mock where user is not joined
        mock_bot = MagicMock()
        mock_chat = SimpleNamespace(id=-100111, title="Official Updates", username="official_updates", invite_link=None)
        mock_bot.get_chat = AsyncMock(return_value=mock_chat)
        mock_bot.get_chat_member = AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.LEFT))
        
        is_member, title, link = await check_channel_membership(mock_bot, 12345, "@official_updates")
        self.assertFalse(is_member)
        self.assertEqual(title, "Official Updates")
        self.assertEqual(link, "https://t.me/official_updates")

        # Test bot mock where user is joined
        mock_bot.get_chat_member = AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER))
        is_member_joined, _, _ = await check_channel_membership(mock_bot, 12345, "@official_updates")
        self.assertTrue(is_member_joined)



if __name__ == "__main__":
    unittest.main()


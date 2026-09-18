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
    toggle_chat_force_sub,
    set_chat_force_sub_channels,
    toggle_chat_send_only,
    set_chat_send_only_delay,
    add_delayed_approval,
    get_due_delayed_approvals,
    mark_delayed_approval_completed,
    log_join_request,
    get_analytics,
    get_chats_by_owner,
    set_chat_owner,
    delete_chat
)
from utils.helpers import (
    format_welcome_message,
    parse_buttons_and_clean_text,
    get_add_to_channel_url,
    get_add_to_group_url,
    send_safe_welcome_dm,
    can_user_manage_chat,
    get_user_manageable_chats
)
from handlers.user import start_command, send_channel_welcome_for_user
from handlers.admin import admin_callback_handler
from keyboards.inline import (
    get_start_keyboard,
    get_channels_keyboard,
    get_chat_settings_keyboard,
    get_chat_welcome_menu_keyboard,
    get_chat_forcesub_menu_keyboard,
    get_chat_sendonly_menu_keyboard,
    format_delay_time,
    get_channel_force_join_request_keyboard,
    get_approve_pending_confirm_keyboard,
    get_about_keyboard,
    get_more_info_keyboard,
    get_developer_info_keyboard,
    get_gift_keyboard,
    get_info_subpage_keyboard,
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

        # Per-chat force sub operations
        await set_chat_force_sub_channels(-100123456789, "@channel1, @channel2")
        fs_chat = await get_chat(-100123456789)
        self.assertEqual(fs_chat["force_sub_channels"], "@channel1, @channel2")
        self.assertEqual(fs_chat["force_sub_enabled"], 1)

        toggled_fs = await toggle_chat_force_sub(-100123456789)
        self.assertFalse(toggled_fs)

    async def test_analytics_and_join_logging(self):
        await log_join_request(1001, -100123456789, "approved")
        stats = await get_analytics()
        self.assertGreaterEqual(stats["total_approved"], 1)

    async def test_send_safe_welcome_dm(self):
        # Create mock bot
        class MockBot:
            def __init__(self):
                self.sent_messages = []
                self.sent_photos = []

            async def send_message(self, **kwargs):
                self.sent_messages.append(kwargs)
                return True

            async def send_photo(self, **kwargs):
                self.sent_photos.append(kwargs)
                return True

        bot = MockBot()
        # 1. Send text DM
        res = await send_safe_welcome_dm(bot, 12345, "Hello Welcome!")
        self.assertTrue(res)
        self.assertEqual(len(bot.sent_messages), 1)

        # 2. Send photo DM
        res_photo = await send_safe_welcome_dm(bot, 12345, "Photo Welcome!", media_file_id="photo_123", media_type="photo")
        self.assertTrue(res_photo)
        self.assertEqual(len(bot.sent_photos), 1)

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

        # Test [Button Name] - {link/text} syntax
        raw_text_2 = "Hii buddy\n\n[Join Our Community] - {aierhg9p454gerh}"
        clean_text_2, kb_2 = parse_buttons_and_clean_text(raw_text_2, mock_user, "Alpha Traders")
        self.assertEqual(clean_text_2, "Hii buddy")
        self.assertIsNotNone(kb_2)
        self.assertEqual(kb_2.inline_keyboard[0][0].text, "Join Our Community")
        self.assertEqual(kb_2.inline_keyboard[0][0].url, "https://t.me/aierhg9p454gerh")

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

        chat_forcesub_kb = get_chat_forcesub_menu_keyboard(123, True, True)
        self.assertIsNotNone(chat_forcesub_kb)
        self.assertEqual(chat_forcesub_kb.inline_keyboard[0][0].callback_data, "chat_toggle_forcesub:123")

        chan_fs_request_kb = get_channel_force_join_request_keyboard(123, [{"title": "Ch 1", "url": "https://t.me/ch1"}])
        self.assertIsNotNone(chan_fs_request_kb)
        self.assertEqual(chan_fs_request_kb.inline_keyboard[1][0].callback_data, "verify_chat_join:123")

        pending_confirm_kb = get_approve_pending_confirm_keyboard(123)
        self.assertIsNotNone(pending_confirm_kb)

        # About & More Info keyboards test
        about_kb = get_about_keyboard("TestBot")
        self.assertIsNotNone(about_kb)
        self.assertEqual(about_kb.inline_keyboard[1][0].text, "ℹ️ More Info")
        self.assertEqual(about_kb.inline_keyboard[1][0].callback_data, "about_more_info")

        more_info_kb = get_more_info_keyboard("TestBot")
        self.assertIsNotNone(more_info_kb)
        self.assertEqual(more_info_kb.inline_keyboard[0][0].text, "👨‍💻 Developer Info")
        self.assertEqual(more_info_kb.inline_keyboard[0][1].text, "👑 Admin Info")
        self.assertEqual(more_info_kb.inline_keyboard[1][0].text, "↗️ Share Bot")
        self.assertEqual(more_info_kb.inline_keyboard[2][0].text, "🔙 Go Back")
        self.assertEqual(more_info_kb.inline_keyboard[2][1].text, "🏠 Back to Main Menu")

        dev_kb = get_developer_info_keyboard()
        self.assertIsNotNone(dev_kb)
        self.assertEqual(dev_kb.inline_keyboard[0][0].text, "🎁 Gift for You Guys")
        self.assertEqual(dev_kb.inline_keyboard[0][0].callback_data, "info_gift")
        self.assertEqual(dev_kb.inline_keyboard[1][0].text, "🔙 Go Back")
        self.assertEqual(dev_kb.inline_keyboard[1][0].callback_data, "about_more_info")

        gift_kb = get_gift_keyboard()
        self.assertIsNotNone(gift_kb)
        self.assertEqual(gift_kb.inline_keyboard[0][0].text, "✅ Yes")
        self.assertIn("qufork.com", gift_kb.inline_keyboard[0][0].url)
        self.assertEqual(gift_kb.inline_keyboard[0][1].text, "❌ No")
        self.assertEqual(gift_kb.inline_keyboard[0][1].callback_data, "info_developer")
        self.assertEqual(gift_kb.inline_keyboard[1][0].text, "🏠 Back to Main Menu")

        subpage_kb = get_info_subpage_keyboard()
        self.assertIsNotNone(subpage_kb)
        self.assertEqual(subpage_kb.inline_keyboard[0][0].text, "🔙 Go Back")
        self.assertEqual(subpage_kb.inline_keyboard[0][0].callback_data, "about_more_info")

        # Force sub keyboard test
        channels = [
            {"title": "Hacker Pushkar", "url": "https://t.me/hackerpushkar"},
            {"title": "Channel 2", "url": "https://t.me/ch2"}
        ]
        fs_kb = get_force_sub_keyboard(channels)
        self.assertIsNotNone(fs_kb)
        self.assertEqual(len(fs_kb.inline_keyboard), 3)
        self.assertEqual(fs_kb.inline_keyboard[0][0].text, "Join Hacker Pushkar")
        self.assertEqual(fs_kb.inline_keyboard[1][0].text, "Join Channel 2")
        self.assertEqual(fs_kb.inline_keyboard[2][0].text, "🔄 I Have Joined (Verify)")
        self.assertEqual(fs_kb.inline_keyboard[2][0].callback_data, "verify_force_sub")

    def test_force_sub_helpers(self):
        self.assertEqual(parse_channel_target("-100123456789"), -100123456789)
        self.assertEqual(parse_channel_target("@mychannel"), "@mychannel")
        self.assertEqual(parse_channel_target("mychannel"), "@mychannel")
        self.assertEqual(parse_channel_target("https://t.me/mychannel"), "@mychannel")

        msg = get_force_sub_message("Alice", [{"title": "Hacker Pushkar", "url": "https://t.me/hackerpushkar"}])
        self.assertIn("Welcome!", msg)
        self.assertIn("To use this bot, you must join our official channel(s) first.", msg)
        self.assertIn("I Have Joined (Verify)", msg)

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

    def test_database_mode_detection(self):
        from database.db import is_mongodb_enabled
        # When MONGO_URI is empty/unset
        self.assertFalse(is_mongodb_enabled())

        # When MONGO_URI is set
        original_uri = config.MONGO_URI
        try:
            config.MONGO_URI = "mongodb://localhost:27017"
            self.assertTrue(is_mongodb_enabled())
        finally:
            config.MONGO_URI = original_uri

    async def test_mongo_operations_mock(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        import database.db as db_mod

        original_uri = config.MONGO_URI
        try:
            config.MONGO_URI = "mongodb://mock_uri:27017"
            mock_mongo_db = MagicMock()
            
            # Users mock
            mock_mongo_db.users.update_one = AsyncMock(return_value=None)
            mock_mongo_db.users.count_documents = AsyncMock(return_value=42)
            
            async def mock_user_cursor():
                yield {"_id": 100, "user_id": 100}
                yield {"_id": 200, "user_id": 200}
            mock_mongo_db.users.find.return_value = mock_user_cursor()

            # Chats mock
            mock_mongo_db.chats.update_one = AsyncMock(return_value=None)
            mock_mongo_db.chats.find_one = AsyncMock(return_value={
                "_id": -100123,
                "chat_id": -100123,
                "title": "VIP Club",
                "chat_type": "channel",
                "auto_accept": 1,
                "welcome_enabled": 1,
                "custom_welcome_message": "Hello!",
                "custom_welcome_media": None,
                "custom_welcome_media_type": None,
                "added_at": "2026-09-01 00:00:00"
            })
            
            async def mock_chats_cursor():
                yield {
                    "_id": -100123,
                    "chat_id": -100123,
                    "title": "VIP Club",
                    "chat_type": "channel",
                    "auto_accept": 1,
                    "welcome_enabled": 1,
                    "custom_welcome_message": None,
                    "custom_welcome_media": None,
                    "custom_welcome_media_type": None,
                    "added_at": "2026-09-01 00:00:00"
                }
            sort_mock = MagicMock(return_value=mock_chats_cursor())
            mock_mongo_db.chats.find.return_value.sort = sort_mock
            mock_mongo_db.chats.count_documents = AsyncMock(return_value=5)

            # Join requests mock
            mock_mongo_db.join_requests.insert_one = AsyncMock(return_value=None)
            mock_mongo_db.join_requests.count_documents = AsyncMock(return_value=128)

            with patch("database.db.get_mongo_db", return_value=mock_mongo_db):
                # 1. User operations
                await db_mod.add_or_update_user(100, "alice", "Alice", "Smith")
                self.assertEqual(await db_mod.get_total_users_count(), 42)
                user_ids = await db_mod.get_all_user_ids()
                self.assertEqual(user_ids, [100, 200])

                # 2. Chat operations
                await db_mod.add_or_update_chat(-100123, "VIP Club", "channel")
                chat = await db_mod.get_chat(-100123)
                self.assertIsNotNone(chat)
                self.assertEqual(chat["title"], "VIP Club")

                # Toggle settings
                new_auto = await db_mod.toggle_chat_auto_accept(-100123)
                self.assertFalse(new_auto)
                new_welc = await db_mod.toggle_chat_welcome(-100123)
                self.assertFalse(new_welc)

                # Set custom welcome
                await db_mod.set_chat_custom_welcome(-100123, "Welcome!", "file_123", "photo")

                # 3. Join request & analytics
                await db_mod.log_join_request(100, -100123, "approved")
                stats = await db_mod.get_analytics()
                self.assertEqual(stats["total_approved"], 128)
                self.assertEqual(stats["total_chats"], 5)
                self.assertEqual(stats["total_users"], 42)
        finally:
            config.MONGO_URI = original_uri

    def test_send_only_workflow(self):
        asyncio.run(self._async_test_send_only_workflow())

    async def _async_test_send_only_workflow(self):
        await init_db()
        chat_id = -100999888
        await add_or_update_chat(chat_id, "Send Only Testing", "channel")

        # 1. Test Send Only toggle
        state1 = await toggle_chat_send_only(chat_id)
        self.assertTrue(state1)
        chat = await get_chat(chat_id)
        self.assertEqual(chat["send_only_enabled"], 1)

        # 2. Test Set Delay
        await set_chat_send_only_delay(chat_id, 172800)  # 2 days
        chat = await get_chat(chat_id)
        self.assertEqual(chat["send_only_delay"], 172800)

        # 3. Test format_delay_time helper
        self.assertEqual(format_delay_time(3600), "1 Hour")
        self.assertEqual(format_delay_time(21600), "6 Hours")
        self.assertEqual(format_delay_time(86400), "1 Day")
        self.assertEqual(format_delay_time(172800), "2 Days")

        # 4. Test Keyboards
        fs_kb = get_chat_forcesub_menu_keyboard(chat_id, force_sub_enabled=True, has_channels=True, send_only_enabled=True, send_only_delay=172800)
        self.assertIsNotNone(fs_kb)
        so_kb = get_chat_sendonly_menu_keyboard(chat_id, send_only_enabled=True, current_delay=172800)
        self.assertIsNotNone(so_kb)

        # 5. Test Delayed Approvals Scheduling & Processing
        user_id = 777111
        # Schedule with 0 delay (immediately due)
        await add_delayed_approval(chat_id, user_id, delay_seconds=-10)
        due = await get_due_delayed_approvals()
        self.assertTrue(any(d["chat_id"] == chat_id and d["user_id"] == user_id for d in due))

        # Mark completed
        await mark_delayed_approval_completed(chat_id, user_id, status="approved_manual")
        due_after = await get_due_delayed_approvals()
        self.assertFalse(any(d["chat_id"] == chat_id and d["user_id"] == user_id for d in due_after))

    async def test_callback_auto_start_and_verification(self):
        # 1. Test user is added to DB on callback query simulation
        test_uid = 555666
        await add_or_update_user(test_uid, "callback_user", "Callback", "Tester")
        user_ids = await get_all_user_ids()
        self.assertIn(test_uid, user_ids)

        # 2. Test chat setup with force sub & verify keyboard generation
        chat_id = -100444555
        await add_or_update_chat(chat_id, "Test Channel", "channel")
        await set_chat_force_sub_channels(chat_id, "@partner1, @partner2")

        unsubscribed_mock = [
            {"channel": "@partner1", "title": "Partner 1", "url": "https://t.me/partner1"},
            {"channel": "@partner2", "title": "Partner 2", "url": "https://t.me/partner2"}
        ]
        # Verify keyboard contains callback button verify_chat_join
        kb = get_channel_force_join_request_keyboard(chat_id, unsubscribed_mock, bot_username="MyTestBot")
        button_callbacks = [
            button.callback_data
            for row in kb.inline_keyboard
            for button in row
            if button.callback_data
        ]
        self.assertIn(f"verify_chat_join:{chat_id}", button_callbacks)

    async def test_start_command_channel_deep_link(self):
        target_chat_id = -100888999
        await add_or_update_chat(target_chat_id, "VIP Alpha Channel", "channel")
        await set_chat_custom_welcome(
            target_chat_id,
            "🔥 Welcome {name} to {chat_title}! Enjoy premium signals.\n[Join VIP Hub] - {https://t.me/viphub}"
        )

        sent_messages = []

        class MockBot:
            username = "MyTestBot"
            async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None, **kwargs):
                sent_messages.append({
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": reply_markup,
                    "parse_mode": parse_mode
                })
                return SimpleNamespace(message_id=123)

        mock_user = SimpleNamespace(
            id=777888,
            username="deeplink_user",
            first_name="DeepLink",
            last_name="Tester"
        )
        mock_update = SimpleNamespace(
            effective_user=mock_user,
            message=SimpleNamespace(reply_text=None),
            callback_query=None
        )
        mock_context = SimpleNamespace(
            bot=MockBot(),
            args=[f"welcome_{target_chat_id}"]
        )

        await start_command(mock_update, mock_context)

        # 1. Verify user was stored in database for future broadcasts
        all_users = await get_all_user_ids()
        self.assertIn(777888, all_users)

        # 2. Verify channel welcome message was sent
        self.assertEqual(len(sent_messages), 1)
        sent = sent_messages[0]
        self.assertEqual(sent["chat_id"], 777888)
        self.assertIn("Welcome DeepLink Tester to VIP Alpha Channel!", sent["text"])
        self.assertIsNotNone(sent["reply_markup"])

    async def test_multi_user_chat_isolation(self):
        user_a = 111222
        user_b = 333444
        chat_a = -1001111111
        chat_b = -1002222222

        # 1. Register chats with different owners
        await add_or_update_chat(chat_a, "User A Channel", "channel", owner_id=user_a)
        await add_or_update_chat(chat_b, "User B Channel", "channel", owner_id=user_b)

        # 2. Verify User A only sees chat_a
        chats_a = await get_chats_by_owner(user_a)
        chat_ids_a = [c["chat_id"] for c in chats_a]
        self.assertIn(chat_a, chat_ids_a)
        self.assertNotIn(chat_b, chat_ids_a)

        # 3. Verify User B only sees chat_b
        chats_b = await get_chats_by_owner(user_b)
        chat_ids_b = [c["chat_id"] for c in chats_b]
        self.assertIn(chat_b, chat_ids_b)
        self.assertNotIn(chat_a, chat_ids_b)

        # 4. Verify User C (no chats) gets empty list
        chats_c = await get_chats_by_owner(999999)
        self.assertEqual(len(chats_c), 0)

    async def test_can_user_manage_chat(self):
        owner_id = 555666
        other_user_id = 777888
        superadmin_id = 999888777  # configured in os.environ["ADMIN_IDS"]
        chat_id = -100999111

        await add_or_update_chat(chat_id, "Permission Test Chat", "channel", owner_id=owner_id)

        class MockBot:
            async def get_chat_member(self, chat_id, user_id):
                return SimpleNamespace(status="member")

        bot = MockBot()

        # Owner has permission
        self.assertTrue(await can_user_manage_chat(bot, chat_id, owner_id))
        # Non-owner regular user is denied
        self.assertFalse(await can_user_manage_chat(bot, chat_id, other_user_id))
        # Superadmin is always allowed
        self.assertTrue(await can_user_manage_chat(bot, chat_id, superadmin_id))

    async def test_delete_chat(self):
        chat_id = -100777333
        await add_or_update_chat(chat_id, "Temporary Chat", "channel", owner_id=123)
        self.assertIsNotNone(await get_chat(chat_id))

        await delete_chat(chat_id)
        self.assertIsNone(await get_chat(chat_id))

    async def test_chat_detail_callback_response(self):
        chat_id = -100888111
        user_id = 999111
        await add_or_update_chat(chat_id, "Demo Channel", "channel", owner_id=user_id)

        answered = []
        edited_messages = []

        class MockQuery:
            data = f"chat_detail:{chat_id}"
            from_user = SimpleNamespace(id=user_id, username="demo_owner")

            async def answer(self, text=None, show_alert=False):
                answered.append({"text": text, "show_alert": show_alert})

            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                edited_messages.append({"text": text, "reply_markup": reply_markup})

        class MockBot:
            async def get_chat_member(self, cid, uid):
                return SimpleNamespace(status="creator")

        update = SimpleNamespace(callback_query=MockQuery(), effective_user=MockQuery.from_user)
        context = SimpleNamespace(bot=MockBot())

        await admin_callback_handler(update, context)

        # Verify the query was answered and the message was edited with Settings for Demo Channel
        self.assertTrue(len(answered) > 0)
        self.assertEqual(len(edited_messages), 1)
        self.assertIn("Settings for:</b> Demo Channel", edited_messages[0]["text"])


if __name__ == "__main__":
    unittest.main()




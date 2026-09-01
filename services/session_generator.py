import asyncio
from typing import Any, cast
from telethon import TelegramClient
from telethon.sessions import StringSession


async def generate_session():
    print("=" * 60)
    print("🔑 TELEGRAM STRING SESSION GENERATOR")
    print("=" * 60)
    print("Get your API_ID and API_HASH for free at: https://my.telegram.org\n")

    api_id_input = input("Enter your API ID: ").strip()
    if not api_id_input.isdigit():
        print("❌ Invalid API ID. Must be an integer.")
        return
    api_id = int(api_id_input)
    api_hash = input("Enter your API HASH: ").strip()

    if not api_hash:
        print("❌ API HASH cannot be empty.")
        return

    print("\nConnecting to Telegram...")
    client = TelegramClient(StringSession(), api_id, api_hash)
    await cast(Any, client.start())

    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("🎉 YOUR SESSION STRING (Copy and paste into your .env):")
    print("=" * 60)
    print(f"\nSESSION_STRING={session_string}\n")
    print("=" * 60)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(generate_session())

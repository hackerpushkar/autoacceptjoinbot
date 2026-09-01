import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Logger configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger("AutoAcceptBot")

# Bot credentials
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Optional MTProto credentials (for Batch / Backlog Join Requests approval)
raw_api_id = os.getenv("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_ID: Optional[int] = int(raw_api_id) if raw_api_id.isdigit() else None
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "").strip()
SESSION_STRING: str = os.getenv("SESSION_STRING", "").strip()
PHONE_NUMBER: str = os.getenv("PHONE_NUMBER", "").strip()

# Admin IDs
raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = []
if raw_admins:
    for item in raw_admins.split(","):
        clean_item = item.strip()
        if clean_item.isdigit() or (clean_item.startswith("-") and clean_item[1:].isdigit()):
            ADMIN_IDS.append(int(clean_item))

# Database configuration (MongoDB with automatic SQLite fallback)
MONGO_URI: str = (
    os.getenv("MONGO_URI", "")
    or os.getenv("MONGODB_URI", "")
    or os.getenv("MONGO_URL", "")
).strip()
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "telegram_auto_accept_bot").strip()
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.sqlite3").strip()
IS_MONGO: bool = bool(MONGO_URI)

# Force Subscribe Channels
# Comma-separated list of channel usernames or chat IDs (e.g. "@mychannel, -100123456789")
raw_force_sub = os.getenv("FORCE_SUB_CHANNELS") or os.getenv("FORCE_SUB_CHANNEL") or os.getenv("force_sub_channel", "")
FORCE_SUB_CHANNELS: List[str] = []
if raw_force_sub:
    for item in raw_force_sub.split(","):
        clean_item = item.strip()
        if clean_item:
            FORCE_SUB_CHANNELS.append(clean_item)

# Default Welcome message
DEFAULT_WELCOME_MESSAGE: str = os.getenv(
    "DEFAULT_WELCOME_MESSAGE",
    "👋 Hello {name}!\n\n🎉 Your request to join <b>{chat_title}</b> has been <b>approved</b>.\n\nWelcome aboard! Enjoy your stay. ✨"
).replace("\\n", "\n")


def is_admin(user_id: int) -> bool:
    """Check if a given user ID is configured as an administrator."""
    if not ADMIN_IDS:
        return True  # If no admin configured, allow first user or warn
    return user_id in ADMIN_IDS


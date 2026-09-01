import aiosqlite
import datetime
from typing import Dict, Any, List, Optional
from config import DATABASE_PATH, logger


async def init_db():
    """Initialize database tables if they do not exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                chat_type TEXT,
                auto_accept INTEGER DEFAULT 1,
                welcome_enabled INTEGER DEFAULT 1,
                custom_welcome_message TEXT,
                custom_welcome_media TEXT,
                custom_welcome_media_type TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Perform seamless column migrations for existing databases
        try:
            await db.execute("ALTER TABLE chats ADD COLUMN custom_welcome_media TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE chats ADD COLUMN custom_welcome_media_type TEXT")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                status TEXT DEFAULT 'approved',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.commit()
        logger.info("Database initialized successfully.")


# ==========================================
# USER OPERATIONS
# ==========================================

async def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]):
    """Insert or update user record upon interaction."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_seen = CURRENT_TIMESTAMP
        """, (user_id, username, first_name, last_name))
        await db.commit()


async def get_all_user_ids() -> List[int]:
    """Retrieve all user IDs for broadcasting."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_total_users_count() -> int:
    """Return count of registered bot users."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ==========================================
# CHAT / CHANNEL OPERATIONS
# ==========================================

async def add_or_update_chat(chat_id: int, title: str, chat_type: str):
    """Register or update channel/group details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO chats (chat_id, title, chat_type)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                chat_type = excluded.chat_type
        """, (chat_id, title, chat_type))
        await db.commit()


async def get_chat(chat_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve details and settings for a specific chat."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_all_chats() -> List[Dict[str, Any]]:
    """Retrieve all registered chats."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chats ORDER BY added_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def toggle_chat_auto_accept(chat_id: int) -> bool:
    """Toggle auto accept flag for a chat and return new boolean state."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT auto_accept FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            current_state = row[0] if row else 1
            new_state = 0 if current_state == 1 else 1

        await db.execute("UPDATE chats SET auto_accept = ? WHERE chat_id = ?", (new_state, chat_id))
        await db.commit()
        return new_state == 1


async def toggle_chat_welcome(chat_id: int) -> bool:
    """Toggle welcome message flag for a chat and return new boolean state."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT welcome_enabled FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            current_state = row[0] if row else 1
            new_state = 0 if current_state == 1 else 1

        await db.execute("UPDATE chats SET welcome_enabled = ? WHERE chat_id = ?", (new_state, chat_id))
        await db.commit()
        return new_state == 1


async def set_chat_custom_welcome(chat_id: int, message: Optional[str], media_file_id: Optional[str] = None, media_type: Optional[str] = None):
    """Set or clear custom welcome message and media for a chat."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE chats 
               SET custom_welcome_message = ?, 
                   custom_welcome_media = ?, 
                   custom_welcome_media_type = ? 
               WHERE chat_id = ?""",
            (message, media_file_id, media_type, chat_id)
        )
        await db.commit()


# ==========================================
# JOIN REQUEST LOGGING & STATS
# ==========================================

async def log_join_request(user_id: int, chat_id: int, status: str = "approved"):
    """Log an approved join request."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO join_requests (user_id, chat_id, status)
            VALUES (?, ?, ?)
        """, (user_id, chat_id, status))
        await db.commit()


async def get_analytics() -> Dict[str, Any]:
    """Calculate overall statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Total join requests approved
        async with db.execute("SELECT COUNT(*) FROM join_requests WHERE status = 'approved'") as cur:
            row = await cur.fetchone()
            total_requests = row[0] if row else 0

        # Total channels / groups
        async with db.execute("SELECT COUNT(*) FROM chats") as cur:
            row = await cur.fetchone()
            total_chats = row[0] if row else 0

        # Total users
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            total_users = row[0] if row else 0

        # Today's approvals
        today_start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d 00:00:00")
        async with db.execute("SELECT COUNT(*) FROM join_requests WHERE created_at >= ?", (today_start,)) as cur:
            row = await cur.fetchone()
            today_requests = row[0] if row else 0

        return {
            "total_approved": total_requests,
            "total_chats": total_chats,
            "total_users": total_users,
            "today_approved": today_requests
        }

import datetime
from typing import Dict, Any, List, Optional
import aiosqlite
import config
from config import DATABASE_PATH, logger

# Global MongoDB client references
_mongo_client = None
_mongo_db = None


def is_mongodb_enabled() -> bool:
    """Check if MongoDB connection URI is configured."""
    return bool(config.MONGO_URI)


def get_mongo_db():
    """Lazily initialize and return the async MongoDB database instance."""
    global _mongo_client, _mongo_db
    if _mongo_db is None and config.MONGO_URI:
        from motor.motor_asyncio import AsyncIOMotorClient
        _mongo_client = AsyncIOMotorClient(config.MONGO_URI)
        _mongo_db = _mongo_client[config.DATABASE_NAME]
    return _mongo_db


async def init_db():
    """Initialize database tables or collections/indexes."""
    if is_mongodb_enabled():
        try:
            db = get_mongo_db()
            # Create indexes for optimal lookup performance
            await db.users.create_index("user_id", unique=True)
            await db.chats.create_index("chat_id", unique=True)
            await db.join_requests.create_index([("status", 1), ("created_at", -1)])
            logger.info(f"Database initialized successfully (MongoDB: {config.DATABASE_NAME}).")
            return
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB ({e}). Falling back to SQLite.")

    # SQLite Database Initialization
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

        try:
            await db.execute("ALTER TABLE chats ADD COLUMN force_sub_enabled INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE chats ADD COLUMN force_sub_channels TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE chats ADD COLUMN send_only_enabled INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE chats ADD COLUMN send_only_delay INTEGER DEFAULT 86400")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS delayed_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approve_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

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
        logger.info(f"Database initialized successfully (SQLite: {DATABASE_PATH}).")


# ==========================================
# USER OPERATIONS
# ==========================================

async def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]):
    """Insert or update user record upon interaction."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        now = datetime.datetime.now(datetime.timezone.utc)
        await db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "last_seen": now
                },
                "$setOnInsert": {
                    "first_seen": now
                }
            },
            upsert=True
        )
        return

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
    if is_mongodb_enabled():
        db = get_mongo_db()
        cursor = db.users.find({}, {"_id": 1, "user_id": 1})
        user_ids = []
        async for doc in cursor:
            user_ids.append(int(doc.get("user_id") or doc["_id"]))
        return user_ids

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_total_users_count() -> int:
    """Return count of registered bot users."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        return await db.users.count_documents({})

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ==========================================
# CHAT / CHANNEL OPERATIONS
# ==========================================

def _format_mongo_chat(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format MongoDB chat document into dictionary matching SQLite schema."""
    if not doc:
        return None
    return {
        "chat_id": doc.get("chat_id", doc.get("_id")),
        "title": doc.get("title", ""),
        "chat_type": doc.get("chat_type", "channel"),
        "auto_accept": doc.get("auto_accept", 1),
        "welcome_enabled": doc.get("welcome_enabled", 1),
        "custom_welcome_message": doc.get("custom_welcome_message"),
        "custom_welcome_media": doc.get("custom_welcome_media"),
        "custom_welcome_media_type": doc.get("custom_welcome_media_type"),
        "force_sub_enabled": doc.get("force_sub_enabled", 0),
        "force_sub_channels": doc.get("force_sub_channels"),
        "send_only_enabled": doc.get("send_only_enabled", 0),
        "send_only_delay": doc.get("send_only_delay", 86400),
        "added_at": str(doc.get("added_at", ""))
    }


async def add_or_update_chat(chat_id: int, title: str, chat_type: str):
    """Register or update channel/group details."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        now = datetime.datetime.now(datetime.timezone.utc)
        await db.chats.update_one(
            {"_id": chat_id},
            {
                "$set": {
                    "chat_id": chat_id,
                    "title": title,
                    "chat_type": chat_type
                },
                "$setOnInsert": {
                    "auto_accept": 1,
                    "welcome_enabled": 1,
                    "custom_welcome_message": None,
                    "custom_welcome_media": None,
                    "custom_welcome_media_type": None,
                    "force_sub_enabled": 0,
                    "force_sub_channels": None,
                    "send_only_enabled": 0,
                    "send_only_delay": 86400,
                    "added_at": now
                }
            },
            upsert=True
        )
        return

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
    if is_mongodb_enabled():
        db = get_mongo_db()
        doc = await db.chats.find_one({"_id": chat_id})
        return _format_mongo_chat(doc)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_all_chats() -> List[Dict[str, Any]]:
    """Retrieve all registered chats."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        cursor = db.chats.find({}).sort("added_at", -1)
        chats = []
        async for doc in cursor:
            formatted = _format_mongo_chat(doc)
            if formatted:
                chats.append(formatted)
        return chats

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM chats ORDER BY added_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def toggle_chat_auto_accept(chat_id: int) -> bool:
    """Toggle auto accept flag for a chat and return new boolean state."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        doc = await db.chats.find_one({"_id": chat_id})
        current_state = doc.get("auto_accept", 1) if doc else 1
        new_state = 0 if current_state == 1 else 1
        await db.chats.update_one({"_id": chat_id}, {"$set": {"auto_accept": new_state}}, upsert=True)
        return new_state == 1

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
    if is_mongodb_enabled():
        db = get_mongo_db()
        doc = await db.chats.find_one({"_id": chat_id})
        current_state = doc.get("welcome_enabled", 1) if doc else 1
        new_state = 0 if current_state == 1 else 1
        await db.chats.update_one({"_id": chat_id}, {"$set": {"welcome_enabled": new_state}}, upsert=True)
        return new_state == 1

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT welcome_enabled FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            current_state = row[0] if row else 1
            new_state = 0 if current_state == 1 else 1

        await db.execute("UPDATE chats SET welcome_enabled = ? WHERE chat_id = ?", (new_state, chat_id))
        await db.commit()
        return new_state == 1


async def set_chat_custom_welcome(
    chat_id: int,
    message: Optional[str],
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None
):
    """Set or clear custom welcome message and media for a chat."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        await db.chats.update_one(
            {"_id": chat_id},
            {
                "$set": {
                    "custom_welcome_message": message,
                    "custom_welcome_media": media_file_id,
                    "custom_welcome_media_type": media_type
                }
            },
            upsert=True
        )
        return

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


async def toggle_chat_force_sub(chat_id: int) -> bool:
    """Toggle per-channel force join flag and return new state."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        doc = await db.chats.find_one({"_id": chat_id})
        current_state = doc.get("force_sub_enabled", 0) if doc else 0
        new_state = 0 if current_state == 1 else 1
        await db.chats.update_one({"_id": chat_id}, {"$set": {"force_sub_enabled": new_state}}, upsert=True)
        return new_state == 1

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT force_sub_enabled FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            current_state = row[0] if row and row[0] is not None else 0
            new_state = 0 if current_state == 1 else 1

        await db.execute("UPDATE chats SET force_sub_enabled = ? WHERE chat_id = ?", (new_state, chat_id))
        await db.commit()
        return new_state == 1


async def set_chat_force_sub_channels(chat_id: int, channels: Optional[str]):
    """Set or clear configured force join channels for a specific chat."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        await db.chats.update_one(
            {"_id": chat_id},
            {
                "$set": {
                    "force_sub_channels": channels,
                    "force_sub_enabled": 1 if channels else 0
                }
            },
            upsert=True
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE chats 
               SET force_sub_channels = ?,
                   force_sub_enabled = CASE WHEN ? IS NOT NULL AND ? != '' THEN 1 ELSE 0 END
               WHERE chat_id = ?""",
            (channels, channels, channels, chat_id)
        )
        await db.commit()


async def toggle_chat_send_only(chat_id: int) -> bool:
    """Toggle Send Only mode (delayed auto-accept with force join DM) for a specific chat."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        doc = await db.chats.find_one({"_id": chat_id})
        current_state = doc.get("send_only_enabled", 0) if doc else 0
        new_state = 0 if current_state == 1 else 1
        await db.chats.update_one({"_id": chat_id}, {"$set": {"send_only_enabled": new_state}}, upsert=True)
        return new_state == 1

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT send_only_enabled FROM chats WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            current_state = row[0] if row and row[0] is not None else 0
            new_state = 0 if current_state == 1 else 1

        await db.execute("UPDATE chats SET send_only_enabled = ? WHERE chat_id = ?", (new_state, chat_id))
        await db.commit()
        return new_state == 1


async def set_chat_send_only_delay(chat_id: int, delay_seconds: int):
    """Set the delay timer in seconds for Send Only auto-approval."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        await db.chats.update_one(
            {"_id": chat_id},
            {"$set": {"send_only_delay": delay_seconds}},
            upsert=True
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE chats SET send_only_delay = ? WHERE chat_id = ?",
            (delay_seconds, chat_id)
        )
        await db.commit()


async def add_delayed_approval(chat_id: int, user_id: int, delay_seconds: int):
    """Schedule a delayed auto-approval for a user."""
    now = datetime.datetime.now(datetime.timezone.utc)
    approve_at = now + datetime.timedelta(seconds=delay_seconds)

    if is_mongodb_enabled():
        db = get_mongo_db()
        await db.delayed_approvals.update_one(
            {"chat_id": chat_id, "user_id": user_id, "status": "pending"},
            {
                "$set": {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "scheduled_at": now,
                    "approve_at": approve_at,
                    "status": "pending"
                }
            },
            upsert=True
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Cancel any previous pending approvals for same user/chat to prevent duplicates
        await db.execute(
            "UPDATE delayed_approvals SET status = 'cancelled' WHERE chat_id = ? AND user_id = ? AND status = 'pending'",
            (chat_id, user_id)
        )
        await db.execute("""
            INSERT INTO delayed_approvals (chat_id, user_id, scheduled_at, approve_at, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (chat_id, user_id, now.isoformat(), approve_at.isoformat()))
        await db.commit()


async def get_due_delayed_approvals() -> List[Dict[str, Any]]:
    """Retrieve all pending delayed approvals that are due for approval."""
    now = datetime.datetime.now(datetime.timezone.utc)

    if is_mongodb_enabled():
        db = get_mongo_db()
        cursor = db.delayed_approvals.find({
            "status": "pending",
            "approve_at": {"$lte": now}
        })
        results = []
        async for doc in cursor:
            results.append({
                "id": str(doc.get("_id")),
                "chat_id": doc.get("chat_id"),
                "user_id": doc.get("user_id"),
                "approve_at": doc.get("approve_at")
            })
        return results

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        now_iso = now.isoformat()
        async with db.execute(
            "SELECT id, chat_id, user_id, approve_at FROM delayed_approvals WHERE status = 'pending' AND approve_at <= ?",
            (now_iso,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def mark_delayed_approval_completed(chat_id: int, user_id: int, status: str = "approved_manual"):
    """Mark a pending delayed approval as resolved (approved_manual, approved_delayed, or cancelled)."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        await db.delayed_approvals.update_many(
            {"chat_id": chat_id, "user_id": user_id, "status": "pending"},
            {"$set": {"status": status}}
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE delayed_approvals SET status = ? WHERE chat_id = ? AND user_id = ? AND status = 'pending'",
            (status, chat_id, user_id)
        )
        await db.commit()


# ==========================================
# JOIN REQUEST LOGGING & STATS
# ==========================================

async def log_join_request(user_id: int, chat_id: int, status: str = "approved"):
    """Log an approved join request."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        now = datetime.datetime.now(datetime.timezone.utc)
        await db.join_requests.insert_one({
            "user_id": user_id,
            "chat_id": chat_id,
            "status": status,
            "created_at": now
        })
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO join_requests (user_id, chat_id, status)
            VALUES (?, ?, ?)
        """, (user_id, chat_id, status))
        await db.commit()


async def get_analytics() -> Dict[str, Any]:
    """Calculate overall statistics."""
    if is_mongodb_enabled():
        db = get_mongo_db()
        total_requests = await db.join_requests.count_documents({"status": "approved"})
        total_chats = await db.chats.count_documents({})
        total_users = await db.users.count_documents({})

        today_start = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_requests = await db.join_requests.count_documents({
            "status": "approved",
            "created_at": {"$gte": today_start}
        })

        return {
            "total_approved": total_requests,
            "total_chats": total_chats,
            "total_users": total_users,
            "today_approved": today_requests
        }

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

"""
DEADMAN SCRAPER - MongoDB Integration
======================================
User configuration, preferences, and multi-user support.

Features:
- User accounts with configuration
- Scraper preferences per user
- Hidden/seen items tracking
- Multi-user dashboard support

Based on zilbers/dark-web-scraper patterns, enhanced for DeadMan.
"""

import logging
from datetime import datetime
from typing import Any

try:
    from pymongo import MongoClient
    from bson import ObjectId
    HAS_MONGODB = True
except ImportError:
    HAS_MONGODB = False
    MongoClient = None
    ObjectId = None

logger = logging.getLogger("DeadMan.MongoDB")


# Default user configuration schema
DEFAULT_USER_CONFIG = {
    "target_urls": [],
    "keywords": [
        "DDOS", "exploits", "credit cards", "bitcoin", "passwords",
        "hacked", "ransomware", "stolen", "leaked", "fullz"
    ],
    "cooldown_minutes": 5,
    "use_tor": True,
    "use_llm": False,
    "extract_strategy": "auto",
    "notifications_enabled": True,
    "darkweb_enabled": True
}


class MongoDBStore:
    """
    MongoDB storage backend for user management and configuration.

    Provides:
    - User CRUD operations
    - Scraper configuration per user
    - Hidden items tracking (mark as seen)
    - Session management
    """

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "deadman_scraper"
    ):
        """
        Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI
            database: Database name
        """
        if not HAS_MONGODB:
            raise ImportError(
                "pymongo package required. Install with: pip install pymongo"
            )

        self.client = MongoClient(uri)
        self.db = self.client[database]
        self.users = self.db["users"]
        self.sessions = self.db["sessions"]
        self.scraper_status = self.db["scraper_status"]

        # Create indexes
        self.users.create_index("email", unique=True)
        self.sessions.create_index("user_id")

        logger.info(f"MongoDB connected: {uri}, database: {database}")

    # ==================== USER OPERATIONS ====================

    def create_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        config: dict | None = None
    ) -> str:
        """
        Create a new user.

        Args:
            email: User email (unique)
            name: Display name
            password_hash: Hashed password
            config: Optional custom configuration

        Returns:
            User ID string
        """
        user_doc = {
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "config": config or DEFAULT_USER_CONFIG.copy(),
            "alerts": [],  # Hidden item IDs
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None
        }

        result = self.users.insert_one(user_doc)
        logger.info(f"Created user: {email}")
        return str(result.inserted_id)

    def get_user(self, user_id: str) -> dict | None:
        """Get user by ID."""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email."""
        user = self.users.find_one({"email": email})
        if user:
            user["id"] = str(user.pop("_id"))
        return user

    def get_all_users(self) -> list[dict]:
        """Get all users."""
        users = []
        for user in self.users.find():
            user["id"] = str(user.pop("_id"))
            users.append(user)
        return users

    def update_user(self, user_id: str, updates: dict) -> bool:
        """Update user fields."""
        updates["updated_at"] = datetime.utcnow()
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_user(self, user_id: str) -> bool:
        """Soft delete user."""
        return self.update_user(user_id, {"deleted_at": datetime.utcnow()})

    # ==================== CONFIGURATION ====================

    def get_user_config(self, user_id: str) -> dict:
        """Get user's scraper configuration."""
        user = self.get_user(user_id)
        if user:
            return user.get("config", DEFAULT_USER_CONFIG.copy())
        return DEFAULT_USER_CONFIG.copy()

    def update_user_config(self, user_id: str, config: dict) -> bool:
        """Update user's scraper configuration."""
        return self.update_user(user_id, {"config": config})

    def merge_user_config(self, user_id: str, partial_config: dict) -> bool:
        """Merge partial config updates into existing config."""
        current = self.get_user_config(user_id)
        current.update(partial_config)
        return self.update_user_config(user_id, current)

    # ==================== ALERTS (HIDDEN ITEMS) ====================

    def get_user_alerts(self, user_id: str) -> list[str]:
        """Get list of hidden item IDs for user."""
        user = self.get_user(user_id)
        if user:
            return user.get("alerts", [])
        return []

    def add_alert(self, user_id: str, item_id: str) -> bool:
        """Add item to user's hidden list."""
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {"alerts": item_id}}
        )
        return result.modified_count > 0

    def remove_alert(self, user_id: str, item_id: str) -> bool:
        """Remove item from user's hidden list."""
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"alerts": item_id}}
        )
        return result.modified_count > 0

    def set_alerts(self, user_id: str, item_ids: list[str]) -> bool:
        """Replace user's hidden list."""
        return self.update_user(user_id, {"alerts": item_ids})

    def clear_alerts(self, user_id: str) -> bool:
        """Clear all hidden items for user."""
        return self.set_alerts(user_id, [])

    # ==================== SCRAPER STATUS ====================

    def get_scraper_status(self) -> dict:
        """Get global scraper status."""
        status = self.scraper_status.find_one({"_id": "global"})
        if status:
            del status["_id"]
            return status
        return {
            "active": False,
            "message": "Idle",
            "last_run": None,
            "checked": False
        }

    def set_scraper_status(
        self,
        active: bool,
        message: str = "",
        checked: bool = False
    ) -> None:
        """Update global scraper status."""
        self.scraper_status.update_one(
            {"_id": "global"},
            {
                "$set": {
                    "active": active,
                    "message": message,
                    "checked": checked,
                    "last_run": datetime.utcnow() if active else None,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )

    def mark_status_checked(self) -> None:
        """Mark status as checked (user has seen it)."""
        self.scraper_status.update_one(
            {"_id": "global"},
            {"$set": {"checked": True}}
        )

    # ==================== SESSIONS ====================

    def create_session(self, user_id: str, token: str) -> str:
        """Create a new session."""
        session_doc = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow(),
            "expires_at": None  # Can be set for expiring sessions
        }
        result = self.sessions.insert_one(session_doc)

        # Update user's last login
        self.update_user(user_id, {"last_login": datetime.utcnow()})

        return str(result.inserted_id)

    def get_session(self, token: str) -> dict | None:
        """Get session by token."""
        session = self.sessions.find_one({"token": token})
        if session:
            session["id"] = str(session.pop("_id"))
        return session

    def delete_session(self, token: str) -> bool:
        """Delete a session (logout)."""
        result = self.sessions.delete_one({"token": token})
        return result.deleted_count > 0

    # ==================== STATISTICS ====================

    def get_user_count(self) -> int:
        """Get total user count."""
        return self.users.count_documents({"deleted_at": {"$exists": False}})

    def get_stats(self) -> dict:
        """Get database statistics."""
        return {
            "user_count": self.get_user_count(),
            "session_count": self.sessions.count_documents({}),
            "database": self.db.name
        }

    # ==================== UTILITIES ====================

    def ensure_default_user(self) -> str:
        """
        Ensure a default user exists for single-user mode.
        Returns the user ID.
        """
        default_email = "default@deadman.local"
        user = self.get_user_by_email(default_email)

        if user:
            return user["id"]

        return self.create_user(
            email=default_email,
            name="DeadMan",
            password_hash="",  # No password for default user
            config=DEFAULT_USER_CONFIG.copy()
        )

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")

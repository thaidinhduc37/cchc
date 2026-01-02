import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from app.config.app_config import Config

config = Config()

class UserManager:
    def __init__(self):
        self.db_path = config.DB_PATH  # Use directly
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent.parent.parent / "database" / "schema.sql"
        with open(schema_path) as f:
            schema = f.read()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema)

    def _dict_factory(self, cursor, row):
        """Convert rows to dictionaries"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user"""
        user_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (id, email, password, fullname, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                user_data["email"],
                user_data["password"],
                user_data["fullname"],
                user_data.get("phone")
            ))
            
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            return cursor.fetchone()

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user"""
        valid_fields = {"email", "password", "fullname", "phone", "is_active", "role"}
        update_fields = {k: v for k, v in update_data.items() if k in valid_fields}
        
        if not update_fields:
            return None
            
        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values()) + [user_id]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = self._dict_factory
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE users 
                SET {set_clause}
                WHERE id = ?
                RETURNING *
            """, values)
            
            return cursor.fetchone()
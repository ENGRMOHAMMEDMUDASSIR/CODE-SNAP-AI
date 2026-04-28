# backend/database.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="codesnap.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    repo_url TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # Users table for authentication
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Analysis history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    repo_url TEXT,
                    analysis_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Comparison history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    repos TEXT,
                    comparison_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
    
    def get_cached(self, repo_url: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT data, expires_at FROM cache WHERE repo_url = ? AND expires_at > datetime('now')",
                (repo_url,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row['data'])
        return None
    
    def save_cache(self, repo_url: str, data: Dict, ttl_hours: int = 24):
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (repo_url, data, expires_at) VALUES (?, ?, ?)",
                (repo_url, json.dumps(data), expires_at.isoformat())
            )
    
    def create_user(self, username: str, password_hash: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user(self, username: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            return cursor.fetchone()
    
    def save_history(self, user_id: int, repo_url: str, analysis_data: Dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO analysis_history (user_id, repo_url, analysis_data) VALUES (?, ?, ?)",
                (user_id, repo_url, json.dumps(analysis_data))
            )
    
    def get_history(self, user_id: int, limit: int = 10):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT repo_url, analysis_data, created_at FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def save_comparison(self, user_id: int, repos: list, comparison_data: Dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO comparisons (user_id, repos, comparison_data) VALUES (?, ?, ?)",
                (user_id, json.dumps(repos), json.dumps(comparison_data))
            )
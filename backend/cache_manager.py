# backend/cache_manager.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.config import config
import hashlib

class CacheManager:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.ttl_hours = config.CACHE_TTL_HOURS
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_url TEXT UNIQUE NOT NULL,
                    repo_hash TEXT NOT NULL,
                    analysis_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_hash ON analyses(repo_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON analyses(expires_at)")
    
    def _get_repo_hash(self, repo_url: str) -> str:
        return hashlib.md5(repo_url.encode()).hexdigest()
    
    def get_cached(self, repo_url: str) -> Optional[Dict[str, Any]]:
        repo_hash = self._get_repo_hash(repo_url)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT analysis_data, expires_at FROM analyses WHERE repo_hash = ?",
                (repo_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                expires_at = datetime.fromisoformat(row['expires_at'])
                if expires_at > datetime.now():
                    return json.loads(row['analysis_data'])
                else:
                    self.delete_cached(repo_url)
        
        return None
    
    def save_analysis(self, repo_url: str, analysis_data: Dict[str, Any]):
        repo_hash = self._get_repo_hash(repo_url)
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=self.ttl_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analyses 
                   (repo_url, repo_hash, analysis_data, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (repo_url, repo_hash, json.dumps(analysis_data), 
                 created_at.isoformat(), expires_at.isoformat())
            )
    
    def delete_cached(self, repo_url: str):
        repo_hash = self._get_repo_hash(repo_url)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analyses WHERE repo_hash = ?", (repo_hash,))
    
    def clear_expired(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analyses WHERE expires_at < ?", (datetime.now().isoformat(),))
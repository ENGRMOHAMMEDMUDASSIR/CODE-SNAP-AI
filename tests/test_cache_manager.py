# tests/test_cache_manager.py
import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from backend.cache_manager import CacheManager
from backend.config import config

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    
    original_db = config.DATABASE_PATH
    config.DATABASE_PATH = temp_path
    
    yield temp_path
    
    config.DATABASE_PATH = original_db
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture
def cache_manager(temp_db):
    return CacheManager()

def test_save_and_get_cached_analysis(cache_manager):
    repo_url = "https://github.com/test/repo"
    analysis_data = {
        "repo_name": "repo",
        "description": "Test description",
        "tech_stack": ["Python"]
    }
    
    cache_manager.save_analysis(repo_url, analysis_data)
    cached = cache_manager.get_cached(repo_url)
    
    assert cached is not None
    assert cached["repo_name"] == "repo"
    assert cached["description"] == "Test description"

def test_get_cached_returns_none_for_nonexistent(cache_manager):
    result = cache_manager.get_cached("https://github.com/nonexistent/repo")
    assert result is None

def test_cache_expiry(cache_manager):
    repo_url = "https://github.com/test/repo"
    analysis_data = {"test": "data"}
    
    cache_manager.ttl_hours = 0
    cache_manager.save_analysis(repo_url, analysis_data)
    
    cached = cache_manager.get_cached(repo_url)
    assert cached is None

def test_delete_cached(cache_manager):
    repo_url = "https://github.com/test/repo"
    analysis_data = {"test": "data"}
    
    cache_manager.save_analysis(repo_url, analysis_data)
    cache_manager.delete_cached(repo_url)
    
    cached = cache_manager.get_cached(repo_url)
    assert cached is None

def test_clear_expired(cache_manager):
    repo_url = "https://github.com/test/repo"
    analysis_data = {"test": "data"}
    
    cache_manager.save_analysis(repo_url, analysis_data)
    
    with cache_manager._get_db_connection() as conn:
        conn.execute(
            "UPDATE analyses SET expires_at = ? WHERE repo_hash = ?",
            ((datetime.now() - timedelta(hours=1)).isoformat(), 
             cache_manager._get_repo_hash(repo_url))
        )
    
    cache_manager.clear_expired()
    cached = cache_manager.get_cached(repo_url)
    assert cached is None

def test_save_analysis_updates_existing(cache_manager):
    repo_url = "https://github.com/test/repo"
    
    cache_manager.save_analysis(repo_url, {"version": 1})
    cache_manager.save_analysis(repo_url, {"version": 2})
    
    cached = cache_manager.get_cached(repo_url)
    assert cached["version"] == 2

def test_repo_hash_consistency(cache_manager):
    url1 = "https://github.com/owner/repo"
    url2 = "https://github.com/owner/repo"
    
    hash1 = cache_manager._get_repo_hash(url1)
    hash2 = cache_manager._get_repo_hash(url2)
    
    assert hash1 == hash2
# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # or "anthropic"
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
    
    # GitHub
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional for higher rate limits
    
    # Cache
    CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", 24))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "codesnap.db")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 5))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", 60))  # seconds
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

config = Config()
# backend/rate_limiter.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
import os
import time
from datetime import datetime

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting for the app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return limiter

# Simple in-memory rate limiter (no Redis required)
class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}
    
    def check_limit(self, identifier: str, limit: int = 30, window: int = 60) -> bool:
        """
        Check if request is allowed
        - identifier: user_id or IP address
        - limit: max requests per window
        - window: time window in seconds
        """
        current_time = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < window
        ]
        
        # Check limit
        if len(self.requests[identifier]) < limit:
            self.requests[identifier].append(current_time)
            return True
        
        return False

rate_limiter = SimpleRateLimiter()

def check_user_rate_limit(user_id: int, endpoint: str):
    """Middleware to check rate limit for authenticated users"""
    limit = int(os.getenv("RATE_LIMIT_REQUESTS", 50))
    period = int(os.getenv("RATE_LIMIT_PERIOD", 60))
    
    if not rate_limiter.check_limit(f"user_{user_id}_{endpoint}", limit, period):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests per {period} seconds."
        )
    return True

def check_ip_rate_limit(ip: str):
    """Middleware to check rate limit for non-authenticated requests"""
    limit = 20  # Stricter limit for unauthenticated
    period = 60
    
    if not rate_limiter.check_limit(f"ip_{ip}", limit, period):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait and try again."
        )
    return True
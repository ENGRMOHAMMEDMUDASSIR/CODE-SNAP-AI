# backend/rate_limiter.py - Updated with expanded free plan
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
import os
import time
from datetime import datetime, timedelta

limiter = Limiter(key_func=get_remote_address)

FREE_TIER_LIMIT = int(os.getenv("FREE_TIER_LIMIT", 100))
FREE_TIER_DAILY = int(os.getenv("FREE_TIER_DAILY", 1000))
PREMIUM_TIER_LIMIT = int(os.getenv("PREMIUM_TIER_LIMIT", 500))
PREMIUM_TIER_DAILY = int(os.getenv("PREMIUM_TIER_DAILY", 10000))

def setup_rate_limiting(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return limiter

class EnhancedRateLimiter:
    def __init__(self):
        self.per_minute_requests = {}
        self.per_day_requests = {}
    
    def check_limit(self, identifier: str, is_premium: bool = False) -> tuple:
        current_time = time.time()
        daily_limit = PREMIUM_TIER_DAILY if is_premium else FREE_TIER_DAILY
        minute_limit = PREMIUM_TIER_LIMIT if is_premium else FREE_TIER_LIMIT
        
        if identifier not in self.per_minute_requests:
            self.per_minute_requests[identifier] = []
        
        self.per_minute_requests[identifier] = [
            req_time for req_time in self.per_minute_requests[identifier]
            if current_time - req_time < 60
        ]
        
        if identifier not in self.per_day_requests:
            self.per_day_requests[identifier] = []
        
        self.per_day_requests[identifier] = [
            req_time for req_time in self.per_day_requests[identifier]
            if current_time - req_time < 86400
        ]
        
        if len(self.per_minute_requests[identifier]) >= minute_limit:
            reset_time = 60 - (current_time - self.per_minute_requests[identifier][0])
            return False, 0, int(reset_time)
        
        if len(self.per_day_requests[identifier]) >= daily_limit:
            reset_time = 86400 - (current_time - self.per_day_requests[identifier][0])
            return False, 0, int(reset_time / 3600)
        
        self.per_minute_requests[identifier].append(current_time)
        self.per_day_requests[identifier].append(current_time)
        
        remaining_minute = minute_limit - len(self.per_minute_requests[identifier])
        remaining_day = daily_limit - len(self.per_day_requests[identifier])
        
        return True, min(remaining_minute, remaining_day), 0

rate_limiter = EnhancedRateLimiter()

class TrialPackManager:
    def __init__(self):
        self.trial_users = {}
    
    def grant_trial(self, user_id: str, days: int = 7):
        expiry = datetime.now() + timedelta(days=days)
        self.trial_users[user_id] = expiry.timestamp()
        return expiry
    
    def has_trial(self, user_id: str) -> bool:
        if user_id not in self.trial_users:
            return False
        return time.time() < self.trial_users[user_id]
    
    def get_trial_remaining(self, user_id: str) -> int:
        if user_id not in self.trial_users:
            return 0
        remaining = self.trial_users[user_id] - time.time()
        return max(0, int(remaining / 86400))

trial_manager = TrialPackManager()

def check_user_rate_limit(user_id: int, endpoint: str, is_premium: bool = False):
    user_identifier = f"user_{user_id}_{endpoint}"
    allowed, remaining, reset_time = rate_limiter.check_limit(user_identifier, is_premium)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please wait {reset_time} seconds.",
                "remaining": 0,
                "reset": reset_time,
                "limit": PREMIUM_TIER_LIMIT if is_premium else FREE_TIER_LIMIT
            }
        )
    return {"allowed": True, "remaining": remaining, "reset": reset_time}

def check_ip_rate_limit(ip: str):
    user_identifier = f"ip_{ip}"
    allowed, remaining, reset_time = rate_limiter.check_limit(user_identifier, is_premium=False)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please wait {reset_time} seconds or sign up for higher limits.",
                "remaining": 0,
                "reset": reset_time
            }
        )
    return {"allowed": True, "remaining": remaining}
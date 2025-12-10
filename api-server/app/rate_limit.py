"""Simple in-memory rate limiter (can be replaced with Redis/DB later)."""
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict


class RateLimiter:
    """In-memory rate limiter for per-user request limiting."""
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per user
        """
        self.requests_per_minute = requests_per_minute
        # Format: {user_id: [list of request timestamps]}
        self.user_requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Check if a request from a user is allowed.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        
        # Clean up old timestamps
        user_requests = self.user_requests[user_id]
        user_requests[:] = [ts for ts in user_requests if ts > cutoff]
        
        # Check if limit exceeded
        if len(user_requests) >= self.requests_per_minute:
            return False
        
        # Add current request timestamp
        user_requests.append(now)
        return True
    
    def reset(self, user_id: str = None):
        """
        Reset rate limits for a user or all users.
        
        Args:
            user_id: User ID to reset, or None to reset all
        """
        if user_id:
            self.user_requests.pop(user_id, None)
        else:
            self.user_requests.clear()


# Global rate limiter instance (will be initialized from settings)
rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        from app.config import settings
        rate_limiter = RateLimiter(settings.rate_limit_requests_per_minute)
    return rate_limiter


"""
Rate Limiter Middleware
=======================
Rate limit requests per user.
"""

import time
from functools import wraps
from typing import Dict, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import get_logger

logger = get_logger(__name__)

# In-memory rate limit storage
_rate_limits: Dict[int, list] = {}


def rate_limit(calls: int = 5, period: int = 60):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            current_time = time.time()
            
            # Initialize user's rate limit record
            if user_id not in _rate_limits:
                _rate_limits[user_id] = []
            
            # Clean old entries
            _rate_limits[user_id] = [
                t for t in _rate_limits[user_id]
                if current_time - t < period
            ]
            
            # Check if limit exceeded
            if len(_rate_limits[user_id]) >= calls:
                remaining_time = int(period - (current_time - _rate_limits[user_id][0]))
                
                await update.message.reply_text(
                    f"⏳ **Rate Limit Exceeded!**\n\n"
                    f"Please wait {remaining_time} seconds before trying again.",
                    parse_mode='Markdown'
                )
                return
            
            # Record this call
            _rate_limits[user_id].append(current_time)
            
            # Call the function
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


class RateLimiter:
    """Advanced rate limiter with different tiers"""
    
    def __init__(self):
        self._limits: Dict[int, Dict] = {}
    
    def is_allowed(self, user_id: int, tier: str = 'default') -> Tuple[bool, int]:
        """
        Check if user is allowed to make a request.
        
        Args:
            user_id: User ID
            tier: Rate limit tier
            
        Returns:
            Tuple of (allowed, remaining_seconds)
        """
        tiers = {
            'free': {'calls': 5, 'period': 60},
            'premium': {'calls': 50, 'period': 60},
            'admin': {'calls': 1000, 'period': 60},
        }
        
        config = tiers.get(tier, tiers['free'])
        current_time = time.time()
        
        # Initialize
        if user_id not in self._limits:
            self._limits[user_id] = {
                'calls': [],
                'tier': tier
            }
        
        # Clean old calls
        self._limits[user_id]['calls'] = [
            t for t in self._limits[user_id]['calls']
            if current_time - t < config['period']
        ]
        
        # Check limit
        if len(self._limits[user_id]['calls']) >= config['calls']:
            remaining = int(config['period'] - (current_time - self._limits[user_id]['calls'][0]))
            return False, remaining
        
        # Record call
        self._limits[user_id]['calls'].append(current_time)
        return True, 0

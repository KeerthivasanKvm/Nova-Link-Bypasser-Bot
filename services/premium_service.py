"""
Premium Service
===============
Manage premium subscriptions and features.
"""

from datetime import datetime, timedelta
from typing import Optional

from database.firebase_db import FirebaseDB
from database.models import User
from config import premium_config
from utils.logger import get_logger

logger = get_logger(__name__)


class PremiumService:
    """Service for managing premium subscriptions"""
    
    def __init__(self, db: FirebaseDB):
        self.db = db
    
    async def is_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        user = await self.db.get_user(user_id)
        if not user:
            return False
        return user.is_premium_active()
    
    async def get_remaining_days(self, user_id: int) -> Optional[int]:
        """Get remaining premium days"""
        user = await self.db.get_user(user_id)
        if not user or not user.premium_expiry:
            return None
        
        remaining = user.premium_expiry - datetime.utcnow()
        return max(0, remaining.days)
    
    async def activate_premium(
        self,
        user_id: int,
        duration_days: float
    ) -> bool:
        """
        Activate premium for user.
        
        Args:
            user_id: User ID
            duration_days: Duration in days
            
        Returns:
            True if activated successfully
        """
        user = await self.db.get_user(user_id)
        if not user:
            return False
        
        if not user.is_premium:
            # New premium
            user.is_premium = True
            user.premium_start = datetime.utcnow()
            user.premium_expiry = datetime.utcnow() + timedelta(days=duration_days)
        else:
            # Extend existing
            user.premium_expiry += timedelta(days=duration_days)
        
        await self.db.update_user(user)
        logger.info(f"Activated premium for user {user_id} for {duration_days} days")
        return True
    
    async def deactivate_premium(self, user_id: int) -> bool:
        """Deactivate premium for user"""
        user = await self.db.get_user(user_id)
        if not user:
            return False
        
        user.is_premium = False
        user.premium_expiry = None
        
        await self.db.update_user(user)
        logger.info(f"Deactivated premium for user {user_id}")
        return True
    
    async def get_premium_users(self):
        """Get all premium users"""
        return await self.db.get_premium_users()
    
    async def check_expiring_premiums(self, days_before: int = 3):
        """
        Check for expiring premium subscriptions.
        
        Args:
            days_before: Days before expiry to check
            
        Returns:
            List of users with expiring premium
        """
        premium_users = await self.get_premium_users()
        expiring = []
        
        for user in premium_users:
            if user.premium_expiry:
                days_remaining = (user.premium_expiry - datetime.utcnow()).days
                if days_remaining <= days_before and days_remaining >= 0:
                    expiring.append(user)
        
        return expiring

"""
Referral System
===============
Manage user referrals and rewards.
"""

from datetime import datetime, timedelta
from typing import Optional

from database.firebase_db import FirebaseDB
from database.models import User
from config import premium_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ReferralSystem:
    """Service for managing referrals"""
    
    def __init__(self, db: FirebaseDB):
        self.db = db
    
    async def process_referral(self, new_user_id: int, referrer_id: int) -> bool:
        """
        Process a new referral.
        
        Args:
            new_user_id: New user who joined
            referrer_id: User who referred them
            
        Returns:
            True if processed successfully
        """
        if not premium_config.REFERRAL_ENABLED:
            return False
        
        # Get referrer
        referrer = await self.db.get_user(referrer_id)
        if not referrer:
            return False
        
        # Check if already at max
        if referrer.referral_earned_days >= premium_config.REFERRAL_MAX_REWARD:
            logger.info(f"Referrer {referrer_id} at max reward limit")
            return False
        
        # Update referrer
        referrer.referral_count += 1
        referrer.referral_earned_days += premium_config.REFERRAL_REWARD_DAYS
        
        # Add premium time
        if not referrer.is_premium:
            referrer.is_premium = True
            referrer.premium_start = datetime.utcnow()
            referrer.premium_expiry = datetime.utcnow() + timedelta(days=premium_config.REFERRAL_REWARD_DAYS)
        else:
            referrer.premium_expiry += timedelta(days=premium_config.REFERRAL_REWARD_DAYS)
        
        await self.db.update_user(referrer)
        
        logger.info(f"Processed referral: {new_user_id} referred by {referrer_id}")
        return True
    
    async def get_referral_stats(self, user_id: int) -> dict:
        """Get referral statistics for user"""
        user = await self.db.get_user(user_id)
        if not user:
            return {
                'referral_code': None,
                'referral_count': 0,
                'earned_days': 0,
                'max_reward': premium_config.REFERRAL_MAX_REWARD
            }
        
        return {
            'referral_code': user.referral_code,
            'referral_count': user.referral_count,
            'earned_days': user.referral_earned_days,
            'max_reward': premium_config.REFERRAL_MAX_REWARD
        }
    
    async def can_earn_more(self, user_id: int) -> bool:
        """Check if user can earn more referral rewards"""
        user = await self.db.get_user(user_id)
        if not user:
            return True
        return user.referral_earned_days < premium_config.REFERRAL_MAX_REWARD

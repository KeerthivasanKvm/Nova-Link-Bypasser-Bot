"""
Notification Service
====================
Send notifications and reminders to users.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

from telegram import Bot

from database.firebase_db import FirebaseDB
from database.models import User
from config import notification_config
from utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self, bot: Bot, db: FirebaseDB):
        self.bot = bot
        self.db = db
        self._running = False
        self._task = None
    
    async def start(self):
        """Start notification service"""
        self._running = True
        self._task = asyncio.create_task(self._notification_loop())
        logger.info("Notification service started")
    
    async def stop(self):
        """Stop notification service"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification service stopped")
    
    async def _notification_loop(self):
        """Main notification loop"""
        while self._running:
            try:
                # Check for expiring premiums
                await self._check_expiring_premiums()
                
                # Wait for next check
                await asyncio.sleep(notification_config.CHECK_INTERVAL * 60)
                
            except Exception as e:
                logger.error(f"Notification loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_expiring_premiums(self):
        """Check and notify users with expiring premium"""
        from services.premium_service import PremiumService
        
        premium_service = PremiumService(self.db)
        
        for days in notification_config.REMINDER_DAYS:
            expiring_users = await premium_service.check_expiring_premiums(days)
            
            for user in expiring_users:
                await self._send_expiry_reminder(user, days)
    
    async def _send_expiry_reminder(self, user: User, days_remaining: int):
        """Send premium expiry reminder"""
        try:
            if days_remaining == 1:
                message = f"""
⏰ **Premium Expiring Tomorrow!**

Hi {user.first_name},

Your premium subscription expires **tomorrow**!

Renew now to continue enjoying:
✅ Unlimited bypasses
✅ Priority processing
✅ All bypass methods

Contact admin to renew your subscription.
"""
            else:
                message = f"""
⏰ **Premium Expiring Soon!**

Hi {user.first_name},

Your premium subscription expires in **{days_remaining} days**.

Don't lose your premium benefits:
✅ Unlimited bypasses
✅ Priority processing
✅ All bypass methods

Contact admin to renew your subscription.
"""
            
            await self.bot.send_message(
                chat_id=user.user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent expiry reminder to user {user.user_id} ({days_remaining} days)")
            
        except Exception as e:
            logger.error(f"Failed to send reminder to {user.user_id}: {e}")
    
    async def send_welcome_premium(self, user_id: int, duration_days: float):
        """Send welcome message for new premium users"""
        try:
            message = f"""
🎉 **Welcome to Premium!**

Congratulations! Your premium subscription is now active!

**Duration:** {duration_days} days
**Status:** ✅ Active

**Your Premium Benefits:**
✅ Unlimited daily bypasses
✅ Priority processing
✅ Access to all bypass methods
✅ No waiting time
✅ Premium support

Enjoy your premium experience! 🚀
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome premium to {user_id}: {e}")
    
    async def send_referral_reward(self, user_id: int, days_earned: int):
        """Send referral reward notification"""
        try:
            message = f"""
🎁 **Referral Reward Earned!**

Congratulations! You earned **{days_earned} days** of premium!

Someone joined using your referral link!

Keep sharing your link to earn more premium days!
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Failed to send referral reward to {user_id}: {e}")

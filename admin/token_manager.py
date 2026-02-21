"""
Token Manager
=============
Manage access tokens and reset keys.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List

from database.firebase_db import FirebaseDB
from database.models import AccessToken, ResetKey
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenManager:
    """Manage access tokens and reset keys"""
    
    def __init__(self, db: FirebaseDB):
        self.db = db
    
    async def generate_access_token(
        self,
        duration_days: float,
        created_by: int
    ) -> AccessToken:
        """
        Generate new access token.
        
        Args:
            duration_days: Token validity in days
            created_by: Admin who created the token
            
        Returns:
            AccessToken object
        """
        token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        
        token_obj = AccessToken(
            token=token,
            duration_days=duration_days,
            created_by=created_by
        )
        
        await self.db.create_access_token(token_obj)
        logger.info(f"Generated access token: {token} by {created_by}")
        
        return token_obj
    
    async def validate_token(self, token: str) -> Optional[AccessToken]:
        """
        Validate and get token.
        
        Args:
            token: Token string
            
        Returns:
            AccessToken if valid, None otherwise
        """
        return await self.db.get_access_token(token)
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if revoked successfully
        """
        return await self.db.delete_access_token(token)
    
    async def generate_reset_key(
        self,
        created_by: int,
        max_uses: int = 1,
        expires_hours: int = 24
    ) -> ResetKey:
        """
        Generate new reset key.
        
        Args:
            created_by: Admin who created the key
            max_uses: Maximum number of uses
            expires_hours: Expiry time in hours
            
        Returns:
            ResetKey object
        """
        key = 'RESET_' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        
        reset_key = ResetKey(
            key=key,
            created_by=created_by,
            max_uses=max_uses,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
        )
        
        await self.db.create_reset_key(reset_key)
        logger.info(f"Generated reset key: {key} by {created_by}")
        
        return reset_key
    
    async def validate_reset_key(self, key: str) -> Optional[ResetKey]:
        """
        Validate and get reset key.
        
        Args:
            key: Key string
            
        Returns:
            ResetKey if valid, None otherwise
        """
        return await self.db.get_reset_key(key)
    
    async def use_reset_key(self, key: str, user_id: int) -> bool:
        """
        Mark reset key as used.
        
        Args:
            key: Key string
            user_id: User who used the key
            
        Returns:
            True if marked successfully
        """
        return await self.db.use_reset_key(key, user_id)


class BroadcastManager:
    """Manage broadcast messages"""
    
    def __init__(self, db: FirebaseDB):
        self.db = db
        self.batch_size = 25
        self.delay = 1.5
    
    async def broadcast(
        self,
        bot,
        message: str,
        admin_id: int
    ) -> dict:
        """
        Broadcast message to all users.
        
        Args:
            bot: Bot instance
            message: Message to broadcast
            admin_id: Admin who initiated broadcast
            
        Returns:
            Dict with broadcast statistics
        """
        import asyncio
        
        users = await self.db.get_all_users(limit=10000)
        
        sent = 0
        failed = 0
        
        for i, user in enumerate(users):
            try:
                await bot.send_message(
                    chat_id=user.user_id,
                    text=f"📢 **Broadcast Message**\n\n{message}",
                    parse_mode='Markdown'
                )
                sent += 1
                
                # Rate limiting
                if (i + 1) % self.batch_size == 0:
                    await asyncio.sleep(self.delay)
                    
            except Exception as e:
                logger.error(f"Failed to send to {user.user_id}: {e}")
                failed += 1
        
        return {
            'total': len(users),
            'sent': sent,
            'failed': failed
        }

"""
Firebase Database
=================
Firebase Firestore integration with optimized caching.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import asdict

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError

from config import firebase_config
from database.models import User, BypassCache, AccessToken, ResetKey, SiteRequest, ErrorReport
from utils.logger import get_logger

logger = get_logger(__name__)


class FirebaseDB:
    """
    Firebase Firestore database manager.
    Handles all database operations with smart caching.
    """
    
    def __init__(self):
        """Initialize Firebase connection"""
        self.db: Optional[firestore.Client] = None
        self._initialized = False
        self._batch_size = 500  # Firestore batch limit
        
        # Collection references
        self.collections = {
            'users': None,
            'bypass_cache': None,
            'access_tokens': None,
            'reset_keys': None,
            'site_requests': None,
            'error_reports': None,
            'stats': None,
            'config': None,
        }
    
    async def initialize(self) -> bool:
        """
        Initialize Firebase connection.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("🔥 Initializing Firebase...")
            
            # Check if already initialized
            if firebase_admin._apps:
                logger.info("Firebase already initialized")
                self.db = firestore.client()
            else:
                # Initialize with credentials
                if firebase_config.FIREBASE_CREDENTIALS_PATH:
                    cred = credentials.Certificate(firebase_config.FIREBASE_CREDENTIALS_PATH)
                else:
                    # Use environment credentials
                    cred_dict = {
                        "type": "service_account",
                        "project_id": firebase_config.FIREBASE_PROJECT_ID,
                        "private_key": firebase_config.FIREBASE_PRIVATE_KEY,
                        "client_email": firebase_config.FIREBASE_CLIENT_EMAIL,
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                    cred = credentials.Certificate(cred_dict)
                
                firebase_admin.initialize_app(cred, {
                    'databaseURL': firebase_config.FIREBASE_DATABASE_URL
                })
                self.db = firestore.client()
            
            # Initialize collection references
            self.collections['users'] = self.db.collection('users')
            self.collections['bypass_cache'] = self.db.collection('bypass_cache')
            self.collections['access_tokens'] = self.db.collection('access_tokens')
            self.collections['reset_keys'] = self.db.collection('reset_keys')
            self.collections['site_requests'] = self.db.collection('site_requests')
            self.collections['error_reports'] = self.db.collection('error_reports')
            self.collections['stats'] = self.db.collection('stats')
            self.collections['config'] = self.db.collection('config')
            
            self._initialized = True
            logger.info("✅ Firebase initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            return False
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User object or None
        """
        try:
            doc_ref = self.collections['users'].document(str(user_id))
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return User.from_dict(data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user: User) -> bool:
        """
        Create new user.
        
        Args:
            user: User object
            
        Returns:
            bool: True if created successfully
        """
        try:
            doc_ref = self.collections['users'].document(str(user.user_id))
            doc_ref.set(user.to_dict())
            logger.info(f"✅ User {user.user_id} created")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user {user.user_id}: {e}")
            return False
    
    async def update_user(self, user: User) -> bool:
        """
        Update user data.
        
        Args:
            user: User object
            
        Returns:
            bool: True if updated successfully
        """
        try:
            doc_ref = self.collections['users'].document(str(user.user_id))
            doc_ref.update(user.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user.user_id}: {e}")
            return False
    
    async def update_user_field(self, user_id: int, field: str, value: Any) -> bool:
        """
        Update specific user field.
        
        Args:
            user_id: Telegram user ID
            field: Field name
            value: New value
            
        Returns:
            bool: True if updated successfully
        """
        try:
            doc_ref = self.collections['users'].document(str(user_id))
            doc_ref.update({field: value})
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id} field {field}: {e}")
            return False
    
    async def get_all_users(self, limit: int = 1000) -> List[User]:
        """
        Get all users.
        
        Args:
            limit: Maximum number of users
            
        Returns:
            List of User objects
        """
        try:
            docs = self.collections['users'].limit(limit).stream()
            users = []
            for doc in docs:
                data = doc.to_dict()
                users.append(User.from_dict(data))
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def get_premium_users(self) -> List[User]:
        """
        Get all premium users.
        
        Returns:
            List of premium User objects
        """
        try:
            docs = (
                self.collections['users']
                .where('is_premium', '==', True)
                .stream()
            )
            users = []
            for doc in docs:
                data = doc.to_dict()
                users.append(User.from_dict(data))
            return users
            
        except Exception as e:
            logger.error(f"Error getting premium users: {e}")
            return []
    
    async def get_total_users(self) -> int:
        """Get total user count"""
        try:
            return len(list(self.collections['users'].stream()))
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    async def get_premium_users_count(self) -> int:
        """Get premium user count"""
        try:
            return len(await self.get_premium_users())
        except Exception as e:
            logger.error(f"Error getting premium count: {e}")
            return 0
    
    # ==================== BYPASS CACHE OPERATIONS ====================
    
    async def get_bypass_cache(self, url_hash: str) -> Optional[BypassCache]:
        """
        Get cached bypass result.
        
        Args:
            url_hash: Hashed URL
            
        Returns:
            BypassCache object or None
        """
        try:
            doc_ref = self.collections['bypass_cache'].document(url_hash)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                cache = BypassCache.from_dict(data)
                
                # Check if cache is still valid (7 days)
                if cache.is_valid():
                    return cache
                else:
                    # Delete expired cache
                    await self.delete_bypass_cache(url_hash)
                    return None
            return None
            
        except Exception as e:
            logger.error(f"Error getting bypass cache: {e}")
            return None
    
    async def set_bypass_cache(self, cache: BypassCache) -> bool:
        """
        Store bypass result in cache.
        
        Args:
            cache: BypassCache object
            
        Returns:
            bool: True if stored successfully
        """
        try:
            doc_ref = self.collections['bypass_cache'].document(cache.url_hash)
            doc_ref.set(cache.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error setting bypass cache: {e}")
            return False
    
    async def delete_bypass_cache(self, url_hash: str) -> bool:
        """
        Delete bypass cache.
        
        Args:
            url_hash: Hashed URL
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            doc_ref = self.collections['bypass_cache'].document(url_hash)
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting bypass cache: {e}")
            return False
    
    async def get_total_bypasses(self) -> int:
        """Get total bypass count"""
        try:
            return len(list(self.collections['bypass_cache'].stream()))
        except Exception as e:
            logger.error(f"Error getting total bypasses: {e}")
            return 0
    
    async def get_today_bypasses(self) -> int:
        """Get today's bypass count"""
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            docs = (
                self.collections['bypass_cache']
                .where('created_date', '==', today)
                .stream()
            )
            return len(list(docs))
        except Exception as e:
            logger.error(f"Error getting today's bypasses: {e}")
            return 0
    
    # ==================== ACCESS TOKEN OPERATIONS ====================
    
    async def create_access_token(self, token: AccessToken) -> bool:
        """
        Create access token.
        
        Args:
            token: AccessToken object
            
        Returns:
            bool: True if created successfully
        """
        try:
            doc_ref = self.collections['access_tokens'].document(token.token)
            doc_ref.set(token.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            return False
    
    async def get_access_token(self, token: str) -> Optional[AccessToken]:
        """
        Get access token.
        
        Args:
            token: Token string
            
        Returns:
            AccessToken object or None
        """
        try:
            doc_ref = self.collections['access_tokens'].document(token)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                token_obj = AccessToken.from_dict(data)
                
                # Check if token is valid
                if token_obj.is_valid():
                    return token_obj
                else:
                    # Delete expired/used token
                    await self.delete_access_token(token)
                    return None
            return None
            
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    async def use_access_token(self, token: str, user_id: int) -> bool:
        """
        Mark token as used.
        
        Args:
            token: Token string
            user_id: User who used the token
            
        Returns:
            bool: True if marked successfully
        """
        try:
            doc_ref = self.collections['access_tokens'].document(token)
            doc_ref.update({
                'used': True,
                'used_by': user_id,
                'used_at': datetime.utcnow()
            })
            return True
            
        except Exception as e:
            logger.error(f"Error using access token: {e}")
            return False
    
    async def delete_access_token(self, token: str) -> bool:
        """
        Delete access token.
        
        Args:
            token: Token string
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            doc_ref = self.collections['access_tokens'].document(token)
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting access token: {e}")
            return False
    
    # ==================== RESET KEY OPERATIONS ====================
    
    async def create_reset_key(self, reset_key: ResetKey) -> bool:
        """
        Create reset key.
        
        Args:
            reset_key: ResetKey object
            
        Returns:
            bool: True if created successfully
        """
        try:
            doc_ref = self.collections['reset_keys'].document(reset_key.key)
            doc_ref.set(reset_key.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error creating reset key: {e}")
            return False
    
    async def get_reset_key(self, key: str) -> Optional[ResetKey]:
        """
        Get reset key.
        
        Args:
            key: Key string
            
        Returns:
            ResetKey object or None
        """
        try:
            doc_ref = self.collections['reset_keys'].document(key)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                key_obj = ResetKey.from_dict(data)
                
                # Check if key is valid
                if key_obj.is_valid():
                    return key_obj
                else:
                    # Delete expired/used key
                    await self.delete_reset_key(key)
                    return None
            return None
            
        except Exception as e:
            logger.error(f"Error getting reset key: {e}")
            return None
    
    async def use_reset_key(self, key: str, user_id: int) -> bool:
        """
        Mark reset key as used.
        
        Args:
            key: Key string
            user_id: User who used the key
            
        Returns:
            bool: True if marked successfully
        """
        try:
            doc_ref = self.collections['reset_keys'].document(key)
            doc_ref.update({
                'used': True,
                'used_by': user_id,
                'used_at': datetime.utcnow()
            })
            return True
            
        except Exception as e:
            logger.error(f"Error using reset key: {e}")
            return False
    
    async def delete_reset_key(self, key: str) -> bool:
        """
        Delete reset key.
        
        Args:
            key: Key string
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            doc_ref = self.collections['reset_keys'].document(key)
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting reset key: {e}")
            return False
    
    # ==================== SITE REQUEST OPERATIONS ====================
    
    async def create_site_request(self, request: SiteRequest) -> bool:
        """
        Create site request.
        
        Args:
            request: SiteRequest object
            
        Returns:
            bool: True if created successfully
        """
        try:
            doc_ref = self.collections['site_requests'].document()
            request.request_id = doc_ref.id
            doc_ref.set(request.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error creating site request: {e}")
            return False
    
    async def get_pending_site_requests(self) -> List[SiteRequest]:
        """
        Get pending site requests.
        
        Returns:
            List of pending SiteRequest objects
        """
        try:
            docs = (
                self.collections['site_requests']
                .where('status', '==', 'pending')
                .stream()
            )
            requests = []
            for doc in docs:
                data = doc.to_dict()
                requests.append(SiteRequest.from_dict(data))
            return requests
            
        except Exception as e:
            logger.error(f"Error getting site requests: {e}")
            return []
    
    # ==================== ERROR REPORT OPERATIONS ====================
    
    async def create_error_report(self, report: ErrorReport) -> bool:
        """
        Create error report.
        
        Args:
            report: ErrorReport object
            
        Returns:
            bool: True if created successfully
        """
        try:
            doc_ref = self.collections['error_reports'].document()
            report.report_id = doc_ref.id
            doc_ref.set(report.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"Error creating error report: {e}")
            return False
    
    async def get_pending_error_reports(self) -> List[ErrorReport]:
        """
        Get pending error reports.
        
        Returns:
            List of pending ErrorReport objects
        """
        try:
            docs = (
                self.collections['error_reports']
                .where('status', '==', 'pending')
                .stream()
            )
            reports = []
            for doc in docs:
                data = doc.to_dict()
                reports.append(ErrorReport.from_dict(data))
            return reports
            
        except Exception as e:
            logger.error(f"Error getting error reports: {e}")
            return []
    
    # ==================== CONFIG OPERATIONS ====================
    
    async def get_config(self, key: str) -> Optional[Any]:
        """
        Get config value.
        
        Args:
            key: Config key
            
        Returns:
            Config value or None
        """
        try:
            doc_ref = self.collections['config'].document('settings')
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get(key)
            return None
            
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return None
    
    async def set_config(self, key: str, value: Any) -> bool:
        """
        Set config value.
        
        Args:
            key: Config key
            value: Config value
            
        Returns:
            bool: True if set successfully
        """
        try:
            doc_ref = self.collections['config'].document('settings')
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({key: value})
            else:
                doc_ref.set({key: value})
            return True
            
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
            return False
    
    # ==================== STATS OPERATIONS ====================
    
    async def increment_stat(self, stat_name: str, value: int = 1) -> bool:
        """
        Increment statistic.
        
        Args:
            stat_name: Statistic name
            value: Increment value
            
        Returns:
            bool: True if incremented successfully
        """
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            doc_ref = self.collections['stats'].document(today)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({stat_name: firestore.Increment(value)})
            else:
                doc_ref.set({stat_name: value, 'date': today})
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing stat {stat_name}: {e}")
            return False

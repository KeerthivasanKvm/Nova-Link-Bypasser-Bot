"""
Database Models
===============
Data models for Firebase collections.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import hashlib
import json


@dataclass
class User:
    """User model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Status
    is_premium: bool = False
    is_admin: bool = False
    is_banned: bool = False
    
    # Premium info
    premium_start: Optional[datetime] = None
    premium_expiry: Optional[datetime] = None
    
    # Usage limits
    daily_limit: int = 5  # Default free limit
    hourly_limit: int = 2
    
    # Usage tracking
    bypass_count_today: int = 0
    bypass_count_total: int = 0
    last_bypass_time: Optional[datetime] = None
    last_reset_date: Optional[datetime] = None
    
    # Referral
    referral_code: Optional[str] = None
    referred_by: Optional[int] = None
    referral_count: int = 0
    referral_earned_days: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Groups allowed to use bot
    allowed_groups: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase"""
        data = asdict(self)
        # Convert datetime to timestamp
        for key in ['premium_start', 'premium_expiry', 'last_bypass_time', 
                    'last_reset_date', 'created_at', 'updated_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        # Convert timestamp to datetime
        for key in ['premium_start', 'premium_expiry', 'last_bypass_time',
                    'last_reset_date', 'created_at', 'updated_at']:
            if data.get(key):
                if isinstance(data[key], str):
                    data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def is_premium_active(self) -> bool:
        """Check if premium is active"""
        if not self.is_premium:
            return False
        if not self.premium_expiry:
            return False
        return datetime.utcnow() < self.premium_expiry
    
    def can_bypass(self) -> bool:
        """Check if user can bypass links"""
        if self.is_premium_active():
            return True
        
        # Check daily limit
        today = datetime.utcnow().date()
        if self.last_reset_date and self.last_reset_date.date() == today:
            return self.bypass_count_today < self.daily_limit
        else:
            # Reset for new day
            return True
    
    def get_remaining_bypasses(self) -> int:
        """Get remaining bypasses for today"""
        if self.is_premium_active():
            return float('inf')
        
        today = datetime.utcnow().date()
        if self.last_reset_date and self.last_reset_date.date() == today:
            return max(0, self.daily_limit - self.bypass_count_today)
        else:
            return self.daily_limit
    
    def increment_bypass(self) -> None:
        """Increment bypass count"""
        today = datetime.utcnow().date()
        if not self.last_reset_date or self.last_reset_date.date() != today:
            self.bypass_count_today = 0
            self.last_reset_date = datetime.utcnow()
        
        self.bypass_count_today += 1
        self.bypass_count_total += 1
        self.last_bypass_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()


@dataclass
class BypassCache:
    """Bypass result cache model"""
    url_hash: str
    original_url: str
    bypassed_url: str
    method_used: str
    success: bool
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # For filtering
    created_date: str = field(default_factory=lambda: datetime.utcnow().strftime('%Y-%m-%d'))
    domain: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'last_accessed']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BypassCache':
        """Create from dictionary"""
        for key in ['created_at', 'last_accessed']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def is_valid(self, max_age_days: int = 7) -> bool:
        """Check if cache is still valid"""
        age = datetime.utcnow() - self.created_at
        return age.days < max_age_days
    
    def access(self) -> None:
        """Record access"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    @staticmethod
    def hash_url(url: str) -> str:
        """Generate hash for URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:32]


@dataclass
class AccessToken:
    """Access token model for premium access"""
    token: str
    duration_days: float  # Can be fractional (e.g., 1/24 for 1 hour)
    created_by: int  # Admin who created it
    
    # Status
    used: bool = False
    used_by: Optional[int] = None
    used_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate expiry"""
        if not self.expires_at:
            self.expires_at = self.created_at + timedelta(days=self.duration_days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'expires_at', 'used_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessToken':
        """Create from dictionary"""
        for key in ['created_at', 'expires_at', 'used_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def is_valid(self) -> bool:
        """Check if token is valid"""
        if self.used:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def get_duration_text(self) -> str:
        """Get human-readable duration"""
        if self.duration_days >= 1:
            return f"{int(self.duration_days)} day(s)"
        elif self.duration_days >= 1/24:
            hours = int(self.duration_days * 24)
            return f"{hours} hour(s)"
        else:
            minutes = int(self.duration_days * 24 * 60)
            return f"{minutes} minute(s)"


@dataclass
class ResetKey:
    """Reset key model for free users"""
    key: str
    created_by: int  # Admin who created it
    max_uses: int = 1  # Maximum uses (default: 1 for one-time)
    
    # Usage tracking
    use_count: int = 0
    used: bool = False
    used_by: List[int] = field(default_factory=list)  # List of user IDs who used it
    used_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'expires_at', 'used_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResetKey':
        """Create from dictionary"""
        for key in ['created_at', 'expires_at', 'used_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def is_valid(self) -> bool:
        """Check if key is valid"""
        if self.use_count >= self.max_uses:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def can_use(self, user_id: int) -> bool:
        """Check if specific user can use this key"""
        if not self.is_valid():
            return False
        # Universal key - anyone can use
        return True


@dataclass
class SiteRequest:
    """Site request model"""
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    site_url: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'resolved_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRequest':
        """Create from dictionary"""
        for key in ['created_at', 'resolved_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ErrorReport:
    """Error report model"""
    report_id: Optional[str] = None
    user_id: Optional[int] = None
    url: Optional[str] = None
    error_type: Optional[str] = None  # broken_link, unsupported, other
    description: Optional[str] = None
    status: str = "pending"  # pending, resolved, ignored
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'resolved_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorReport':
        """Create from dictionary"""
        for key in ['created_at', 'resolved_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GroupPermission:
    """Group permission model"""
    group_id: int
    group_name: Optional[str] = None
    allowed: bool = False
    allowed_by: Optional[int] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        for key in ['created_at', 'updated_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupPermission':
        """Create from dictionary"""
        for key in ['created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

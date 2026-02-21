"""
Base Bypass
===========
Base class for all bypass methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class BypassStatus(Enum):
    """Bypass status enum"""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    UNSUPPORTED = "unsupported"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class BypassResult:
    """Bypass result data class"""
    success: bool
    url: Optional[str] = None
    method: Optional[str] = None
    status: BypassStatus = BypassStatus.FAILED
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    execution_time: float = 0.0
    retries: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'url': self.url,
            'method': self.method,
            'status': self.status.value,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'execution_time': self.execution_time,
            'retries': self.retries
        }
    
    @classmethod
    def success_result(
        cls,
        url: str,
        method: str,
        execution_time: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> 'BypassResult':
        """Create success result"""
        return cls(
            success=True,
            url=url,
            method=method,
            status=BypassStatus.SUCCESS,
            execution_time=execution_time,
            metadata=metadata or {}
        )
    
    @classmethod
    def failed_result(
        cls,
        error_message: str,
        method: str,
        execution_time: float = 0.0,
        status: BypassStatus = BypassStatus.FAILED
    ) -> 'BypassResult':
        """Create failed result"""
        return cls(
            success=False,
            method=method,
            status=status,
            error_message=error_message,
            execution_time=execution_time
        )


class BaseBypass(ABC):
    """
    Base class for all bypass methods.
    All bypass implementations must inherit from this class.
    """
    
    # Method name (override in subclasses)
    METHOD_NAME = "base"
    
    # Priority order (lower = tried first)
    PRIORITY = 100
    
    # Supported domains (empty = all domains)
    SUPPORTED_DOMAINS: List[str] = []
    
    # Timeout for this method
    TIMEOUT = 30
    
    def __init__(self):
        """Initialize bypass method"""
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    @abstractmethod
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt to bypass the link.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult with the result
        """
        pass
    
    def is_supported(self, url: str) -> bool:
        """
        Check if this method supports the given URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if supported
        """
        if not self.SUPPORTED_DOMAINS:
            return True
        
        domain = self._extract_domain(url)
        return any(d in domain for d in self.SUPPORTED_DOMAINS)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _extract_path(self, url: str) -> str:
        """Extract path from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        if not url:
            return False
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    
    def _follow_redirects(self, url: str, max_redirects: int = 10) -> str:
        """
        Follow redirects to get final URL.
        
        Args:
            url: Starting URL
            max_redirects: Maximum redirects to follow
            
        Returns:
            Final URL
        """
        import requests
        
        try:
            response = requests.head(
                url,
                headers=self.headers,
                allow_redirects=True,
                timeout=self.TIMEOUT,
                max_redirects=max_redirects
            )
            return response.url
        except Exception:
            return url
    
    def _decode_base64(self, text: str) -> Optional[str]:
        """
        Try to decode base64.
        
        Args:
            text: Text to decode
            
        Returns:
            Decoded text or None
        """
        import base64
        try:
            decoded = base64.b64decode(text).decode('utf-8')
            return decoded
        except Exception:
            return None
    
    def _decode_url(self, text: str) -> Optional[str]:
        """
        URL decode text.
        
        Args:
            text: Text to decode
            
        Returns:
            Decoded text
        """
        from urllib.parse import unquote
        try:
            return unquote(text)
        except Exception:
            return None
    
    def _extract_links(self, text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of URLs
        """
        import re
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
        return re.findall(url_pattern, text)


class BypassRegistry:
    """Registry for bypass methods"""
    
    _methods: Dict[str, type] = {}
    
    @classmethod
    def register(cls, method_class: type) -> type:
        """Register a bypass method"""
        cls._methods[method_class.METHOD_NAME] = method_class
        return method_class
    
    @classmethod
    def get_method(cls, name: str) -> Optional[type]:
        """Get bypass method by name"""
        return cls._methods.get(name)
    
    @classmethod
    def get_all_methods(cls) -> List[type]:
        """Get all registered methods sorted by priority"""
        return sorted(cls._methods.values(), key=lambda m: m.PRIORITY)
    
    @classmethod
    def get_method_names(cls) -> List[str]:
        """Get all method names"""
        return list(cls._methods.keys())


def register_bypass(method_class: type) -> type:
    """Decorator to register bypass method"""
    return BypassRegistry.register(method_class)

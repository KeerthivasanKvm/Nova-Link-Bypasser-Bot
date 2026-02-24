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

    METHOD_NAME = "base"
    PRIORITY = 100
    SUPPORTED_DOMAINS: List[str] = []
    TIMEOUT = 30

    def __init__(self):
        self.session = None

        # Realistic Chrome 124 headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Cache-Control': 'max-age=0',
            'Priority': 'u=0, i',
        }

        # User agent pool for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        ]

    def _get_session(self, use_proxy: bool = True):
        """
        Create a requests session with anti-detection settings + proxy.
        
        Args:
            use_proxy: Whether to attach a proxy (default True)
        """
        import requests
        import random
        from bypass.proxy_manager import proxy_manager

        session = requests.Session()

        # Rotate user agent
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        session.headers.update(headers)

        # Attach proxy
        if use_proxy:
            proxy = proxy_manager.get_proxy()
            if proxy:
                session.proxies.update(proxy)

        return session

    def _get_cloudscraper(self, use_proxy: bool = True):
        """
        Get a cloudscraper instance with proxy.
        Use this instead of cloudscraper.create_scraper() in subclasses.
        
        Args:
            use_proxy: Whether to attach a proxy (default True)
        """
        import cloudscraper
        from bypass.proxy_manager import proxy_manager

        client = cloudscraper.create_scraper(allow_brotli=False)
        if use_proxy:
            proxy = proxy_manager.get_proxy()
            if proxy:
                client.proxies.update(proxy)
        return client

    @abstractmethod
    async def bypass(self, url: str) -> BypassResult:
        pass

    def is_supported(self, url: str) -> bool:
        if not self.SUPPORTED_DOMAINS:
            return True
        domain = self._extract_domain(url)
        return any(d in domain for d in self.SUPPORTED_DOMAINS)

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()

    def _extract_path(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).path

    def _is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)

    def _follow_redirects(self, url: str, max_redirects: int = 10) -> str:
        """Follow redirects using a proxy-enabled session."""
        try:
            session = self._get_session(use_proxy=True)
            response = session.get(
                url,
                allow_redirects=True,
                timeout=self.TIMEOUT,
                max_redirects=max_redirects
            )
            return response.url
        except Exception:
            return url

    def _decode_base64(self, text: str) -> Optional[str]:
        import base64
        try:
            return base64.b64decode(text).decode('utf-8')
        except Exception:
            return None

    def _decode_url(self, text: str) -> Optional[str]:
        from urllib.parse import unquote
        try:
            return unquote(text)
        except Exception:
            return None

    def _extract_links(self, text: str) -> List[str]:
        import re
        url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
        return re.findall(url_pattern, text)


class BypassRegistry:
    """Registry for bypass methods"""

    _methods: Dict[str, type] = {}

    @classmethod
    def register(cls, method_class: type) -> type:
        cls._methods[method_class.METHOD_NAME] = method_class
        return method_class

    @classmethod
    def get_method(cls, name: str) -> Optional[type]:
        return cls._methods.get(name)

    @classmethod
    def get_all_methods(cls) -> List[type]:
        return sorted(cls._methods.values(), key=lambda m: m.PRIORITY)

    @classmethod
    def get_method_names(cls) -> List[str]:
        return list(cls._methods.keys())


def register_bypass(method_class: type) -> type:
    """Decorator to register bypass method"""
    return BypassRegistry.register(method_class)

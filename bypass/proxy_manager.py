"""
Proxy Manager
=============
Handles proxy rotation for all bypass requests.
Prevents adlink websites from blocking the bot's server IP.

Setup (Render Environment Variables):
    PROXY_LIST = "http://user:pass@host1:port,http://user:pass@host2:port"
    
    Or use a proxy service:
    WEBSHARE_API_KEY = "your_key"        (webshare.io - cheap rotating proxies)
    PROXYSCRAPE_API  = "your_key"        (proxyscrape.com)

Free proxy sources (less reliable, use paid for production):
    Set PROXY_LIST with free proxies from https://proxyscrape.com/free-proxy-list
"""

import os
import random
import time
import requests
from typing import Optional, List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class ProxyManager:
    """
    Rotating proxy manager.
    Automatically removes dead proxies and rotates on failure.
    """

    def __init__(self):
        self.proxies: List[str]      = []
        self.dead_proxies: set       = set()
        self.proxy_fail_count: Dict  = {}
        self.last_refresh: float     = 0
        self.refresh_interval: int   = 3600  # re-fetch proxies every 1 hour
        self._load_proxies()

    # ─────────────────────────────────────────────
    # LOADING
    # ─────────────────────────────────────────────

    def _load_proxies(self):
        """Load proxies from env vars or proxy services."""
        loaded = []

        # 1. Manual proxy list from env (highest priority)
        proxy_list_env = os.environ.get("PROXY_LIST", "")
        if proxy_list_env:
            for p in proxy_list_env.split(","):
                p = p.strip()
                if p:
                    loaded.append(p)
            logger.info(f"[Proxy] Loaded {len(loaded)} proxies from PROXY_LIST env")

        # 2. Webshare.io rotating proxy API
        webshare_key = os.environ.get("WEBSHARE_API_KEY", "")
        if webshare_key and not loaded:
            loaded.extend(self._fetch_webshare(webshare_key))

        # 3. ProxyScrape API
        proxyscrape_key = os.environ.get("PROXYSCRAPE_API", "")
        if proxyscrape_key and not loaded:
            loaded.extend(self._fetch_proxyscrape(proxyscrape_key))

        # 4. Free public proxies (fallback — less reliable)
        if not loaded:
            logger.warning("[Proxy] No proxy config found — fetching free public proxies (less reliable)")
            loaded.extend(self._fetch_free_proxies())

        self.proxies = loaded
        self.dead_proxies.clear()
        self.proxy_fail_count.clear()
        self.last_refresh = time.time()
        logger.info(f"[Proxy] Total proxies available: {len(self.proxies)}")

    def _fetch_webshare(self, api_key: str) -> List[str]:
        """Fetch proxies from webshare.io"""
        try:
            resp = requests.get(
                "https://proxy.webshare.io/api/v2/proxy/list/",
                headers={"Authorization": f"Token {api_key}"},
                params={"mode": "direct", "page": 1, "page_size": 100},
                timeout=10
            )
            data = resp.json()
            proxies = []
            for p in data.get("results", []):
                proxy = f"http://{p['username']}:{p['password']}@{p['proxy_address']}:{p['port']}"
                proxies.append(proxy)
            logger.info(f"[Proxy] Fetched {len(proxies)} proxies from Webshare")
            return proxies
        except Exception as e:
            logger.error(f"[Proxy] Webshare fetch failed: {e}")
            return []

    def _fetch_proxyscrape(self, api_key: str) -> List[str]:
        """Fetch proxies from proxyscrape.com"""
        try:
            resp = requests.get(
                f"https://api.proxyscrape.com/v3/free-proxy-list/get",
                params={
                    "request": "displayproxies",
                    "protocol": "http",
                    "timeout": 5000,
                    "country": "all",
                    "ssl": "all",
                    "anonymity": "elite",
                    "apikey": api_key
                },
                timeout=10
            )
            proxies = [f"http://{line.strip()}" for line in resp.text.splitlines() if line.strip()]
            logger.info(f"[Proxy] Fetched {len(proxies)} proxies from ProxyScrape")
            return proxies
        except Exception as e:
            logger.error(f"[Proxy] ProxyScrape fetch failed: {e}")
            return []

    def _fetch_free_proxies(self) -> List[str]:
        """Fetch free proxies as last resort."""
        try:
            resp = requests.get(
                "https://api.proxyscrape.com/v2/",
                params={
                    "request": "getproxies",
                    "protocol": "http",
                    "timeout": 5000,
                    "country": "all",
                    "ssl": "all",
                    "anonymity": "elite"
                },
                timeout=10
            )
            proxies = [f"http://{line.strip()}" for line in resp.text.splitlines() if line.strip()]
            logger.info(f"[Proxy] Fetched {len(proxies)} free proxies")
            return proxies
        except Exception as e:
            logger.error(f"[Proxy] Free proxy fetch failed: {e}")
            return []

    # ─────────────────────────────────────────────
    # PROXY SELECTION
    # ─────────────────────────────────────────────

    def get_proxy(self) -> Optional[Dict]:
        """
        Get a random working proxy as a dict for requests.
        Returns None if no proxies available (direct connection).
        
        Usage:
            proxies = proxy_manager.get_proxy()
            requests.get(url, proxies=proxies)
        """
        # Auto-refresh every hour
        if time.time() - self.last_refresh > self.refresh_interval:
            logger.info("[Proxy] Refreshing proxy list...")
            self._load_proxies()

        # Get alive proxies
        alive = [p for p in self.proxies if p not in self.dead_proxies]

        if not alive:
            logger.warning("[Proxy] No alive proxies — using direct connection")
            # Try refreshing once
            if self.dead_proxies:
                self._load_proxies()
                alive = [p for p in self.proxies if p not in self.dead_proxies]
            if not alive:
                return None

        proxy = random.choice(alive)
        return {"http": proxy, "https": proxy}

    def get_proxy_url(self) -> Optional[str]:
        """Get just the proxy URL string."""
        proxy_dict = self.get_proxy()
        return proxy_dict["http"] if proxy_dict else None

    def mark_dead(self, proxy_url: str):
        """Mark a proxy as dead after failure."""
        # Track fail count — remove after 3 failures
        self.proxy_fail_count[proxy_url] = self.proxy_fail_count.get(proxy_url, 0) + 1
        if self.proxy_fail_count[proxy_url] >= 3:
            self.dead_proxies.add(proxy_url)
            logger.debug(f"[Proxy] Marked dead: {proxy_url[:30]}...")

    def mark_working(self, proxy_url: str):
        """Mark proxy as working — reset its fail count."""
        self.proxy_fail_count.pop(proxy_url, None)
        self.dead_proxies.discard(proxy_url)

    def get_cloudscraper(self, **kwargs):
        """
        Get a cloudscraper instance with proxy attached.
        Use this instead of cloudscraper.create_scraper() everywhere.
        """
        import cloudscraper
        client = cloudscraper.create_scraper(allow_brotli=False, **kwargs)
        proxy = self.get_proxy()
        if proxy:
            client.proxies.update(proxy)
        return client

    def get_requests_session(self, headers: dict = None) -> requests.Session:
        """
        Get a requests.Session with proxy and headers attached.
        Use this instead of requests.Session() everywhere.
        """
        session = requests.Session()
        proxy = self.get_proxy()
        if proxy:
            session.proxies.update(proxy)
        if headers:
            session.headers.update(headers)
        return session

    @property
    def status(self) -> str:
        """Get proxy status summary."""
        total = len(self.proxies)
        dead  = len(self.dead_proxies)
        alive = total - dead
        return f"Proxies: {alive} alive / {dead} dead / {total} total"


# ─────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────
# Import this in any file that needs proxies:
#   from bypass.proxy_manager import proxy_manager
#   proxies = proxy_manager.get_proxy()

proxy_manager = ProxyManager()

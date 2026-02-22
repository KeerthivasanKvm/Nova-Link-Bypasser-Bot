"""
GPLinks Dedicated Bypass
========================
Specific bypass for gplinks.co, gplinks.in and similar sites.
Uses the known token-based API technique.
"""

import re
import time
import requests
from typing import Optional
from urllib.parse import urlparse, urlencode
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class GPLinksbypass(BaseBypass):
    """
    Dedicated bypass for GPLinks shortener.
    Supports: gplinks.co, gplinks.in, gplinks.online
    Uses token extraction + API call technique.
    """

    METHOD_NAME = "gplinks"
    PRIORITY = 1  # Try this FIRST for gplinks domains
    TIMEOUT = 30
    SUPPORTED_DOMAINS = ['gplinks.co', 'gplinks.in', 'gplinks.online', 'gplinks.net']

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })

    async def bypass(self, url: str) -> BypassResult:
        start_time = time.time()

        try:
            logger.info(f"[GPLinks] Attempting bypass for: {url}")

            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            # Step 1: GET the page to collect cookies + extract token
            response = self.session.get(url, timeout=self.TIMEOUT, allow_redirects=True)

            if response.status_code == 403:
                # Try with Referer trick
                self.session.headers.update({'Referer': 'https://www.google.com/'})
                response = self.session.get(url, timeout=self.TIMEOUT, allow_redirects=True)

            if response.status_code != 200:
                execution_time = time.time() - start_time
                return BypassResult.failed_result(
                    error_message=f"HTTP {response.status_code}",
                    method=self.METHOD_NAME,
                    execution_time=execution_time
                )

            html = response.text
            final_url = response.url

            # Step 2: Try to extract token from page
            token = self._extract_token(html)

            if token:
                # Step 3: Call the API with the token
                result = self._call_api(domain, token, final_url)
                if result:
                    execution_time = time.time() - start_time
                    logger.info(f"[GPLinks] API bypass success: {result}")
                    return BypassResult.success_result(
                        url=result,
                        method=self.METHOD_NAME,
                        execution_time=execution_time,
                        metadata={'technique': 'api_token'}
                    )

            # Step 4: Fallback - extract link directly from HTML
            result = self._extract_from_html(html, final_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[GPLinks] HTML extraction success: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'html_extraction'}
                )

            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="GPLinks bypass failed - no token or link found",
                method=self.METHOD_NAME,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[GPLinks] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )

    def _extract_token(self, html: str) -> Optional[str]:
        """Extract the bypass token from page HTML"""
        # Common token patterns used by GPLinks
        patterns = [
            r'var\s+_0x\w+\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
            r'token["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]+)["\']',
            r'name=["\']token["\']\s+value=["\']([^"\']+)["\']',
            r'input[^>]*name=["\']_token["\']\s*value=["\']([^"\']+)["\']',
            r'"_token"\s*:\s*"([^"]+)"',
            r"'_token'\s*:\s*'([^']+)'",
            r'var\s+token\s*=\s*["\']([^"\']+)["\']',
            r'data-token=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                token = match.group(1)
                if len(token) > 8:  # Real tokens are usually longer
                    logger.debug(f"[GPLinks] Found token: {token[:20]}...")
                    return token

        # Try BeautifulSoup for hidden inputs
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for inp in soup.find_all('input', {'type': 'hidden'}):
                name = inp.get('name', '')
                value = inp.get('value', '')
                if ('token' in name.lower() or name == '_token') and value:
                    return value
        except Exception:
            pass

        return None

    def _call_api(self, domain: str, token: str, referer: str) -> Optional[str]:
        """Call GPLinks API with the extracted token"""
        api_endpoints = [
            f"{domain}/links/go",
            f"{domain}/go",
            f"{domain}/api/links/go",
            f"{domain}/link/go",
        ]

        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': referer,
            'Origin': domain,
        }

        for endpoint in api_endpoints:
            try:
                data = {'token': token, '_token': token}
                response = self.session.post(
                    endpoint,
                    data=data,
                    headers=headers,
                    timeout=self.TIMEOUT
                )

                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        # Check common response keys
                        for key in ['url', 'link', 'redirect', 'data', 'target']:
                            if key in json_data:
                                val = json_data[key]
                                if isinstance(val, str) and val.startswith('http'):
                                    return val
                                if isinstance(val, dict):
                                    for k in ['url', 'link']:
                                        if k in val and val[k].startswith('http'):
                                            return val[k]
                    except Exception:
                        # Not JSON, check if it's a URL
                        text = response.text.strip()
                        if text.startswith('http'):
                            return text

            except Exception as e:
                logger.debug(f"[GPLinks] API endpoint {endpoint} failed: {e}")
                continue

        return None

    def _extract_from_html(self, html: str, base_url: str) -> Optional[str]:
        """Last resort - extract any external link from the page"""
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, 'html.parser')
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        # Look for known destination link patterns
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if not href or href.startswith('#'):
                continue
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            # Must be external (different domain) and valid http
            if parsed.netloc and parsed.netloc != base_domain and parsed.scheme in ('http', 'https'):
                return full

        # Look for meta refresh
        meta = soup.find('meta', attrs={'http-equiv': re.compile('refresh', re.I)})
        if meta:
            content = meta.get('content', '')
            match = re.search(r'url=([^\s;]+)', content, re.I)
            if match:
                return match.group(1).strip('"\'')

        return None


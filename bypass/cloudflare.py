"""
Cloudflare Bypass
=================
Bypass for Cloudflare-protected sites.
"""

import re
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
import cloudscraper
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class CloudflareBypass(BaseBypass):
    """
    Cloudflare bypass method.
    Uses multiple techniques:
    - cloudscraper library
    - curl_cffi (impersonates real browsers)
    - Custom TLS fingerprinting
    """
    
    METHOD_NAME = "cloudflare"
    PRIORITY = 4
    TIMEOUT = 45
    
    def __init__(self):
        super().__init__()
        # Initialize cloudscraper
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt Cloudflare bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        try:
            logger.info(f"[Cloudflare] Attempting bypass for: {url}")
            
            result = None
            
            # Method 1: Try cloudscraper
            result = self._try_cloudscraper(url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Cloudflare] Cloudscraper success: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'cloudscraper'}
                )
            
            # Method 2: Try curl_cffi
            result = await self._try_curl_cffi(url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Cloudflare] curl_cffi success: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'curl_cffi'}
                )
            
            # Method 3: Try with session cookies
            result = self._try_with_session(url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Cloudflare] Session success: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'session_cookies'}
                )
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="Cloudflare bypass failed",
                method=self.METHOD_NAME,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[Cloudflare] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    def _try_cloudscraper(self, url: str) -> Optional[str]:
        """
        Try bypass using cloudscraper.
        
        Args:
            url: URL to bypass
            
        Returns:
            Result URL or None
        """
        try:
            response = self.scraper.get(url, timeout=self.TIMEOUT)
            
            if response.status_code == 200:
                # Check if we got the actual page
                if not self._is_cloudflare_challenge(response.text):
                    # Try to extract link from page
                    result = self._extract_link(response.text, response.url)
                    if result:
                        return result
                    # If no link found, return the final URL
                    return response.url
                    
        except Exception as e:
            logger.debug(f"Cloudscraper failed: {e}")
        
        return None
    
    async def _try_curl_cffi(self, url: str) -> Optional[str]:
        """
        Try bypass using curl_cffi (browser impersonation).
        
        Args:
            url: URL to bypass
            
        Returns:
            Result URL or None
        """
        try:
            # Use curl_cffi to impersonate Chrome
            response = curl_requests.get(
                url,
                impersonate="chrome120",
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                if not self._is_cloudflare_challenge(response.text):
                    result = self._extract_link(response.text, response.url)
                    if result:
                        return result
                    return response.url
                    
        except Exception as e:
            logger.debug(f"curl_cffi failed: {e}")
        
        return None
    
    def _try_with_session(self, url: str) -> Optional[str]:
        """Try bypass using session with referer spoofing and cookie pre-loading."""
        try:
            import requests
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            session = requests.Session()
            
            # Step 1: Visit the homepage first to get cookies (mimics real browser)
            try:
                session.get(domain, headers=self.headers, timeout=10)
            except Exception:
                pass
            
            # Step 2: Set Referer to look like we came from Google
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.google.com/'
            headers['Origin'] = domain
            
            # Step 3: Request with cookies + referer
            response = session.get(url, headers=headers, timeout=self.TIMEOUT)
            
            if response.status_code == 200 and not self._is_cloudflare_challenge(response.text):
                result = self._extract_link(response.text, response.url)
                if result:
                    return result
                # Return final URL after redirects if it changed
                if response.url != url:
                    return response.url
                    
        except Exception as e:
            logger.debug(f"Session bypass failed: {e}")
        
        return None
    
    def _is_cloudflare_challenge(self, html: str) -> bool:
        """
        Check if page is a Cloudflare challenge.
        
        Args:
            html: HTML content
            
        Returns:
            True if challenge page
        """
        challenge_indicators = [
            'cf-browser-verification',
            'cf-im-under-attack',
            'cf-challenge',
            'challenge-platform',
            'turnstile',
            'cf_chl_jschl_tk',
            'cf_chl_captcha_tk',
            'Please wait',
            'Checking your browser',
            'DDoS protection',
            'Ray ID',
            '__cf_chl_jschl_tk__',
            'cf_chl_prog',
            'cf-spinner-please-wait',
            'cf-captcha-bookmark',
        ]
        
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in challenge_indicators)
    
    def _extract_link(self, html: str, base_url: str) -> Optional[str]:
        """
        Extract link from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL
            
        Returns:
            Extracted URL or None
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for download links
        selectors = [
            'a[href*="download"]',
            'a.download',
            'a.btn-download',
            'a#download',
            'a[href^="magnet:"]',
            'a[href*="drive.google.com"]',
            'a[href*="mega.nz"]',
            'a[href*="mediafire.com"]',
            'a[href*=".mp4"]',
            'a[href*=".mkv"]',
            'a[href*=".zip"]',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self._is_valid_url(full_url):
                        return full_url
        
        # Look for any external link
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('http') and self._extract_domain(href) != self._extract_domain(base_url):
                return href
        
        return None

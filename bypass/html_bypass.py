"""
HTML Bypass
===========
Bypass for pure HTML-based link shorteners.
Handles forms, meta tags, and simple redirects.
"""

import re
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class HTMLBypass(BaseBypass):
    """
    HTML-based bypass method.
    Handles:
    - Meta refresh redirects
    - Form submissions
    - Simple link pages
    - Base64 encoded links
    """
    
    METHOD_NAME = "html_forms"
    PRIORITY = 1
    TIMEOUT = 15
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt HTML-based bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        try:
            logger.info(f"[HTML] Attempting bypass for: {url}")
            
            # Fetch the page
            response = self.session.get(url, timeout=self.TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            # Get final URL after redirects
            final_url = response.url
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different methods
            result = None
            
            # Method 1: Meta refresh
            result = self._check_meta_refresh(soup, final_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[HTML] Meta refresh found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'meta_refresh'}
                )
            
            # Method 2: Form submission
            result = await self._handle_form(soup, final_url, response)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[HTML] Form bypass successful: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'form_submission'}
                )
            
            # Method 3: Direct link in page
            result = self._find_direct_link(soup, final_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[HTML] Direct link found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'direct_link'}
                )
            
            # Method 4: Base64 encoded link
            result = self._find_base64_link(response.text)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[HTML] Base64 link found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'base64_decode'}
                )
            
            # Method 5: JavaScript redirect in HTML
            result = self._check_js_redirect(response.text, final_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[HTML] JS redirect found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'js_redirect'}
                )
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="No bypass method worked",
                method=self.METHOD_NAME,
                execution_time=execution_time
            )
            
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="Request timeout",
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.TIMEOUT
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[HTML] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    def _check_meta_refresh(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Check for meta refresh redirect.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Target URL or None
        """
        # Find meta refresh tag
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh:
            content = meta_refresh.get('content', '')
            # Extract URL from content (e.g., "5;url=https://example.com")
            match = re.search(r'url\s*=\s*["\']?([^"\';]+)', content, re.IGNORECASE)
            if match:
                url = match.group(1).strip()
                return urljoin(base_url, url)
        
        # Also check for meta with URL
        meta_url = soup.find('meta', attrs={'property': 'og:url'})
        if meta_url:
            return meta_url.get('content')
        
        return None
    
    async def _handle_form(
        self,
        soup: BeautifulSoup,
        base_url: str,
        response: requests.Response
    ) -> Optional[str]:
        """
        Handle form submission.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL
            response: Original response
            
        Returns:
            Result URL or None
        """
        # Find forms
        forms = soup.find_all('form')
        
        for form in forms:
            # Get form action
            action = form.get('action', '')
            if not action:
                action = base_url
            else:
                action = urljoin(base_url, action)
            
            # Get form method
            method = form.get('method', 'get').lower()
            
            # Get form inputs
            inputs = {}
            for input_tag in form.find_all(['input', 'textarea', 'select']):
                name = input_tag.get('name')
                if name:
                    value = input_tag.get('value', '')
                    inputs[name] = value
            
            # Submit form
            try:
                if method == 'post':
                    form_response = self.session.post(
                        action,
                        data=inputs,
                        timeout=self.TIMEOUT,
                        allow_redirects=True
                    )
                else:
                    form_response = self.session.get(
                        action,
                        params=inputs,
                        timeout=self.TIMEOUT,
                        allow_redirects=True
                    )
                
                # Check if we got a redirect
                if form_response.url != action and form_response.url != base_url:
                    return form_response.url
                
                # Parse response for links
                form_soup = BeautifulSoup(form_response.text, 'html.parser')
                result = self._find_direct_link(form_soup, form_response.url)
                if result:
                    return result
                    
            except Exception as e:
                logger.debug(f"Form submission failed: {e}")
                continue
        
        return None
    
    def _find_direct_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find direct download/link in page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL
            
        Returns:
            Link URL or None
        """
        # Look for common link patterns
        selectors = [
            'a[href*="download"]',
            'a[href*="direct"]',
            'a.btn-download',
            'a.download-button',
            'a#download',
            '.download-link a',
            'a[href^="magnet:"]',
            'a[href*=".mp4"]',
            'a[href*=".mkv"]',
            'a[href*=".zip"]',
            'a[href*=".rar"]',
            'a[href*=".pdf"]',
            'a[href*="drive.google.com"]',
            'a[href*="mega.nz"]',
            'a[href*="mediafire.com"]',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self._is_valid_url(full_url):
                        return full_url
        
        # Look for any link that might be the destination
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Skip common non-target links
            if any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'tel:']):
                continue
            
            full_url = urljoin(base_url, href)
            if self._is_valid_url(full_url):
                # Check if it's an external link (likely the destination)
                if self._extract_domain(full_url) != self._extract_domain(base_url):
                    return full_url
        
        return None
    
    def _find_base64_link(self, text: str) -> Optional[str]:
        """
        Find and decode base64 encoded links.
        
        Args:
            text: Text to search
            
        Returns:
            Decoded URL or None
        """
        # Look for base64 patterns
        patterns = [
            r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)',
            r'base64["\']?\s*[:=]\s*["\']?([A-Za-z0-9+/=]+)',
            r'["\']([A-Za-z0-9+/=]{20,})["\']',
            r'var\s+\w+\s*=\s*["\']([A-Za-z0-9+/=]+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                decoded = self._decode_base64(match)
                if decoded and self._is_valid_url(decoded):
                    return decoded
        
        return None
    
    def _check_js_redirect(self, text: str, base_url: str) -> Optional[str]:
        """
        Check for JavaScript redirects in HTML.
        
        Args:
            text: HTML text
            base_url: Base URL
            
        Returns:
            Target URL or None
        """
        patterns = [
            r'window\.location\s*=\s*["\']([^"\']+)["\']',
            r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
            r'location\.replace\(["\']([^"\']+)["\']\)',
            r'location\.assign\(["\']([^"\']+)["\']\)',
            r'top\.location\s*=\s*["\']([^"\']+)["\']',
            r'window\.open\(["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                url = match.group(1)
                full_url = urljoin(base_url, url)
                if self._is_valid_url(full_url):
                    return full_url
        
        return None

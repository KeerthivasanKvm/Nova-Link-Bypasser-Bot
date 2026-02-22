"""
Toonworld4all Dedicated Bypass
==============================
Specific bypass for toonworld4all.me and related domains.
Technique: Scrape page → find redirect/main.php links → follow
redirect headers (no auto-redirect) → extract final destination URL.
"""

import re
import time
import requests
from typing import Optional, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class ToonWorld4AllBypass(BaseBypass):
    """
    Dedicated bypass for Toonworld4all site.
    Supports: toonworld4all.me, toonworld4all.*, and similar anime/cartoon sites
    that use the redirect/main.php pattern.

    How it works:
    1. Fetch the episode/movie page
    2. Find all links matching 'redirect/main.php?'
    3. Follow each redirect manually (stream=True, allow_redirects=False)
       to read the Location header — this is the real destination URL
    4. Return all found destination links
    """

    METHOD_NAME = "toonworld4all"
    PRIORITY = 1  # Try first for toonworld4all domains
    TIMEOUT = 30
    SUPPORTED_DOMAINS = [
        'toonworld4all.me',
        'link.toonworld4all.me
        'archive.toonworld4all.me',   # ← archive subdomain for redirect links
        'toonworld4all.com',
        'toonworld4all.net',
        'toonworld4all.org',
        'toonworld4all.in',
    ]
    
    # The archive subdomain that hosts redirect links
    ARCHIVE_DOMAIN = 'archive.toonworld4all.me'

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/avif,image/webp,*/*;q=0.8',
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
            logger.info(f"[ToonWorld4All] Attempting bypass for: {url}")

            # Step 1: Fetch the page
            response = self.session.get(url, timeout=self.TIMEOUT)

            if response.status_code != 200:
                # Try with Referer if blocked
                self.session.headers.update({'Referer': 'https://www.google.com/'})
                response = self.session.get(url, timeout=self.TIMEOUT)

            if response.status_code != 200:
                execution_time = time.time() - start_time
                return BypassResult.failed_result(
                    error_message=f"Page fetch failed: HTTP {response.status_code}",
                    method=self.METHOD_NAME,
                    execution_time=execution_time
                )

            html = response.text
            page_url = response.url

            # Step 2: Find all redirect links
            redirect_links = self._find_redirect_links(html, page_url)

            if not redirect_links:
                # Fallback: try to find any external links directly
                result = self._extract_direct_links(html, page_url)
                if result:
                    execution_time = time.time() - start_time
                    logger.info(f"[ToonWorld4All] Direct link found: {result}")
                    return BypassResult.success_result(
                        url=result,
                        method=self.METHOD_NAME,
                        execution_time=execution_time,
                        metadata={'technique': 'direct_extraction'}
                    )

                execution_time = time.time() - start_time
                return BypassResult.failed_result(
                    error_message="No redirect links found on page",
                    method=self.METHOD_NAME,
                    execution_time=execution_time
                )

            logger.info(f"[ToonWorld4All] Found {len(redirect_links)} redirect links")

            # Step 3: Follow each redirect to get Location header
            results = []
            for redirect_url in redirect_links:
                destination = self._follow_redirect_header(redirect_url, page_url)
                if destination:
                    logger.info(f"[ToonWorld4All] Resolved: {destination}")
                    results.append(destination)

            if not results:
                execution_time = time.time() - start_time
                return BypassResult.failed_result(
                    error_message="Redirect headers returned no destinations",
                    method=self.METHOD_NAME,
                    execution_time=execution_time
                )

            execution_time = time.time() - start_time

            # Return first result, include all in metadata
            primary = results[0]
            logger.info(f"[ToonWorld4All] Success! Found {len(results)} link(s)")

            return BypassResult.success_result(
                url=primary,
                method=self.METHOD_NAME,
                execution_time=execution_time,
                metadata={
                    'technique': 'redirect_header',
                    'all_links': results,
                    'total_found': len(results)
                }
            )

        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="Request timed out",
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.TIMEOUT
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[ToonWorld4All] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )

    def _find_redirect_links(self, html: str, base_url: str) -> List[str]:
        """
        Find all redirect links on the page.
        Toonworld4all uses archive.toonworld4all.me as the redirect domain.

        Args:
            html: Page HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of full redirect URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        # Primary pattern: links pointing to archive subdomain
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if not href:
                continue
            full_url = urljoin(base_url, href)
            # Match archive.toonworld4all.me links
            if self.ARCHIVE_DOMAIN in full_url and full_url not in links:
                links.append(full_url)
                logger.debug(f"[ToonWorld4All] Found archive link: {full_url}")

        # Secondary pattern: redirect/main.php pattern (any domain)
        if not links:
            for a in soup.select('a[href*="redirect/main.php"]'):
                href = a.get('href', '')
                if href:
                    full_url = urljoin(base_url, href)
                    if full_url not in links:
                        links.append(full_url)

        # Tertiary: other redirect patterns on same or archive domain
        if not links:
            redirect_patterns = [
                'a[href*="redirect"]',
                'a[href*="go.php"]',
                'a[href*="out.php"]',
                'a[href*="link.php"]',
                'a[href*="download.php"]',
            ]
            for pattern in redirect_patterns:
                for a in soup.select(pattern):
                    href = a.get('href', '')
                    if href:
                        full_url = urljoin(base_url, href)
                        parsed = urlparse(full_url)
                        # Accept archive subdomain OR same domain redirects
                        if (self.ARCHIVE_DOMAIN in full_url or
                                'toonworld4all' in parsed.netloc) and full_url not in links:
                            links.append(full_url)

        logger.info(f"[ToonWorld4All] Total redirect links found: {len(links)}")
        return links

    def _follow_redirect_header(self, redirect_url: str, referer: str) -> Optional[str]:
        """
        Follow a redirect URL without auto-redirecting to get the Location header.
        For archive.toonworld4all.me links, we set the Referer to the main site
        so the server accepts the request.

        Args:
            redirect_url: The archive/redirect URL to follow
            referer: Original page URL (used as Referer)

        Returns:
            Destination URL from Location header, or None
        """
        try:
            headers = dict(self.session.headers)
            
            # If it's an archive link, set Referer to the main site
            parsed = urlparse(redirect_url)
            if self.ARCHIVE_DOMAIN in redirect_url:
                main_site = f"{parsed.scheme}://toonworld4all.me"
                headers['Referer'] = referer or main_site
                headers['Origin'] = main_site
            else:
                headers['Referer'] = referer

            # stream=True + allow_redirects=False = read Location header directly
            response = self.session.get(
                redirect_url,
                headers=headers,
                stream=True,
                allow_redirects=False,
                timeout=self.TIMEOUT
            )

            # Check Location header (301/302/307/308 redirect)
            location = (response.headers.get('Location') or
                        response.headers.get('location'))

            if location:
                # Make sure it's a full URL
                if not location.startswith('http'):
                    location = urljoin(redirect_url, location)
                logger.debug(f"[ToonWorld4All] Location header: {location}")
                return location

            # If no redirect, check if it's a direct download response
            content_type = response.headers.get('Content-Type', '')
            if any(ct in content_type for ct in [
                'video/', 'application/octet-stream', 'application/zip',
                'application/x-zip', 'application/rar'
            ]):
                return redirect_url

        except Exception as e:
            logger.debug(f"[ToonWorld4All] Redirect follow failed for {redirect_url}: {e}")

        return None

    def _extract_direct_links(self, html: str, base_url: str) -> Optional[str]:
        """
        Fallback: extract any known external download links directly from HTML.

        Args:
            html: Page HTML
            base_url: Base URL

        Returns:
            First found download URL or None
        """
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(base_url).netloc

        # Known download/hosting domains to look for
        target_domains = [
            'drive.google.com',
            'mega.nz',
            'mediafire.com',
            'gdtot',
            'appdrive',
            'gdflix',
            'hubdrive',
            'katdrive',
            'filepress',
            'filebee',
            'onlystream',
            'telegram.me',
            't.me',
        ]

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if not href or href.startswith('#'):
                continue

            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Skip same-domain links
            if parsed.netloc == base_domain:
                continue

            # Check if it matches any target domain
            for domain in target_domains:
                if domain in parsed.netloc or domain in full_url:
                    return full_url

        # Last resort: return any external http link
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if href.startswith('http') and base_domain not in href:
                return href

        return None

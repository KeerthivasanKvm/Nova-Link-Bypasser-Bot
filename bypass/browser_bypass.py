"""
Browser Bypass
==============
Browser automation for complex bypass scenarios.
Uses Playwright for headless browser automation.
"""

import re
import time
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class BrowserBypass(BaseBypass):
    """
    Browser automation bypass method.
    Uses Playwright for:
    - Full JavaScript execution
    - Waiting for dynamic content
    - Handling complex interactions
    - Bypassing advanced protections
    """
    
    METHOD_NAME = "browser_auto"
    PRIORITY = 5
    TIMEOUT = 60
    
    def __init__(self):
        super().__init__()
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def _init_browser(self):
        """Initialize browser instance"""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-blink-features=AutomationControlled',
                    ]
                )
            except Exception as e:
                # Try installing browsers if not found
                if 'Executable doesn\'t exist' in str(e):
                    logger.warning("[Browser] Chromium not found, attempting install...")
                    import subprocess
                    subprocess.run(['playwright', 'install', 'chromium'], check=True)
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                        ]
                    )
                else:
                    raise
    
    async def _close_browser(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt browser-based bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        page: Optional[Page] = None
        
        try:
            logger.info(f"[Browser] Attempting bypass for: {url}")
            
            # Initialize browser
            await self._init_browser()
            
            # Create new page
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
            )
            
            # Add stealth scripts
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            page = await context.new_page()
            
            # Navigate to URL
            response = await page.goto(
                url,
                wait_until='networkidle',
                timeout=self.TIMEOUT * 1000
            )
            
            if not response:
                raise Exception("Page navigation failed")
            
            # Wait for any challenges to complete
            await asyncio.sleep(3)
            
            # Try different methods
            result = None
            
            # Method 1: Look for direct links
            result = await self._find_direct_link(page)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Browser] Direct link found: {result}")
                await context.close()
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'direct_link'}
                )
            
            # Method 2: Handle countdown timers
            result = await self._handle_countdown(page)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Browser] Countdown bypass: {result}")
                await context.close()
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'countdown_bypass'}
                )
            
            # Method 3: Click buttons
            result = await self._click_buttons(page)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Browser] Button click bypass: {result}")
                await context.close()
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'button_click'}
                )
            
            # Method 4: Extract from JavaScript
            result = await self._extract_from_js(page)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[Browser] JS extraction: {result}")
                await context.close()
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'js_extraction'}
                )
            
            # Method 5: Check final URL
            final_url = page.url
            if final_url != url:
                execution_time = time.time() - start_time
                logger.info(f"[Browser] Redirect detected: {final_url}")
                await context.close()
                return BypassResult.success_result(
                    url=final_url,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'redirect_follow'}
                )
            
            await context.close()
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="Browser bypass failed",
                method=self.METHOD_NAME,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[Browser] Error: {e}")
            if page:
                try:
                    await page.close()
                except:
                    pass
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    async def _find_direct_link(self, page: Page) -> Optional[str]:
        """
        Find direct download/link on page.
        
        Args:
            page: Playwright page
            
        Returns:
            URL or None
        """
        try:
            # Look for common link selectors
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
                '[data-url]',
                '[data-link]',
                '[data-href]',
            ]
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    href = await element.get_attribute('href')
                    if href:
                        return href
                    
                    # Check data attributes
                    for attr in ['data-url', 'data-link', 'data-href', 'data-download']:
                        value = await element.get_attribute(attr)
                        if value:
                            return value
            
            # Look for links with specific text
            link_texts = ['download', 'get link', 'continue', 'go', 'proceed', 'click here']
            for text in link_texts:
                link = await page.query_selector(f'a:has-text("{text}")')
                if link:
                    href = await link.get_attribute('href')
                    if href:
                        return href
        
        except Exception as e:
            logger.debug(f"Direct link search failed: {e}")
        
        return None
    
    async def _handle_countdown(self, page: Page) -> Optional[str]:
        """
        Handle countdown timers.
        
        Args:
            page: Playwright page
            
        Returns:
            URL or None
        """
        try:
            # Check for countdown element
            countdown_selectors = [
                '#countdown',
                '.countdown',
                '[id*="timer"]',
                '[class*="timer"]',
                '[id*="countdown"]',
                '[class*="countdown"]',
            ]
            
            has_countdown = False
            for selector in countdown_selectors:
                element = await page.query_selector(selector)
                if element:
                    has_countdown = True
                    break
            
            if has_countdown:
                # Wait for countdown to finish (max 15 seconds)
                for _ in range(15):
                    await asyncio.sleep(1)
                    
                    # Check if link appeared
                    result = await self._find_direct_link(page)
                    if result:
                        return result
                    
                    # Check for visible download button
                    button = await page.query_selector('a:visible, button:visible')
                    if button:
                        await button.click()
                        await asyncio.sleep(2)
                        
                        # Check if new page opened
                        pages = page.context.pages
                        if len(pages) > 1:
                            new_page = pages[-1]
                            url = new_page.url
                            await new_page.close()
                            return url
                        
                        # Check for link after click
                        result = await self._find_direct_link(page)
                        if result:
                            return result
        
        except Exception as e:
            logger.debug(f"Countdown handling failed: {e}")
        
        return None
    
    async def _click_buttons(self, page: Page) -> Optional[str]:
        """
        Click buttons to reveal links.
        
        Args:
            page: Playwright page
            
        Returns:
            URL or None
        """
        try:
            # Common button selectors
            button_selectors = [
                'button:has-text("Continue")',
                'button:has-text("Get Link")',
                'button:has-text("Download")',
                'a:has-text("Continue")',
                'a:has-text("Get Link")',
                'a:has-text("Download")',
                '.btn:visible',
                'button[type="submit"]',
                'input[type="submit"]',
            ]
            
            for selector in button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        # Check if button is visible
                        is_visible = await button.is_visible()
                        if is_visible:
                            await button.click()
                            await asyncio.sleep(3)
                            
                            # Check for new page
                            pages = page.context.pages
                            if len(pages) > 1:
                                new_page = pages[-1]
                                url = new_page.url
                                if url != page.url:
                                    await new_page.close()
                                    return url
                            
                            # Check for link on current page
                            result = await self._find_direct_link(page)
                            if result:
                                return result
                            
                            # Check if URL changed
                            if page.url != page.url:
                                return page.url
                
                except Exception:
                    continue
        
        except Exception as e:
            logger.debug(f"Button click failed: {e}")
        
        return None
    
    async def _extract_from_js(self, page: Page) -> Optional[str]:
        """
        Extract URL from JavaScript variables.
        
        Args:
            page: Playwright page
            
        Returns:
            URL or None
        """
        try:
            # Common variable names
            var_names = ['url', 'link', 'href', 'redirect', 'target', 'downloadUrl', 'fileUrl']
            
            for var_name in var_names:
                try:
                    value = await page.evaluate(f'window.{var_name}')
                    if value and isinstance(value, str) and value.startswith('http'):
                        return value
                except:
                    pass
            
            # Try to find in page source
            content = await page.content()
            
            # Look for URL patterns
            patterns = [
                r'var\s+url\s*=\s*["\'](https?://[^"\']+)["\']',
                r'var\s+link\s*=\s*["\'](https?://[^"\']+)["\']',
                r'["\'](https?://[^"\']+)["\']\s*;\s*//\s*download',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if self._is_valid_url(match):
                        return match
        
        except Exception as e:
            logger.debug(f"JS extraction failed: {e}")
        
        return None

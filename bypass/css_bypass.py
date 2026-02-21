"""
CSS Bypass
==========
Bypass for CSS-hidden elements and visual obfuscation.
"""

import re
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Comment

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class CSSBypass(BaseBypass):
    """
    CSS-based bypass method.
    Handles:
    - Display:none elements
    - Visibility:hidden elements
    - Opacity:0 elements
    - Position off-screen elements
    - CSS text obfuscation
    """
    
    METHOD_NAME = "css_hidden"
    PRIORITY = 2
    TIMEOUT = 15
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt CSS-based bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        try:
            logger.info(f"[CSS] Attempting bypass for: {url}")
            
            # Fetch the page
            response = self.session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            base_url = response.url
            
            # Extract CSS
            css_text = self._extract_css(soup, base_url)
            
            # Find hidden elements
            result = None
            
            # Method 1: Check for hidden links
            result = self._find_hidden_links(soup, css_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[CSS] Hidden link found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'hidden_link'}
                )
            
            # Method 2: Check for CSS obfuscated text
            result = self._deobfuscate_css_text(soup, css_text)
            if result and self._is_valid_url(result):
                execution_time = time.time() - start_time
                logger.info(f"[CSS] Deobfuscated link: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'css_deobfuscation'}
                )
            
            # Method 3: Check for pseudo-elements
            result = self._check_pseudo_elements(soup, css_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[CSS] Pseudo-element link: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'pseudo_element'}
                )
            
            # Method 4: Check HTML comments
            result = self._check_comments(soup, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[CSS] Comment link found: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'html_comment'}
                )
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="No CSS bypass method worked",
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
            logger.error(f"[CSS] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    def _extract_css(self, soup: BeautifulSoup, base_url: str) -> str:
        """
        Extract all CSS from page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL
            
        Returns:
            Combined CSS text
        """
        css_parts = []
        
        # Inline styles
        for style in soup.find_all('style'):
            css_parts.append(style.get_text())
        
        # External stylesheets (try to fetch)
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                try:
                    css_url = urljoin(base_url, href)
                    response = self.session.get(css_url, timeout=5)
                    if response.status_code == 200:
                        css_parts.append(response.text)
                except Exception:
                    pass
        
        # Inline style attributes
        for tag in soup.find_all(style=True):
            css_parts.append(f"{{ {tag['style']} }}")
        
        return '\n'.join(css_parts)
    
    def _find_hidden_links(
        self,
        soup: BeautifulSoup,
        css_text: str,
        base_url: str
    ) -> Optional[str]:
        """
        Find links hidden with CSS.
        
        Args:
            soup: BeautifulSoup object
            css_text: CSS text
            base_url: Base URL
            
        Returns:
            Hidden link URL or None
        """
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            # Check inline style
            style = link.get('style', '').lower()
            
            # Check for hidden indicators
            is_hidden = any([
                'display:none' in style,
                'display: none' in style,
                'visibility:hidden' in style,
                'visibility: hidden' in style,
                'opacity:0' in style,
                'opacity: 0' in style,
                'position:absolute' in style and 'left:-' in style,
                'position: absolute' in style and 'left: -' in style,
                'height:0' in style,
                'height: 0' in style,
                'width:0' in style,
                'width: 0' in style,
                'z-index:-' in style,
                'z-index: -' in style,
            ])
            
            # Check CSS classes
            if not is_hidden and link.get('class'):
                for class_name in link['class']:
                    # Check if class hides elements
                    if self._class_hides_elements(class_name, css_text):
                        is_hidden = True
                        break
            
            # Check ID
            if not is_hidden and link.get('id'):
                if self._id_hides_elements(link['id'], css_text):
                    is_hidden = True
            
            if is_hidden:
                href = link.get('href', '')
                if href and not href.startswith(('#', 'javascript:')):
                    full_url = urljoin(base_url, href)
                    if self._is_valid_url(full_url):
                        return full_url
        
        return None
    
    def _class_hides_elements(self, class_name: str, css_text: str) -> bool:
        """Check if CSS class hides elements"""
        pattern = rf'\.{re.escape(class_name)}\s*{{[^}}]*(?:display:\s*none|visibility:\s*hidden|opacity:\s*0)'
        return bool(re.search(pattern, css_text, re.IGNORECASE))
    
    def _id_hides_elements(self, element_id: str, css_text: str) -> bool:
        """Check if CSS ID hides elements"""
        pattern = rf'#{re.escape(element_id)}\s*{{[^}}]*(?:display:\s*none|visibility:\s*hidden|opacity:\s*0)'
        return bool(re.search(pattern, css_text, re.IGNORECASE))
    
    def _deobfuscate_css_text(
        self,
        soup: BeautifulSoup,
        css_text: str
    ) -> Optional[str]:
        """
        Deobfuscate text hidden with CSS.
        
        Args:
            soup: BeautifulSoup object
            css_text: CSS text
            
        Returns:
            Deobfuscated URL or None
        """
        # Look for character manipulation
        # Common technique: text-indent, letter-spacing, word-spacing
        
        # Check for text-indent hiding
        text_indent_pattern = r'text-indent:\s*-?\d+px'
        if re.search(text_indent_pattern, css_text):
            # Text might be hidden, look for actual content
            for tag in soup.find_all(text=True):
                text = str(tag).strip()
                if text.startswith('http') and self._is_valid_url(text):
                    return text
        
        # Check for font-size: 0 hiding
        font_size_pattern = r'font-size:\s*0'
        if re.search(font_size_pattern, css_text, re.IGNORECASE):
            # Content might be split across elements
            combined = ''
            for tag in soup.find_all(['span', 'div', 'i', 'b']):
                combined += tag.get_text(strip=True)
            
            if self._is_valid_url(combined):
                return combined
        
        # Check for content in ::before or ::after
        content_pattern = r'content:\s*["\']([^"\']+)["\']'
        contents = re.findall(content_pattern, css_text)
        for content in contents:
            # Remove escape sequences
            content = content.replace('\\', '')
            if self._is_valid_url(content):
                return content
            # Try combining multiple content pieces
            
        return None
    
    def _check_pseudo_elements(
        self,
        soup: BeautifulSoup,
        css_text: str,
        base_url: str
    ) -> Optional[str]:
        """
        Check for links in pseudo-elements.
        
        Args:
            soup: BeautifulSoup object
            css_text: CSS text
            base_url: Base URL
            
        Returns:
            URL or None
        """
        # Look for attr() function in CSS
        attr_pattern = r'content:\s*attr\(([^)]+)\)'
        attrs = re.findall(attr_pattern, css_text)
        
        for attr in attrs:
            # Find elements with this attribute
            for tag in soup.find_all(attrs={attr: True}):
                value = tag.get(attr, '')
                if self._is_valid_url(value):
                    return value
                # Might be relative URL
                full_url = urljoin(base_url, value)
                if self._is_valid_url(full_url):
                    return full_url
        
        return None
    
    def _check_comments(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Check HTML comments for hidden links.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL
            
        Returns:
            URL or None
        """
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        for comment in comments:
            comment_text = str(comment)
            
            # Look for URLs in comments
            urls = self._extract_links(comment_text)
            for url in urls:
                if self._is_valid_url(url):
                    return url
                # Try with base URL
                full_url = urljoin(base_url, url)
                if self._is_valid_url(full_url):
                    return full_url
            
            # Look for base64 in comments
            decoded = self._find_base64_in_text(comment_text)
            if decoded and self._is_valid_url(decoded):
                return decoded
        
        return None
    
    def _find_base64_in_text(self, text: str) -> Optional[str]:
        """Find base64 encoded strings in text"""
        # Look for base64 patterns
        pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        matches = re.findall(pattern, text)
        
        for match in matches:
            decoded = self._decode_base64(match)
            if decoded and (self._is_valid_url(decoded) or 'http' in decoded):
                return decoded
        
        return None

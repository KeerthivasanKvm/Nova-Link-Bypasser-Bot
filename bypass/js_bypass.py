"""
JavaScript Bypass
=================
Bypass for JavaScript-protected links.
"""

import re
import json
import time
import execjs
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class JavaScriptBypass(BaseBypass):
    """
    JavaScript-based bypass method.
    Handles:
    - JavaScript redirects
    - Encoded JavaScript
    - Obfuscated JavaScript
    - Dynamic link generation
    - Timer-based redirects
    """
    
    METHOD_NAME = "javascript"
    PRIORITY = 3
    TIMEOUT = 20
    
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt JavaScript-based bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        try:
            logger.info(f"[JS] Attempting bypass for: {url}")
            
            # Fetch the page
            response = self.session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            html_text = response.text
            base_url = response.url
            
            result = None
            
            # Method 1: Extract and execute inline scripts
            result = self._execute_inline_scripts(html_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[JS] Inline script bypass: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'inline_script'}
                )
            
            # Method 2: Decode obfuscated JavaScript
            result = self._decode_obfuscated_js(html_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[JS] Deobfuscated bypass: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'deobfuscation'}
                )
            
            # Method 3: Find timer-based redirects
            result = self._handle_timer_redirects(html_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[JS] Timer redirect bypass: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'timer_bypass'}
                )
            
            # Method 4: Extract from JavaScript variables
            result = self._extract_js_variables(html_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[JS] Variable extraction: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'variable_extraction'}
                )
            
            # Method 5: Handle AJAX-based links
            result = self._handle_ajax_links(html_text, base_url)
            if result:
                execution_time = time.time() - start_time
                logger.info(f"[JS] AJAX bypass: {result}")
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=execution_time,
                    metadata={'technique': 'ajax_bypass'}
                )
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message="No JavaScript bypass method worked",
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
            logger.error(f"[JS] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    def _execute_inline_scripts(self, html_text: str, base_url: str) -> Optional[str]:
        """
        Extract and execute inline JavaScript.
        
        Args:
            html_text: HTML content
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        # Extract all script tags
        soup = BeautifulSoup(html_text, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            js_code = script.string
            if not js_code:
                continue
            
            try:
                # Look for direct redirects
                redirect_patterns = [
                    r'window\.location\s*=\s*["\']([^"\']+)["\']',
                    r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'location\.replace\(["\']([^"\']+)["\']\)',
                    r'location\.assign\(["\']([^"\']+)["\']\)',
                    r'top\.location\s*=\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in redirect_patterns:
                    match = re.search(pattern, js_code)
                    if match:
                        url = match.group(1)
                        # Handle variable references
                        if url.startswith('$') or url.startswith('{'):
                            continue
                        full_url = urljoin(base_url, url)
                        if self._is_valid_url(full_url):
                            return full_url
                
                # Try to execute with execjs for complex scripts
                result = self._safe_execute_js(js_code, base_url)
                if result:
                    return result
                    
            except Exception as e:
                logger.debug(f"Script execution failed: {e}")
                continue
        
        return None
    
    def _safe_execute_js(self, js_code: str, base_url: str) -> Optional[str]:
        """
        Safely execute JavaScript code.
        
        Args:
            js_code: JavaScript code
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        try:
            # Create a minimal context
            context = execjs.compile(f"""
                var window = {{
                    location: {{ href: '' }},
                    open: function(url) {{ return url; }}
                }};
                var document = {{}};
                var location = window.location;
                var top = window;
                
                {js_code}
                
                window.location.href;
            """)
            
            result = context.eval("")
            if result and self._is_valid_url(result):
                return result
            
            # Check if window.location was modified
            result = context.eval("window.location.href")
            if result and self._is_valid_url(result):
                return result
                
        except Exception as e:
            logger.debug(f"JS execution error: {e}")
        
        return None
    
    def _decode_obfuscated_js(self, html_text: str, base_url: str) -> Optional[str]:
        """
        Decode obfuscated JavaScript.
        
        Args:
            html_text: HTML content
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        # Common obfuscation patterns
        
        # 1. String concatenation
        concat_pattern = r'["\']([^"\']+)["\']\s*\+\s*["\']([^"\']+)["\']'
        matches = re.findall(concat_pattern, html_text)
        for match in matches:
            combined = ''.join(match)
            if self._is_valid_url(combined):
                return combined
        
        # 2. fromCharCode
        charcode_pattern = r'String\.fromCharCode\(([^)]+)\)'
        matches = re.findall(charcode_pattern, html_text)
        for match in matches:
            try:
                # Parse char codes
                codes = [int(x.strip()) for x in match.split(',')]
                decoded = ''.join(chr(c) for c in codes)
                if self._is_valid_url(decoded):
                    return decoded
            except Exception:
                pass
        
        # 3. atob (base64 decode)
        atob_pattern = r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)'
        matches = re.findall(atob_pattern, html_text)
        for match in matches:
            decoded = self._decode_base64(match)
            if decoded and self._is_valid_url(decoded):
                return decoded
        
        # 4. decodeURIComponent
        decode_pattern = r'decodeURIComponent\(["\']([^"\']+)["\']\)'
        matches = re.findall(decode_pattern, html_text)
        for match in matches:
            try:
                decoded = unquote(match)
                if self._is_valid_url(decoded):
                    return decoded
            except Exception:
                pass
        
        # 5. Hex encoded strings
        hex_pattern = r'["\']((?:\\x[0-9a-fA-F]{2})+)["\']'
        matches = re.findall(hex_pattern, html_text)
        for match in matches:
            try:
                decoded = bytes.fromhex(match.replace('\\x', '')).decode('utf-8')
                if self._is_valid_url(decoded):
                    return decoded
            except Exception:
                pass
        
        # 6. Unicode escape sequences
        unicode_pattern = r'["\']((?:\\u[0-9a-fA-F]{4})+)["\']'
        matches = re.findall(unicode_pattern, html_text)
        for match in matches:
            try:
                decoded = match.encode().decode('unicode_escape')
                if self._is_valid_url(decoded):
                    return decoded
            except Exception:
                pass
        
        return None
    
    def _handle_timer_redirects(self, html_text: str, base_url: str) -> Optional[str]:
        """
        Handle timer-based redirects.
        
        Args:
            html_text: HTML content
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        # Look for setTimeout/setInterval with redirects
        timer_patterns = [
            r'setTimeout\s*\(\s*function\s*\(\s*\)\s*\{[^}]*location[^}]*\}\s*,\s*\d+\s*\)',
            r'setTimeout\s*\(\s*["\']([^"\']+)["\']\s*,\s*\d+\s*\)',
            r'setInterval\s*\([^)]*location[^)]*\)',
        ]
        
        for pattern in timer_patterns:
            match = re.search(pattern, html_text, re.DOTALL)
            if match:
                # Extract URL from timer
                url_match = re.search(r'["\'](https?://[^"\']+)["\']', match.group(0))
                if url_match:
                    return url_match.group(1)
        
        # Look for countdown timers that reveal links
        countdown_pattern = r'var\s+\w+\s*=\s*(\d+)\s*;'
        matches = re.findall(countdown_pattern, html_text)
        
        if matches:
            # Page has countdown, look for link that will be revealed
            link_pattern = r'document\.getElementById\s*\(\s*["\']([^"\']+)["\']\s*\)\.\w+\s*=\s*["\']([^"\']+)["\']'
            link_matches = re.findall(link_pattern, html_text)
            for _, url in link_matches:
                full_url = urljoin(base_url, url)
                if self._is_valid_url(full_url):
                    return full_url
        
        return None
    
    def _extract_js_variables(self, html_text: str, base_url: str) -> Optional[str]:
        """
        Extract URLs from JavaScript variables.
        
        Args:
            html_text: HTML content
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        # Look for common variable patterns
        var_patterns = [
            r'var\s+url\s*=\s*["\']([^"\']+)["\']',
            r'var\s+link\s*=\s*["\']([^"\']+)["\']',
            r'var\s+redirect\s*=\s*["\']([^"\']+)["\']',
            r'var\s+target\s*=\s*["\']([^"\']+)["\']',
            r'const\s+url\s*=\s*["\']([^"\']+)["\']',
            r'const\s+link\s*=\s*["\']([^"\']+)["\']',
            r'let\s+url\s*=\s*["\']([^"\']+)["\']',
            r'let\s+link\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in var_patterns:
            matches = re.findall(pattern, html_text)
            for match in matches:
                full_url = urljoin(base_url, match)
                if self._is_valid_url(full_url):
                    return full_url
        
        # Look for JSON data
        json_pattern = r'var\s+\w+\s*=\s*(\{[^;]+\})\s*;'
        matches = re.findall(json_pattern, html_text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                # Look for URL in JSON
                for key in ['url', 'link', 'redirect', 'href', 'target']:
                    if key in data and isinstance(data[key], str):
                        if self._is_valid_url(data[key]):
                            return data[key]
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _handle_ajax_links(self, html_text: str, base_url: str) -> Optional[str]:
        """
        Handle AJAX-based link loading.
        
        Args:
            html_text: HTML content
            base_url: Base URL
            
        Returns:
            Result URL or None
        """
        # Look for fetch/XHR requests
        fetch_patterns = [
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'\.ajax\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\']',
            r'XMLHttpRequest\s*.*?open\s*\(\s*["\']\w+["\']\s*,\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in fetch_patterns:
            matches = re.findall(pattern, html_text)
            for match in matches:
                full_url = urljoin(base_url, match)
                # Try to fetch the AJAX endpoint
                try:
                    response = self.session.get(full_url, timeout=10)
                    if response.status_code == 200:
                        # Look for URL in response
                        try:
                            data = response.json()
                            for key in ['url', 'link', 'redirect', 'href', 'target', 'download']:
                                if key in data and isinstance(data[key], str):
                                    if self._is_valid_url(data[key]):
                                        return data[key]
                        except ValueError:
                            # Not JSON, check text
                            urls = self._extract_links(response.text)
                            for url in urls:
                                if self._is_valid_url(url):
                                    return url
                except Exception:
                    pass
        
        return None

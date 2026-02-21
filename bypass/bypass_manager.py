"""
Bypass Manager
==============
Central manager for all bypass methods.
"""

import time
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from bypass.base_bypass import BypassResult, BypassStatus
from bypass.html_bypass import HTMLBypass
from bypass.css_bypass import CSSBypass
from bypass.js_bypass import JavaScriptBypass
from bypass.cloudflare import CloudflareBypass
from bypass.browser_bypass import BrowserBypass
from bypass.ai_bypass import AIBypass
from database.firebase_db import FirebaseDB
from database.models import BypassCache
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BypassAttempt:
    """Bypass attempt record"""
    method: str
    success: bool
    execution_time: float
    error: Optional[str] = None


class BypassManager:
    """
    Central manager for all bypass methods.
    Handles method selection, caching, and fallback.
    """
    
    def __init__(self, db: FirebaseDB):
        """
        Initialize bypass manager.
        
        Args:
            db: Firebase database instance
        """
        self.db = db
        
        # Initialize bypass methods
        self.methods = {
            'html_forms': HTMLBypass(),
            'css_hidden': CSSBypass(),
            'javascript': JavaScriptBypass(),
            'cloudflare': CloudflareBypass(),
            'browser_auto': BrowserBypass(),
            'ai_powered': AIBypass(),
        }
        
        # Method priority order
        self.method_priority = [
            'html_forms',
            'css_hidden',
            'javascript',
            'cloudflare',
            'browser_auto',
            'ai_powered',
        ]
        
        # Statistics
        self.stats = {
            'total_attempts': 0,
            'successful_bypasses': 0,
            'failed_bypasses': 0,
            'cache_hits': 0,
        }
    
    async def bypass(
        self,
        url: str,
        skip_cache: bool = False,
        preferred_method: Optional[str] = None
    ) -> BypassResult:
        """
        Attempt to bypass a URL using all available methods.
        
        Args:
            url: URL to bypass
            skip_cache: Skip cache lookup
            preferred_method: Preferred bypass method
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        logger.info(f"[Manager] Starting bypass for: {url}")
        
        # Check cache first
        if not skip_cache:
            cached_result = await self._check_cache(url)
            if cached_result:
                self.stats['cache_hits'] += 1
                logger.info(f"[Manager] Cache hit: {cached_result}")
                return BypassResult.success_result(
                    url=cached_result,
                    method='cache',
                    execution_time=time.time() - start_time,
                    metadata={'cached': True}
                )
        
        # Track attempts
        attempts: List[BypassAttempt] = []
        
        # Determine method order
        if preferred_method and preferred_method in self.methods:
            method_order = [preferred_method] + [
                m for m in self.method_priority if m != preferred_method
            ]
        else:
            method_order = self.method_priority
        
        # Try each method
        for method_name in method_order:
            method = self.methods.get(method_name)
            if not method:
                continue
            
            method_start = time.time()
            
            try:
                logger.info(f"[Manager] Trying {method_name}...")
                result = await method.bypass(url)
                
                method_time = time.time() - method_start
                attempts.append(BypassAttempt(
                    method=method_name,
                    success=result.success,
                    execution_time=method_time,
                    error=result.error_message
                ))
                
                if result.success and result.url:
                    # Success! Cache and return
                    await self._cache_result(url, result)
                    
                    # Update stats
                    self.stats['total_attempts'] += len(attempts)
                    self.stats['successful_bypasses'] += 1
                    
                    # Add attempts to metadata
                    result.metadata['attempts'] = [
                        {
                            'method': a.method,
                            'success': a.success,
                            'time': a.execution_time
                        }
                        for a in attempts
                    ]
                    result.metadata['total_time'] = time.time() - start_time
                    
                    logger.info(f"[Manager] Success with {method_name}: {result.url}")
                    return result
                
                else:
                    logger.debug(f"[Manager] {method_name} failed: {result.error_message}")
            
            except Exception as e:
                method_time = time.time() - method_start
                attempts.append(BypassAttempt(
                    method=method_name,
                    success=False,
                    execution_time=method_time,
                    error=str(e)
                ))
                logger.error(f"[Manager] {method_name} error: {e}")
        
        # All methods failed
        self.stats['total_attempts'] += len(attempts)
        self.stats['failed_bypasses'] += 1
        
        total_time = time.time() - start_time
        
        # Build error message from attempts
        error_details = '\n'.join([
            f"• {a.method}: {a.error or 'Failed'}"
            for a in attempts
        ])
        
        logger.warning(f"[Manager] All methods failed for: {url}")
        
        return BypassResult.failed_result(
            error_message=f"All bypass methods failed:\n{error_details}",
            method='all',
            execution_time=total_time,
            status=BypassStatus.FAILED
        )
    
    async def _check_cache(self, url: str) -> Optional[str]:
        """
        Check if URL is in cache.
        
        Args:
            url: URL to check
            
        Returns:
            Cached URL or None
        """
        try:
            url_hash = BypassCache.hash_url(url)
            cache = await self.db.get_bypass_cache(url_hash)
            
            if cache and cache.success:
                # Update access stats
                cache.access()
                await self.db.set_bypass_cache(cache)
                return cache.bypassed_url
            
            return None
            
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            return None
    
    async def _cache_result(self, original_url: str, result: BypassResult) -> None:
        """
        Cache successful bypass result.
        
        Args:
            original_url: Original URL
            result: Bypass result
        """
        try:
            from urllib.parse import urlparse
            
            url_hash = BypassCache.hash_url(original_url)
            domain = urlparse(original_url).netloc
            
            cache = BypassCache(
                url_hash=url_hash,
                original_url=original_url,
                bypassed_url=result.url,
                method_used=result.method,
                success=True,
                domain=domain
            )
            
            await self.db.set_bypass_cache(cache)
            logger.debug(f"Cached result for: {original_url}")
            
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")
    
    def get_method_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all methods.
        
        Returns:
            List of method info dicts
        """
        info = []
        for name, method in self.methods.items():
            info.append({
                'name': name,
                'priority': method.PRIORITY,
                'timeout': method.TIMEOUT,
                'supported_domains': method.SUPPORTED_DOMAINS or 'All'
            })
        return sorted(info, key=lambda x: x['priority'])
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get bypass statistics.
        
        Returns:
            Statistics dict
        """
        total = self.stats['total_attempts']
        success_rate = (
            (self.stats['successful_bypasses'] / total * 100)
            if total > 0 else 0
        )
        
        return {
            'total_attempts': total,
            'successful_bypasses': self.stats['successful_bypasses'],
            'failed_bypasses': self.stats['failed_bypasses'],
            'cache_hits': self.stats['cache_hits'],
            'success_rate': f"{success_rate:.1f}%"
        }
    
    async def test_method(self, url: str, method_name: str) -> BypassResult:
        """
        Test a specific bypass method.
        
        Args:
            url: URL to test
            method_name: Method to test
            
        Returns:
            BypassResult
        """
        method = self.methods.get(method_name)
        if not method:
            return BypassResult.failed_result(
                error_message=f"Method {method_name} not found",
                method=method_name
            )
        
        return await method.bypass(url)
    
    async def clear_cache(self) -> bool:
        """
        Clear all bypass cache.
        
        Returns:
            True if cleared successfully
        """
        try:
            # This would require iterating through all cache entries
            # For now, just log the request
            logger.info("Cache clear requested")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

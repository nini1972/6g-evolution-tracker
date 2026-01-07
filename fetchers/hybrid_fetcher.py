import structlog
from typing import Optional, Dict
from .base_fetcher import BaseFetcher, FetchResult
from .httpx_fetcher import HttpxFetcher
from .playwright_fetcher import PlaywrightFetcher
from pathlib import Path
import json

logger = structlog.get_logger()

class HybridFetcher(BaseFetcher):
    """
    Smart fetcher that tries httpx first, falls back to Playwright if needed.
    Learns from past attempts and caches the successful method per domain.
    """
    
    def __init__(self, cache_file: str = "fetch_method_cache.json"):
        self.httpx_fetcher = HttpxFetcher()
        self.playwright_fetcher = PlaywrightFetcher()
        self.cache_file = Path(cache_file)
        self.method_cache: Dict[str, str] = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """Load cached fetch methods for domains"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, FileNotFoundError):
                return {}
        return {}
    
    def _save_cache(self):
        """Persist fetch method cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.method_cache, f, indent=2)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for caching"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """
        Smart fetch with fallback strategy:
        1. Check cache for known successful method
        2. Try httpx first (fast)
        3. If httpx fails with 403/bot detection OR returns HTML, try Playwright
        4. Cache successful method for future use
        """
        domain = self._get_domain(url)
        force_method = kwargs.get("force_method", None)
        
        # Check cache
        cached_method = self.method_cache.get(domain)
        
        # If we have a cached success or forced method, use it
        if force_method == "playwright" or cached_method == "playwright":
            logger.info("using_playwright", url=url, reason="cached" if cached_method else "forced")
            result = await self.playwright_fetcher.fetch(url, **kwargs)
            if result.success:
                self.method_cache[domain] = "playwright"
                self._save_cache()
            return result
        
        # Try httpx first (fast path)
        logger.info("trying_httpx", url=url)
        result = await self.httpx_fetcher.fetch(url, **kwargs)
        
        # If httpx succeeded, check if content is valid
        if result.success:
            # Check if we got HTML when expecting RSS/XML
            content_lower = (result.content or "").lower()
            is_html_response = (
                'incapsula' in content_lower or
                'cloudflare' in content_lower or
                ('<html' in content_lower and '<?xml' not in content_lower[:100])
            )
            
            if is_html_response:
                logger.warning("httpx_returned_html_trying_playwright", url=url)
                # Don't cache this as success, try Playwright instead
            else:
                logger.info("httpx_success", url=url)
                self.method_cache[domain] = "httpx"
                self._save_cache()
                return result
        
        # If httpx failed with bot detection indicators or returned HTML, try Playwright
        should_try_playwright = (
            result.status_code == 403 or
            result.status_code == 429 or
            "bot" in (result.error or "").lower() or
            "cloudflare" in (result.error or "").lower() or
            (result.success and is_html_response)
        )
        
        if should_try_playwright and not kwargs.get("no_fallback", False):
            logger.warning(
                "httpx_failed_trying_playwright",
                url=url,
                status_code=result.status_code,
                error=result.error if not result.success else "HTML response"
            )
            
            playwright_result = await self.playwright_fetcher.fetch(url, **kwargs)
            
            if playwright_result.success:
                logger.info("playwright_fallback_success", url=url)
                self.method_cache[domain] = "playwright"
                self._save_cache()
                return playwright_result
            else:
                logger.error("playwright_fallback_failed", url=url)
                return playwright_result
        
        # Return original httpx failure if no fallback attempted
        return result
    
    async def close(self):
        """Close all fetchers"""
        await self.httpx_fetcher.close()
        await self.playwright_fetcher.close()
        self._save_cache()
    
    @property
    def name(self) -> str:
        return "hybrid"

import httpx
import random
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .base_fetcher import BaseFetcher, FetchResult
from config.user_agents import USER_AGENTS

class HttpxFetcher(BaseFetcher):
    """Fast HTTP fetching using httpx (from Phase 1)"""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def _ensure_client(self):
        """Lazy client initialization"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                http2=True,
                timeout=self.timeout,
                follow_redirects=True,
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch using httpx with retry logic"""
        await self._ensure_client()
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            **kwargs.get("headers", {})
        }
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            return FetchResult(
                success=True,
                content=response.text,
                status_code=response.status_code,
                method_used="httpx",
                metadata={"headers": dict(response.headers)}
            )
            
        except httpx.HTTPStatusError as e:
            return FetchResult(
                success=False,
                status_code=e.response.status_code,
                error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                method_used="httpx"
            )
            
        except httpx.TimeoutException:
            return FetchResult(
                success=False,
                error="Request timeout",
                method_used="httpx"
            )
            
        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                method_used="httpx"
            )
    
    async def close(self):
        """Close the httpx client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    @property
    def name(self) -> str:
        return "httpx"

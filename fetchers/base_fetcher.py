from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class FetchResult:
    """Standardized fetch result"""
    success: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    method_used: str = ""  # 'httpx', 'playwright', etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseFetcher(ABC):
    """Abstract base class for all fetchers"""
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch content from URL"""
        pass
    
    @abstractmethod
    async def close(self):
        """Cleanup resources"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Fetcher identifier"""
        pass

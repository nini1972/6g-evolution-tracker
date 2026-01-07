"""Fetching layer with hybrid strategy"""

from .base_fetcher import BaseFetcher, FetchResult
from .httpx_fetcher import HttpxFetcher
from .playwright_fetcher import PlaywrightFetcher
from .hybrid_fetcher import HybridFetcher

__all__ = [
    'BaseFetcher',
    'FetchResult',
    'HttpxFetcher',
    'PlaywrightFetcher',
    'HybridFetcher',
]

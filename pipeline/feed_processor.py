"""
Feed processor for the 6G Evolution Tracker.
Handles RSS feed fetching, keyword relevance filtering, and async AI enrichment.
"""
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import structlog
from bs4 import BeautifulSoup

import google.genai as genai

from config.prompts import ANALYSIS_PROMPT_TEMPLATE
from fetchers.hybrid_fetcher import HybridFetcher
from pipeline.utils import hash_url, is_recent, parse_ai_response, relevance_score

# Re-export for backwards compatibility so callers importing from feed_processor still work
__all__ = [
    "hash_url",
    "is_recent",
    "relevance_score",
    "parse_ai_response",
    "get_ai_summary",
    "get_ai_summary_async",
    "fetch_feed",
    "fetch_all_feeds",
    "process_feeds",
    "get_fetcher",
    "cleanup_fetcher",
]

# Keep old private name for backwards compatibility (tests that import _parse_ai_response)
_parse_ai_response = parse_ai_response

logger = structlog.get_logger()

# ⚙️ Configuration
RELEVANCE_THRESHOLD = 2

# Global fetcher instance (shared across the run)
_fetcher: Optional[HybridFetcher] = None


async def get_fetcher() -> HybridFetcher:
    """Get or create the global fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = HybridFetcher()
    return _fetcher


async def cleanup_fetcher() -> None:
    """Close and release the global fetcher."""
    global _fetcher
    if _fetcher:
        await _fetcher.close()
        _fetcher = None


# ---------------------------------------------------------------------------
# AI enrichment
# ---------------------------------------------------------------------------

def get_ai_summary(
    title: str,
    summary: str,
    site_name: str,
    client: genai.Client,
    model: str,
) -> Optional[dict]:
    """
    Get an AI-powered summary and 6G impact score from Gemini.
    Returns a parsed dict on success, None on failure.
    """
    if not client or not model:
        return None

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        site_name=site_name,
        title=title,
        summary=summary,
    )

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return parse_ai_response(response.text.strip(), title)
    except Exception as e:
        print(f"  ⚠️ AI Summary failed for '{title[:30]}...': {e}")
        return None


async def get_ai_summary_async(
    title: str,
    summary: str,
    site_name: str,
    client: genai.Client,
    model: str,
) -> Optional[dict]:
    """Async wrapper for :func:`get_ai_summary` using a thread pool."""
    return await asyncio.to_thread(
        get_ai_summary, title, summary, site_name, client, model
    )


# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------

async def _find_rss_feed(url: str, headers: dict, http_client) -> Optional[str]:
    """
    Try to find an RSS/Atom feed URL from an HTML page.
    Returns the feed URL if found, else None.
    """
    try:
        response = await http_client.get(
            url, headers=headers, timeout=10, follow_redirects=True
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "xml" in content_type or "rss" in content_type:
            return url

        soup = BeautifulSoup(response.content, "html.parser")
        for link in soup.find_all("link", rel="alternate"):
            link_type = link.get("type", "")
            if link_type in (
                "application/rss+xml",
                "application/atom+xml",
                "application/xml",
                "text/xml",
            ):
                feed_url = link.get("href")
                if feed_url:
                    return urljoin(url, feed_url)
        return None
    except Exception:
        return None


async def fetch_feed(source: str, url: str) -> Optional[object]:
    """Fetch a single RSS feed using the hybrid strategy."""
    hybrid = await get_fetcher()
    logger.info("fetch_started", source=source, url=url)

    result = await hybrid.fetch(url)

    if result.success:
        feed = feedparser.parse(result.content)

        if feed.bozo and not feed.entries:
            logger.warning(
                "feed_parse_error",
                source=source,
                error=getattr(feed, "bozo_exception", "Unknown parsing error"),
            )
            return None

        if not feed.entries:
            logger.warning("feed_empty", source=source)
            return None

        logger.info(
            "fetch_success",
            source=source,
            method=result.method_used,
            entries=len(feed.entries),
        )
        print(
            f"✓ {source}: {len(feed.entries)} total entries fetched "
            f"(via {result.method_used})"
        )
        return feed
    else:
        logger.error(
            "fetch_failed",
            source=source,
            status_code=result.status_code,
            error=result.error,
            method=result.method_used,
        )
        print(f"✗ {source}: Failed to fetch")
        return None


async def fetch_all_feeds(feeds: dict) -> dict:
    """Fetch all feeds in parallel using the hybrid strategy."""
    print(f"📡 Fetching {len(feeds)} RSS feeds in parallel...")

    tasks = [fetch_feed(source, url) for source, url in feeds.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    fetched: dict = {}
    for (source, _), result in zip(feeds.items(), results):
        if isinstance(result, Exception):
            logger.error("feed_exception", source=source, error=str(result))
        elif result is not None:
            fetched[source] = result

    return fetched


# ---------------------------------------------------------------------------
# Article processing
# ---------------------------------------------------------------------------

async def process_feeds(
    feeds_data: dict,
    cache: dict,
    date: str,
    client: genai.Client,
    model: str,
) -> tuple[list, int]:
    """
    Process all fetched feeds: filter by relevance, run AI enrichment
    concurrently, return (processed_entries, new_articles_count).
    """
    all_processed: list = []
    new_count = 0

    for source, feed in feeds_data.items():
        candidate_entries = []

        for entry in feed.entries:
            article_url = entry.get("link", "")
            if not article_url:
                continue
            if hash_url(article_url) in cache:
                continue
            if not is_recent(entry):
                continue
            score = relevance_score(entry)
            if score >= RELEVANCE_THRESHOLD:
                entry["_relevance_score"] = score
                candidate_entries.append(entry)

        if not candidate_entries:
            print(f"📭 {source}: No new keyword-matching updates this cycle.\n")
            continue

        # Run AI enrichment concurrently for all candidates in this feed
        print(
            f"  ✨ Generating AI insights for {len(candidate_entries)} articles "
            f"from {source}..."
        )
        ai_tasks = [
            get_ai_summary_async(
                entry.get("title", ""),
                entry.get("summary", ""),
                source,
                client,
                model,
            )
            for entry in candidate_entries
        ]
        ai_results = await asyncio.gather(*ai_tasks)

        relevant_entries = []
        for entry, ai_insights in zip(candidate_entries, ai_results):
            # Reject articles flagged as non-6G by the AI
            if ai_insights and not ai_insights.get("is_6g_relevant", True):
                print(
                    f"  🚫 AI rejected as irrelevant: {entry.get('title', '')[:50]}"
                )
                continue

            if ai_insights:
                ai_insights["impact_score"] = ai_insights.get(
                    "overall_6g_importance", 0
                )

            entry["_ai_insights"] = ai_insights
            relevant_entries.append(entry)

            article_url = entry.get("link", "")
            cache[hash_url(article_url)] = {
                "url": article_url,
                "title": entry.get("title", ""),
                "processed_date": date,
            }
            new_count += 1

        if not relevant_entries:
            print(f"📭 {source}: No new relevant updates this cycle.\n")
            continue

        # Sort by descending relevance score
        relevant_entries.sort(
            key=lambda x: x.get("_relevance_score", 0), reverse=True
        )

        print(f"🔎 {source}: {len(relevant_entries)} new relevant updates found.")
        for entry in relevant_entries:
            score = entry.get("_relevance_score", 0)
            print(f"  • [{score}] {entry.get('title')}")
            print(f"    {entry.get('link')}")
        print()

        # Build portable dicts for JSON export
        for entry in relevant_entries:
            ai = entry.get("_ai_insights")
            pub_date = date
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(
                        *entry.published_parsed[:6]
                    ).strftime("%Y-%m-%d")
                except Exception:
                    pass

            article_url = entry.get("link", "")
            all_processed.append(
                {
                    "article_id": hash_url(article_url),
                    "source": source,
                    "title": entry.get("title", ""),
                    "link": article_url,
                    "score": entry.get("_relevance_score", 0),
                    "ai_insights": ai,
                    "source_region": ai.get("source_region", "Other") if ai else "Other",
                    "summary": entry.get("summary", ""),
                    "date": pub_date,
                }
            )

        # Attach processed entries back for markdown logging
        for entry in relevant_entries:
            entry["_source"] = source

    return all_processed, new_count

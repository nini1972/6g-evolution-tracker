import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import google.genai as genai
import structlog

from config.feeds import FEEDS
from fetchers.standards_fetcher import fetch_standardization_data
from pipeline.exporters import (
    aggregate_momentum,
    evict_stale_cache,
    export_to_json,
    generate_source_target_matrix,
    update_historical_intelligence,
    update_recent_articles,
)
from pipeline.feed_processor import cleanup_fetcher, fetch_all_feeds, process_feeds
from pipeline.markdown_logger import log_to_markdown

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# ⚙️ Configuration
CACHE_FILE = "seen_articles.json"
DATE = datetime.now().strftime("%Y-%m-%d")
DIGESTS_DIR = Path("digests")
LOG_FILE = str(DIGESTS_DIR / f"6g_digest_{DATE}.md")

# 🤖 Gemini AI Config
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
model = "gemini-3-flash-preview"


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load the cache of previously seen articles."""
    cache_path = Path(CACHE_FILE)
    if cache_path.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading cache: {e}")
    return {}


def save_cache(cache: dict) -> None:
    """Save the cache of seen articles."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving cache: {e}")


# ---------------------------------------------------------------------------
# Backwards-compatibility shims (used by tests / external callers)
# ---------------------------------------------------------------------------

# Backwards-compatibility shim for the legacy get_ai_summary signature
from pipeline.feed_processor import get_ai_summary as _get_ai_summary  # noqa: E402


def get_ai_summary(title: str, summary: str, site_name: str):
    """Legacy shim – delegates to pipeline.feed_processor."""
    return _get_ai_summary(title, summary, site_name, client, model)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main_async() -> None:
    """Main async execution function."""
    print("🚀 6G Sentinel started its monthly sweep.\n")

    if not model:
        print("⚠️  Warning: GOOGLE_API_KEY not found in environment.")
        print("   AI insights and Rigorous Filtering are DISABLED.")
    else:
        print(f"🤖 Gemini AI Intelligence is ACTIVE. (Model: {model})")
    print()

    try:
        # Load and evict stale cache entries
        cache = load_cache()
        cache = evict_stale_cache(cache)

        print("📡 Fetching RSS feeds and 3GPP standardization data in parallel...")

        feeds_data, standardization_data = await asyncio.gather(
            fetch_all_feeds(FEEDS),
            fetch_standardization_data(),
            return_exceptions=True,
        )

        if isinstance(feeds_data, Exception):
            logger.error("feeds_fetch_failed", error=str(feeds_data))
            feeds_data = {}

        if not isinstance(standardization_data, dict):
            logger.warning("standards_fetch_failed", error=str(standardization_data))
            standardization_data = None
        else:
            print("✓ 3GPP standardization data fetched successfully")
            progress = standardization_data.get("release_21_progress", {})
            meetings = standardization_data.get("recent_meetings", [])
            print(f"  • Release 21 Progress: {progress.get('progress_percentage', 0)}%")
            print(f"  • Recent Meetings: {len(meetings)}")
        print()

        # Process feeds (concurrent AI enrichment)
        all_processed, new_articles_count = await process_feeds(
            feeds_data, cache, DATE, client, model
        )

        # Write Markdown digest
        DIGESTS_DIR.mkdir(exist_ok=True)
        # Group processed entries back by source for the logger
        from collections import defaultdict
        entries_by_source: dict = defaultdict(list)
        for entry in all_processed:
            entries_by_source[entry["source"]].append(entry)

        for source, entries in entries_by_source.items():
            log_to_markdown(source, entries, LOG_FILE, DATE)

        # Export for dashboard
        # Always update the rolling recent-articles history first so we have a
        # fallback for quiet cycles (all articles already cached).
        recent_articles = update_recent_articles(all_processed)

        if all_processed:
            export_to_json(all_processed, DATE, standardization_data)
            current_matrix = generate_source_target_matrix(all_processed)
            aggregate_momentum(all_processed)
            update_historical_intelligence(standardization_data, current_matrix, DATE)
        else:
            # Quiet cycle: no new articles this run.  Use the historical window
            # so that concepts, evidence, and topic-frequency panels remain
            # populated on the dashboard instead of showing empty states.
            articles_for_dashboard = recent_articles
            export_to_json(articles_for_dashboard, DATE, standardization_data)

        # Persist cache
        save_cache(cache)

        print("✅ 6G Sentinel completed its sweep.")
        print(f"📊 Total new articles processed: {new_articles_count}")
        print(f"💾 Cache updated with {len(cache)} unique articles.")
        print("🔮 The future is still under construction.")

    finally:
        await cleanup_fetcher()


def main() -> None:
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Legacy functions kept for backwards-compatibility with any existing callers.
# New code should use the pipeline modules directly.
# ---------------------------------------------------------------------------

def _legacy_removed(*args, **kwargs):  # type: ignore[no-untyped-def]
    raise NotImplementedError(
        "This function has been moved to a pipeline module. "
        "See pipeline/feed_processor.py and pipeline/exporters.py."
    )

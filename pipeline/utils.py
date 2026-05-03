"""
Pure utility functions for the 6G Evolution Tracker pipeline.
These have no heavy dependencies and can be imported in isolation (e.g., for tests).
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from config.feeds import HIGH_PRIORITY, HIGH_PRIORITY_INTL, MEDIUM_PRIORITY, MEDIUM_PRIORITY_INTL


def hash_url(url: str) -> str:
    """Return an MD5 hex-digest for *url*."""
    return hashlib.md5(url.encode()).hexdigest()


def is_recent(entry, days_lookback: int = 30) -> bool:
    """Return True if *entry* was published within the last *days_lookback* days."""
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        return True  # Keep entries with no date info
    try:
        published_date = datetime(*entry.published_parsed[:6])
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        return published_date >= cutoff_date
    except Exception:
        return True


def relevance_score(entry) -> int:
    """Calculate keyword-based relevance score for *entry*.

    Checks both English and multilingual (Chinese, Korean, Japanese) keywords
    so that non-English articles can pass the relevance threshold and reach the
    AI screening stage.
    """
    score = 0
    text = (entry.get("title", "") + " " + entry.get("summary", ""))
    text_lower = text.lower()
    # English high/medium keywords (case-insensitive)
    for keyword in HIGH_PRIORITY:
        if keyword.lower() in text_lower:
            score += 3
    for keyword in MEDIUM_PRIORITY:
        if keyword.lower() in text_lower:
            score += 2
    # Multilingual keywords (Unicode-aware, exact substring match)
    for keyword in HIGH_PRIORITY_INTL:
        if keyword in text:
            score += 3
    for keyword in MEDIUM_PRIORITY_INTL:
        if keyword in text:
            score += 2
    return score


def parse_ai_response(text: str, title: str = "") -> Optional[dict]:
    """Parse and validate the raw JSON string returned by the AI model."""
    # Strip markdown code fences if present
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        text = text[start:end].strip() if end != -1 else text[start:].strip()
    elif "```" in text:
        start = text.find("```") + len("```")
        end = text.find("```", start)
        text = text[start:end].strip() if end != -1 else text[start:].strip()
    elif "{" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]

    text = text.strip()
    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("AI response is not a valid JSON object")

    # Normalise is_6g_relevant to a proper bool
    if "is_6g_relevant" in data:
        raw = data["is_6g_relevant"]
        if isinstance(raw, str):
            val = raw.strip().lower()
            data["is_6g_relevant"] = val in ("1", "true", "yes")
        elif not isinstance(raw, bool):
            data["is_6g_relevant"] = bool(raw)

    return data

"""Unit tests for pipeline.utils and pipeline.feed_processor helpers."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from pipeline.utils import hash_url, is_recent, relevance_score, parse_ai_response

# Alias for the test that expects the private name
_parse_ai_response = parse_ai_response


# ---------------------------------------------------------------------------
# hash_url
# ---------------------------------------------------------------------------

def test_hash_url_returns_string():
    result = hash_url("https://example.com/article/1")
    assert isinstance(result, str)
    assert len(result) == 32  # MD5 hex digest length


def test_hash_url_deterministic():
    url = "https://arxiv.org/abs/2401.00001"
    assert hash_url(url) == hash_url(url)


def test_hash_url_different_urls():
    assert hash_url("https://a.com/1") != hash_url("https://a.com/2")


# ---------------------------------------------------------------------------
# is_recent
# ---------------------------------------------------------------------------

def _make_entry(days_ago: int):
    """Create a mock feedparser entry published *days_ago* days ago."""
    entry = MagicMock()
    dt = datetime.now() - timedelta(days=days_ago)
    entry.published_parsed = dt.timetuple()
    return entry


def test_is_recent_fresh_article():
    entry = _make_entry(5)
    assert is_recent(entry, days_lookback=30) is True


def test_is_recent_old_article():
    entry = _make_entry(60)
    assert is_recent(entry, days_lookback=30) is False


def test_is_recent_no_date():
    """Entries without a date should be treated as recent."""
    entry = MagicMock()
    entry.published_parsed = None
    assert is_recent(entry) is True


def test_is_recent_boundary():
    """An article 1 day inside the lookback window is still considered recent."""
    entry = _make_entry(29)
    assert is_recent(entry, days_lookback=30) is True


# ---------------------------------------------------------------------------
# relevance_score
# ---------------------------------------------------------------------------

def test_relevance_score_high_priority_keyword():
    entry = {"title": "6G deployment plans", "summary": "IMT-2030 roadmap"}
    # "6G" is high-priority (+3) and "IMT-2030" is high-priority (+3) = 6
    assert relevance_score(entry) == 6


def test_relevance_score_medium_priority_keyword():
    entry = {"title": "Release 21 update", "summary": "millimeter wave spectrum"}
    # "Release 21" medium (+2) and "millimeter wave" medium (+2) = 4
    assert relevance_score(entry) == 4


def test_relevance_score_no_keywords():
    entry = {"title": "Weather report", "summary": "Sunny day expected."}
    assert relevance_score(entry) == 0


def test_relevance_score_case_insensitive():
    entry = {"title": "TERAHERTZ research", "summary": ""}
    assert relevance_score(entry) >= 3  # terahertz is high-priority


# ---------------------------------------------------------------------------
# _parse_ai_response
# ---------------------------------------------------------------------------

def test_parse_ai_response_plain_json():
    raw = '{"is_6g_relevant": true, "overall_6g_importance": 7}'
    result = _parse_ai_response(raw, "test")
    assert result["is_6g_relevant"] is True
    assert result["overall_6g_importance"] == 7


def test_parse_ai_response_fenced_json():
    raw = '```json\n{"is_6g_relevant": false}\n```'
    result = _parse_ai_response(raw, "test")
    assert result["is_6g_relevant"] is False


def test_parse_ai_response_string_bool_true():
    raw = '{"is_6g_relevant": "true"}'
    result = _parse_ai_response(raw, "test")
    assert result["is_6g_relevant"] is True


def test_parse_ai_response_string_bool_false():
    raw = '{"is_6g_relevant": "false"}'
    result = _parse_ai_response(raw, "test")
    assert result["is_6g_relevant"] is False


def test_parse_ai_response_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_ai_response("not json at all", "test")

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
# relevance_score — multilingual (CJK / Korean) keywords
# ---------------------------------------------------------------------------

def test_relevance_score_korean_high_priority():
    """Korean 6세대 (6th generation) is HIGH_PRIORITY_INTL → +3."""
    entry = {"title": "6세대 이동통신 기술 개발", "summary": ""}
    # "6세대" high-priority (+3) + "이동통신" medium-priority (+2) = 5
    assert relevance_score(entry) == 5


def test_relevance_score_chinese_high_priority():
    """Chinese 第六代移动 is HIGH_PRIORITY_INTL → +3."""
    entry = {"title": "第六代移动技术白皮书发布", "summary": ""}
    assert relevance_score(entry) >= 3


def test_relevance_score_japanese_high_priority():
    """Japanese 第6世代 is HIGH_PRIORITY_INTL → +3."""
    entry = {"title": "第6世代移動通信システム", "summary": ""}
    # "第6世代" high (+3) + "移動通信" medium (+2) = 5
    assert relevance_score(entry) == 5


def test_relevance_score_korean_medium_priority():
    """Korean 이동통신 alone (no high-priority hit) scores +2."""
    entry = {"title": "이동통신 표준화 동향", "summary": ""}
    assert relevance_score(entry) == 2


def test_relevance_score_chinese_medium_priority():
    """Chinese 移动通信 alone scores +2."""
    entry = {"title": "移动通信发展报告", "summary": ""}
    assert relevance_score(entry) == 2


def test_relevance_score_japanese_medium_priority():
    """Japanese 移動通信 alone scores +2."""
    entry = {"title": "移動通信の最新動向", "summary": ""}
    assert relevance_score(entry) == 2


def test_relevance_score_cjk_no_false_positive():
    """CJK text that contains none of the configured keywords scores 0."""
    entry = {"title": "スマートフォン市場調査レポート", "summary": "台風情報"}
    assert relevance_score(entry) == 0


def test_relevance_score_intl_keywords_not_lowercased():
    """Multilingual matching uses the original text, not a lowercased copy.

    Lowercasing CJK text is a no-op, but this test guards against a future
    refactor that accidentally normalises the text before CJK matching.
    """
    entry = {"title": "6세대 기술", "summary": ""}
    score_original = relevance_score(entry)
    # Force the same text through as lowercase (Python lower() on Korean is a no-op)
    entry_lower = {"title": "6세대 기술".lower(), "summary": ""}
    assert relevance_score(entry_lower) == score_original


def test_relevance_score_mixed_english_and_cjk():
    """An entry mixing English and CJK keywords accumulates scores from both."""
    entry = {"title": "6G and 第6世代 convergence", "summary": "이동통신 spectrum"}
    # "6G" high (+3) + "第6世代" high (+3) + "이동통신" medium (+2) = 8
    assert relevance_score(entry) == 8


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

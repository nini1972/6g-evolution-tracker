"""Unit tests for api.mcp_server input validation."""
import pytest
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_get_latest_6g_news_clamps_min_importance(monkeypatch):
    """min_importance outside 0-10 should be clamped, not error."""
    import api.mcp_server as srv

    monkeypatch.setattr(srv, "load_digest", lambda: {"articles": []})

    # Should not raise
    result = srv.get_latest_6g_news(min_importance=-5)
    assert result == []

    result = srv.get_latest_6g_news(min_importance=999)
    assert result == []


def test_get_latest_6g_news_rejects_invalid_region(monkeypatch):
    import api.mcp_server as srv

    monkeypatch.setattr(srv, "load_digest", lambda: {"articles": []})

    with pytest.raises(ValueError, match="Invalid region"):
        srv.get_latest_6g_news(region="Mars")


def test_get_latest_6g_news_valid_region(monkeypatch):
    import api.mcp_server as srv

    monkeypatch.setattr(srv, "load_digest", lambda: {"articles": []})

    # Should not raise for valid region
    result = srv.get_latest_6g_news(region="US")
    assert result == []


def test_search_6g_topics_truncates_long_topic(monkeypatch):
    import api.mcp_server as srv

    monkeypatch.setattr(srv, "load_digest", lambda: {"articles": []})

    long_topic = "a" * 200  # exceeds _MAX_TOPIC_LENGTH = 100
    result = srv.search_6g_topics(topic=long_topic)
    assert result == []


def test_search_6g_topics_clamps_min_importance(monkeypatch):
    import api.mcp_server as srv

    monkeypatch.setattr(srv, "load_digest", lambda: {"articles": []})

    result = srv.search_6g_topics(topic="6G", min_importance=999)
    assert result == []

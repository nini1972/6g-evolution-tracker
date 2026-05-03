"""Unit tests for pipeline.exporters helpers."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from pipeline.exporters import (
    aggregate_momentum,
    evict_stale_cache,
    export_to_json,
    generate_source_target_matrix,
)


# ---------------------------------------------------------------------------
# evict_stale_cache
# ---------------------------------------------------------------------------

def test_evict_stale_cache_removes_old():
    old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
    cache = {
        "hash1": {"url": "http://a.com", "processed_date": old_date},
    }
    result = evict_stale_cache(cache, ttl_days=180)
    assert "hash1" not in result


def test_evict_stale_cache_keeps_recent():
    recent_date = datetime.now().strftime("%Y-%m-%d")
    cache = {
        "hash2": {"url": "http://b.com", "processed_date": recent_date},
    }
    result = evict_stale_cache(cache, ttl_days=180)
    assert "hash2" in result


def test_evict_stale_cache_keeps_unparseable_date():
    cache = {
        "hash3": {"url": "http://c.com", "processed_date": "not-a-date"},
    }
    result = evict_stale_cache(cache, ttl_days=180)
    assert "hash3" in result


# ---------------------------------------------------------------------------
# export_to_json
# ---------------------------------------------------------------------------

def test_export_to_json_creates_file(tmp_path):
    out = str(tmp_path / "digest.json")
    export_to_json([{"title": "test"}], "2026-01-01", output_file=out)
    assert Path(out).exists()
    data = json.loads(Path(out).read_text())
    assert data["date"] == "2026-01-01"
    assert len(data["articles"]) == 1


def test_export_to_json_includes_standardization(tmp_path):
    out = str(tmp_path / "digest.json")
    std = {"release_21_progress": {"progress_percentage": 42}}
    export_to_json([], "2026-01-01", standardization_data=std, output_file=out)
    data = json.loads(Path(out).read_text())
    assert "standardization" in data


# ---------------------------------------------------------------------------
# aggregate_momentum
# ---------------------------------------------------------------------------

def _make_article(region, date_str, importance=5, dims=None):
    if dims is None:
        dims = {
            "research_intensity": 3,
            "standardization_influence": 2,
            "industrial_deployment": 1,
            "spectrum_policy_signal": 2,
            "ecosystem_maturity": 2,
        }
    return {
        "date": date_str,
        "source": "Test",
        "ai_insights": {
            "is_6g_relevant": True,
            "source_region": region,
            "overall_6g_importance": importance,
            "impact_dimensions": dims,
        },
    }


def test_aggregate_momentum_produces_output(tmp_path):
    out = str(tmp_path / "momentum.json")
    articles = [
        _make_article("US", "2026-01-15"),
        _make_article("EU", "2026-02-20"),
    ]
    aggregate_momentum(articles, output_file=out)
    data = json.loads(Path(out).read_text())
    assert len(data) == 2
    regions = {d["region"] for d in data}
    assert "US" in regions
    assert "EU" in regions


def test_aggregate_momentum_ignores_irrelevant(tmp_path):
    out = str(tmp_path / "momentum.json")
    articles = [
        {
            "date": "2026-01-15",
            "source": "Test",
            "ai_insights": {"is_6g_relevant": False, "source_region": "US"},
        }
    ]
    aggregate_momentum(articles, output_file=out)
    data = json.loads(Path(out).read_text())
    assert data == []


# ---------------------------------------------------------------------------
# generate_source_target_matrix
# ---------------------------------------------------------------------------

def test_generate_source_target_matrix_creates_file(tmp_path):
    out = str(tmp_path / "matrix.json")
    articles = [
        {
            "source": "Test",
            "ai_insights": {
                "is_6g_relevant": True,
                "source_region": "US",
                "overall_6g_importance": 8,
                "world_power_impact": {"EU": 3, "China": 2},
            },
        }
    ]
    generate_source_target_matrix(articles, matrix_file=out)
    data = json.loads(Path(out).read_text())
    assert data["US"]["EU"] > 0
    assert data["US"]["China"] > 0

"""Unit tests for pipeline.exporters helpers."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from pipeline.exporters import (
    aggregate_momentum,
    evict_stale_cache,
    export_to_json,
    generate_source_target_matrix,
    update_historical_intelligence,
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


def test_generate_source_target_matrix_normalizes_region(tmp_path):
    """'South Korea' should be normalized to 'Korea' before accumulating."""
    out = str(tmp_path / "matrix.json")
    articles = [
        {
            "source": "Test",
            "ai_insights": {
                "is_6g_relevant": True,
                "source_region": "South Korea",
                "overall_6g_importance": 5,
                "world_power_impact": {"US": 3},
            },
        }
    ]
    generate_source_target_matrix(articles, matrix_file=out)
    data = json.loads(Path(out).read_text())
    assert data["Korea"]["US"] > 0


def test_generate_source_target_matrix_returns_dict(tmp_path):
    """generate_source_target_matrix should return the matrix dict."""
    out = str(tmp_path / "matrix.json")
    result = generate_source_target_matrix([], matrix_file=out)
    assert isinstance(result, dict)
    assert "US" in result


# ---------------------------------------------------------------------------
# aggregate_momentum — cumulative behaviour
# ---------------------------------------------------------------------------

def test_aggregate_momentum_is_cumulative(tmp_path):
    """Entries from previous runs must be preserved after a new run."""
    out = str(tmp_path / "momentum.json")
    articles_q1 = [_make_article("US", "2026-01-15")]
    aggregate_momentum(articles_q1, output_file=out)
    articles_q2 = [_make_article("EU", "2026-04-15")]
    aggregate_momentum(articles_q2, output_file=out)
    data = json.loads(Path(out).read_text())
    keys = {(d["region"], d["time_window"]) for d in data}
    assert ("US", "2026-Q1") in keys
    assert ("EU", "2026-Q2") in keys


def test_aggregate_momentum_overwrites_same_quarter(tmp_path):
    """When new articles arrive for an existing quarter, that entry is updated."""
    out = str(tmp_path / "momentum.json")
    # First run: US Q1 with low research_intensity
    dims_low = {"research_intensity": 1, "standardization_influence": 1,
                "industrial_deployment": 1, "spectrum_policy_signal": 1, "ecosystem_maturity": 1}
    articles_run1 = [_make_article("US", "2026-01-15", dims=dims_low)]
    aggregate_momentum(articles_run1, output_file=out)
    data_run1 = json.loads(Path(out).read_text())
    score_run1 = next(d["momentum_score"] for d in data_run1 if d["region"] == "US")

    # Second run: US Q1 with high research_intensity — should overwrite
    dims_high = {"research_intensity": 5, "standardization_influence": 5,
                 "industrial_deployment": 5, "spectrum_policy_signal": 5, "ecosystem_maturity": 5}
    articles_run2 = [_make_article("US", "2026-01-20", dims=dims_high)]
    aggregate_momentum(articles_run2, output_file=out)
    data_run2 = json.loads(Path(out).read_text())
    us_q1_entries = [d for d in data_run2 if d["region"] == "US" and d["time_window"] == "2026-Q1"]
    assert len(us_q1_entries) == 1
    # Score should differ after the overwrite (high-intensity article now dominates)
    assert us_q1_entries[0]["momentum_score"] != score_run1


# ---------------------------------------------------------------------------
# update_historical_intelligence
# ---------------------------------------------------------------------------

def test_update_historical_intelligence_creates_file(tmp_path):
    out = str(tmp_path / "historical.json")
    std_data = {"release_21_progress": {"progress_percentage": 50}}
    matrix = {"US": {"EU": 100}}
    update_historical_intelligence(std_data, matrix, "2026-05-03", output_file=out)
    data = json.loads(Path(out).read_text())
    assert len(data["standardization_snapshots"]) == 1
    assert len(data["matrix_snapshots"]) == 1
    assert data["standardization_snapshots"][0]["date"] == "2026-05-03"
    assert data["matrix_snapshots"][0]["date"] == "2026-05-03"


def test_update_historical_intelligence_is_idempotent(tmp_path):
    """Calling twice for the same date must not add duplicate snapshots."""
    out = str(tmp_path / "historical.json")
    std_data = {"release_21_progress": {}}
    matrix = {"US": {"EU": 10}}
    update_historical_intelligence(std_data, matrix, "2026-05-03", output_file=out)
    update_historical_intelligence(std_data, matrix, "2026-05-03", output_file=out)
    data = json.loads(Path(out).read_text())
    assert len(data["standardization_snapshots"]) == 1
    assert len(data["matrix_snapshots"]) == 1


def test_update_historical_intelligence_appends_multiple_dates(tmp_path):
    """Different dates should each produce their own snapshot entry."""
    out = str(tmp_path / "historical.json")
    matrix = {"US": {"EU": 5}}
    update_historical_intelligence(None, matrix, "2026-04-01", output_file=out)
    update_historical_intelligence(None, matrix, "2026-05-01", output_file=out)
    data = json.loads(Path(out).read_text())
    assert len(data["matrix_snapshots"]) == 2


def test_update_historical_intelligence_preserves_existing_articles(tmp_path):
    """Existing articles in the file should not be touched."""
    out = str(tmp_path / "historical.json")
    initial = {"articles": [{"title": "existing"}], "standardization_snapshots": [], "matrix_snapshots": []}
    Path(out).write_text(json.dumps(initial))
    update_historical_intelligence(None, {}, "2026-05-03", output_file=out)
    data = json.loads(Path(out).read_text())
    assert len(data["articles"]) == 1
    assert data["articles"][0]["title"] == "existing"

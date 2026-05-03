"""
Data exporters for the 6G Evolution Tracker.
Handles JSON export, momentum aggregation, and source→target matrix generation.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

# Cache eviction TTL: entries older than this many days are pruned
CACHE_TTL_DAYS = 180

# Recent articles rolling window parameters
RECENT_ARTICLES_TTL_DAYS = 90
MAX_RECENT_ARTICLES = 50

# Canonical region names used throughout the pipeline
CANONICAL_REGIONS = ["US", "EU", "China", "Japan", "Korea", "India"]

# Maps common AI-generated region name variants to their canonical forms
REGION_ALIASES: dict = {
    "south korea": "Korea",
    "republic of korea": "Korea",
    "s. korea": "Korea",
    "european union": "EU",
    "europe": "EU",
    "eu27": "EU",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "america": "US",
    "peoples republic of china": "China",
    "people's republic of china": "China",
    "prc": "China",
    "mainland china": "China",
}


def _normalize_region(raw: Optional[str], regions: list) -> Optional[str]:
    """Normalize an AI-generated region name to its canonical form.

    Returns the input unchanged if it is already canonical or cannot be mapped.
    """
    if not raw:
        return raw
    if raw in regions:
        return raw
    return REGION_ALIASES.get(raw.lower().strip(), raw)


def export_to_json(
    all_entries: list,
    date: str,
    standardization_data: Optional[dict] = None,
    output_file: str = "latest_digest.json",
) -> None:
    """Export all processed entries to a JSON file for the dashboard."""
    output_data: dict = {"date": date, "articles": all_entries}

    if standardization_data:
        output_data["standardization"] = standardization_data

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"📊 JSON data exported to {output_file}")
    except Exception as e:
        print(f"❌ JSON export failed: {e}")


def aggregate_momentum(
    articles: list,
    output_file: str = "momentum_data.json",
) -> None:
    """Compute region-specific 6G momentum per quarterly time window.

    Results are accumulated across pipeline runs: entries for past quarters are
    preserved while the current quarter's data is updated as new articles arrive.
    """
    regions = CANONICAL_REGIONS
    aggregation: dict = {}  # region -> quarter -> metrics

    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue

        src_region = _normalize_region(ai.get("source_region"), regions)
        if src_region not in regions:
            continue

        try:
            article_date = datetime.strptime(article["date"], "%Y-%m-%d")
            quarter = f"{article_date.year}-Q{(article_date.month - 1) // 3 + 1}"
        except Exception:
            quarter = "unknown"

        dimensions = ai.get("impact_dimensions", {})
        importance = ai.get("overall_6g_importance", 1)

        dim_values = [v for v in dimensions.values() if isinstance(v, (int, float))]
        article_momentum = sum(dim_values) / len(dim_values) if dim_values else 0

        aggregation.setdefault(src_region, {})
        aggregation[src_region].setdefault(
            quarter,
            {
                "research_intensity": [],
                "standardization_influence": [],
                "industrial_deployment": [],
                "spectrum_policy_signal": [],
                "ecosystem_maturity": [],
                "momenta": [],
            },
        )

        bucket = aggregation[src_region][quarter]
        bucket["momenta"].append((article_momentum, importance))
        for dim in bucket:
            if dim == "momenta":
                continue
            val = dimensions.get(dim, 0)
            bucket[dim].append((val, importance))

    # Compute weighted averages for the current run's articles
    new_data: dict = {}  # (region, quarter) -> entry
    for region, quarters in aggregation.items():
        for quarter, metrics in quarters.items():
            entry: dict = {"region": region, "time_window": quarter}

            if metrics["momenta"]:
                total = sum(m * w for m, w in metrics["momenta"])
                weight = sum(w for _, w in metrics["momenta"])
                entry["momentum_score"] = round(total / weight, 2)
            else:
                entry["momentum_score"] = 0

            for dim, values in metrics.items():
                if dim == "momenta":
                    continue
                if values:
                    total = sum(v * w for v, w in values)
                    weight = sum(w for _, w in values)
                    entry[dim] = round(total / weight, 2)
                else:
                    entry[dim] = 0

            new_data[(region, quarter)] = entry

    # Load existing persisted momentum entries so that past quarters are not lost
    existing_data: dict = {}  # (region, quarter) -> entry
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_list = json.load(f)
            if isinstance(existing_list, list):
                for e in existing_list:
                    existing_data[(e["region"], e["time_window"])] = e
    except Exception:
        pass

    # Merge: existing entries preserved; new entries overwrite for updated quarters
    merged = {**existing_data, **new_data}
    final_data = list(merged.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)

    print(
        f"📈 Region-specific momentum aggregated for {len(final_data)} "
        "region-quarter windows."
    )


def generate_source_target_matrix(
    articles: list,
    matrix_file: str = "source_target_matrix.json",
) -> dict:
    """Build / update the weighted Source→Target region influence matrix.

    Returns the updated matrix dict so callers can pass it to other exporters
    (e.g. ``update_historical_intelligence``) without re-reading the file.
    """
    regions = CANONICAL_REGIONS

    # Load previous matrix for cumulative influence
    try:
        with open(matrix_file, "r", encoding="utf-8") as f:
            matrix = json.load(f)
    except Exception:
        matrix = {src: {tgt: 0 for tgt in regions} for src in regions}

    # Ensure all canonical regions are present (handles first-run or legacy files)
    for src in regions:
        matrix.setdefault(src, {tgt: 0 for tgt in regions})
        for tgt in regions:
            matrix[src].setdefault(tgt, 0)

    region_article_counts: dict = {r: 0 for r in regions}

    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue

        source_region = _normalize_region(ai.get("source_region"), regions)
        if source_region not in regions:
            continue

        region_article_counts[source_region] += 1
        wp_impact = ai.get("world_power_impact", {})
        importance = ai.get("overall_6g_importance", 1)

        for target_region, score in wp_impact.items():
            norm_target = _normalize_region(target_region, regions)
            if norm_target in regions and score > 0:
                matrix[source_region][norm_target] += score * importance

    with open(matrix_file, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print("🌐 Weighted Source→Target matrix updated.")
    print("   Articles attributed per region this run:")
    for region, count in region_article_counts.items():
        print(f"     {region}: {count}")

    return matrix


def update_historical_intelligence(
    standardization_data: Optional[dict],
    matrix: dict,
    date: str,
    output_file: str = "historical_intelligence.json",
) -> None:
    """Append today's standardization snapshot and matrix snapshot to the
    historical intelligence file.

    The operation is idempotent: if a snapshot for *date* already exists it
    will not be duplicated.  The ``articles`` key already in the file is left
    untouched.
    """
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            hist: dict = json.load(f)
    except FileNotFoundError:
        hist = {"articles": [], "standardization_snapshots": [], "matrix_snapshots": []}
    except json.JSONDecodeError as e:
        print(f"⚠️  historical_intelligence.json is corrupt and will be reset: {e}")
        hist = {"articles": [], "standardization_snapshots": [], "matrix_snapshots": []}

    hist.setdefault("standardization_snapshots", [])
    hist.setdefault("matrix_snapshots", [])

    # Append standardization snapshot (idempotent by date)
    existing_std_dates = {s["date"] for s in hist["standardization_snapshots"]}
    if standardization_data and date not in existing_std_dates:
        hist["standardization_snapshots"].append(
            {"date": date, "data": standardization_data}
        )

    # Append matrix snapshot (idempotent by date)
    existing_matrix_dates = {s["date"] for s in hist["matrix_snapshots"]}
    if date not in existing_matrix_dates:
        hist["matrix_snapshots"].append({"date": date, "matrix": matrix})

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2)
        print(f"📚 Historical intelligence updated (date: {date}).")
    except Exception as e:
        print(f"❌ Failed to write historical intelligence: {e}")


def update_recent_articles(
    new_articles: list,
    output_file: str = "recent_articles.json",
) -> list:
    """
    Maintain a rolling window of recent articles (last RECENT_ARTICLES_TTL_DAYS days,
    capped at MAX_RECENT_ARTICLES entries).

    Merges *new_articles* into the persisted history, deduplicates by
    ``article_id``, prunes entries older than the TTL, and writes the result
    back to *output_file*.  Returns the updated list so callers can use it
    immediately (e.g. as a fallback for quiet cycles).
    """
    existing: list = []
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                existing = data
    except Exception:
        pass

    # Merge: newer articles (by article_id) take precedence
    by_id: dict = {a["article_id"]: a for a in existing if "article_id" in a}
    for article in new_articles:
        if "article_id" in article:
            by_id[article["article_id"]] = article

    # Prune entries older than the TTL
    cutoff = (
        datetime.now() - timedelta(days=RECENT_ARTICLES_TTL_DAYS)
    ).strftime("%Y-%m-%d")
    merged = [
        a for a in by_id.values() if a.get("date", "0000-00-00") >= cutoff
    ]

    # Keep only the most recent MAX_RECENT_ARTICLES
    merged.sort(key=lambda a: a.get("date", ""), reverse=True)
    merged = merged[:MAX_RECENT_ARTICLES]

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        print(f"📰 Recent articles history updated ({len(merged)} entries).")
    except Exception as e:
        print(f"❌ Failed to write recent articles history: {e}")

    return merged


def evict_stale_cache(cache: dict, ttl_days: int = CACHE_TTL_DAYS) -> dict:
    """
    Remove cache entries older than *ttl_days* days.
    Each cache entry is expected to have a ``processed_date`` field (YYYY-MM-DD).
    Returns the pruned cache dict.
    """
    cutoff = datetime.now().date()
    to_delete = []
    for url_hash, meta in cache.items():
        processed = meta.get("processed_date", "")
        try:
            entry_date = datetime.strptime(processed, "%Y-%m-%d").date()
            age = (cutoff - entry_date).days
            if age > ttl_days:
                to_delete.append(url_hash)
        except Exception:
            # Keep entries with unparseable dates
            pass

    for key in to_delete:
        del cache[key]

    if to_delete:
        print(f"🗑️  Evicted {len(to_delete)} stale cache entries (>{ttl_days} days old).")

    return cache

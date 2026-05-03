"""
Data exporters for the 6G Evolution Tracker.
Handles JSON export, momentum aggregation, and source→target matrix generation.
"""
import json
from datetime import datetime
from typing import Optional

# Cache eviction TTL: entries older than this many days are pruned
CACHE_TTL_DAYS = 180


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
    """Compute region-specific 6G momentum per quarterly time window."""
    regions = ["US", "EU", "China", "Japan", "Korea", "India"]
    aggregation: dict = {}  # region -> quarter -> metrics

    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue

        src_region = ai.get("source_region")
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

    # Compute weighted averages
    final_data = []
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

            final_data.append(entry)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)

    print(
        f"📈 Region-specific momentum aggregated for {len(final_data)} "
        "region-quarter windows."
    )


def generate_source_target_matrix(
    articles: list,
    matrix_file: str = "source_target_matrix.json",
) -> None:
    """Build / update the weighted Source→Target region influence matrix."""
    regions = ["US", "EU", "China", "Japan", "Korea", "India"]

    # Load previous matrix for cumulative influence
    try:
        with open(matrix_file, "r", encoding="utf-8") as f:
            matrix = json.load(f)
    except Exception:
        matrix = {src: {tgt: 0 for tgt in regions} for src in regions}

    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue

        source_region = ai.get("source_region")
        if source_region not in regions:
            continue

        wp_impact = ai.get("world_power_impact", {})
        importance = ai.get("overall_6g_importance", 1)

        for target_region, score in wp_impact.items():
            if target_region in regions and score > 0:
                matrix[source_region][target_region] += score * importance

    with open(matrix_file, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print("🌐 Weighted Source→Target matrix updated.")


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

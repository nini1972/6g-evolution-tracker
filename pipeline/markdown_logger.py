"""
Markdown logger for the 6G Evolution Tracker.
Writes relevant articles to a daily digest Markdown file.
"""
from datetime import datetime
from pathlib import Path

from pipeline.utils import clean_html


def log_to_markdown(source: str, entries: list, log_file: str, date: str) -> None:
    """Log relevant entries to a Markdown file with enhanced details and duplicate check."""
    existing_content = ""
    if Path(log_file).exists():
        with open(log_file, "r", encoding="utf-8") as f:
            existing_content = f.read()

    with open(log_file, "a", encoding="utf-8") as f:
        # Only write the source header if it's not already present for today
        header = f"## {source} — {date}"
        if header not in existing_content:
            f.write(f"{header}\n\n")

        for entry in entries:
            title = clean_html(entry.get("title", "No Title")) or "No Title"
            link = entry.get("link", "#")

            # Skip if this specific link is already in the file
            if link in existing_content:
                continue

            # Support both portable dicts ("score", "ai_insights") and raw feedparser entries
            score = entry.get("score", entry.get("_relevance_score", 0))
            ai_data = entry.get("ai_insights") or entry.get("_ai_insights")

            raw_summary = clean_html(entry.get("summary", ""))
            summary = raw_summary[:200]
            if len(raw_summary) > 200:
                summary += "..."

            if ai_data:
                summary = clean_html(ai_data.get("summary", summary)) or summary
                impact_score = ai_data.get(
                    "impact_score", ai_data.get("overall_6g_importance", "N/A")
                )
                score_str = f"{score} (AI Impact: {impact_score})"
            else:
                score_str = str(score)

            # Format published date if available
            pub_date = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                    pub_date = f" | 📅 {pub_date}"
                except Exception:
                    pass
            elif entry.get("date"):
                pub_date = f" | 📅 {entry['date']}"

            f.write(f"### [{title}]({link})\n")
            f.write(f"> **Relevance Score:** {score_str}{pub_date}\n\n")
            if summary:
                f.write(f"{summary}\n\n")
            f.write("---\n\n")
        f.write("\n")

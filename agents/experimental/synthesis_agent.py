from collections import Counter
from typing import Optional
import html
import structlog

logger = structlog.get_logger(__name__)


class SynthesisAgent:
    """
    Analyst agent that synthesizes gathered 6G signals into executive briefings.
    Identifies trends, regional shifts, and standardization bottlenecks.
    """

    def __init__(self, gemini_client=None, model: str = "gemini-2.5-flash"):
        self.client = gemini_client
        self.model = model

    def synthesize(
        self, articles: list, standardization_data: Optional[dict]
    ) -> str:
        """
        Generates a high-level HTML briefing from the intelligence gathered.
        Uses Gemini when available, with a deterministic data-driven fallback.
        """
        logger.info("synthesis_agent_starting_analysis", articles=len(articles))

        top_topics = self._get_top_topics(articles)
        std_progress = (
            standardization_data.get("release_21_progress", {})
            if standardization_data
            else {}
        )

        if self.client and articles:
            try:
                headlines = "\n".join(
                    f"- [{a.get('source', 'Source')} | {a.get('source_region', 'Other')}] {a.get('title', '')}"
                    for a in articles[:15]
                )
                prompt = (
                    "You are an executive 6G intelligence briefer. Write 3 concise paragraphs "
                    "(plain text separated by blank lines, no markdown headers or bullet lists) "
                    "summarizing: (1) Strategic Overview of top themes, (2) 3GPP Release 21 "
                    f"Standardization Velocity (currently {std_progress.get('progress_percentage', 0)}% "
                    f"across {std_progress.get('total_work_items', 0)} items), and (3) Geopolitical "
                    f"Regional Signals based on these recent articles:\n{headlines}"
                )
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt
                )
                if resp and resp.text:
                    paragraphs = [
                        p.strip()
                        for p in resp.text.strip().split("\n\n")
                        if p.strip()
                    ]
                    if len(paragraphs) >= 2:
                        titles = [
                            "Strategic Overview",
                            "Standardization Velocity",
                            "Geopolitical Signals",
                        ]
                        sections = []
                        for idx, p in enumerate(paragraphs[:3]):
                            heading = titles[idx] if idx < len(titles) else "Key Takeaway"
                            sections.append(
                                f"<h3>{heading}</h3><p>{html.escape(p)}</p>"
                            )
                        return f'<div class="briefing-card">{"".join(sections)}</div>'
            except Exception as e:
                logger.warning("synthesis_agent_llm_fallback", error=str(e))

        context = {
            "article_count": len(articles),
            "top_topics": top_topics,
            "std_progress": std_progress,
        }
        briefing = self._generate_simulated_briefing(context)
        logger.info("synthesis_agent_complete")
        return briefing

    def _get_top_topics(self, articles: list) -> list:
        all_topics = []
        for a in articles:
            ai = a.get("ai_insights")
            if isinstance(ai, dict) and ai.get("6g_topics"):
                all_topics.extend(ai["6g_topics"])
        if not all_topics:
            return ["AI-native RAN", "sub-THz", "ISAC", "NTN", "standardization"]
        return [t for t, _ in Counter(all_topics).most_common(5)]

    def _generate_simulated_briefing(self, context: dict) -> str:
        """Returns a structured HTML briefing grounded in current cycle metrics."""
        topics_str = html.escape(", ".join(context["top_topics"]))
        progress = context["std_progress"].get("progress_percentage", 0)
        total_wi = context["std_progress"].get("total_work_items", 0)
        article_count = context.get("article_count", 0)

        return f"""
        <div class="briefing-card">
            <h3>Strategic Overview</h3>
            <p>Across <strong>{article_count}</strong> tracked signals this cycle, the 6G landscape is increasingly shaped by <strong>{topics_str}</strong>.</p>
            <h3>Standardization Velocity</h3>
            <p>3GPP Release 21 progress currently stands at <strong>{progress}%</strong> ({total_wi} tracked work items across RAN &amp; SA working groups).</p>
            <h3>Geopolitical Signals</h3>
            <p>Cross-regional activity highlights intensifying collaboration across North America, Europe, and Asia-Pacific on AI-RAN architecture, spectrum allocation, and IMT-2030 timelines.</p>
        </div>
        """


if __name__ == "__main__":
    agent = SynthesisAgent(None)
    result = agent.synthesize([], {})
    print(result)

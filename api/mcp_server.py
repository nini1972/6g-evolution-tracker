"""
FastMCP Server for 6G Evolution Intelligence
Exposes 6G tracker data as MCP tools for AI agents (Claude, ChatGPT, etc.)
"""
from mcp.server.fastmcp import FastMCP
import json
from pathlib import Path
from typing import Optional, List
from collections import Counter

mcp = FastMCP("6g-intelligence-mcp", json_response=True)

# Constants
DIGEST_FILE = "latest_digest.json"

# === Helper Functions ===

def load_digest() -> dict:
    """Load the latest digest file with error handling"""
    try:
        with open(DIGEST_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"date": "", "articles": [], "standardization": {}}
    except json.JSONDecodeError:
        return {"date": "", "articles": [], "standardization": {}}

# === Core Tools ===

@mcp.tool()
def get_latest_6g_news(min_importance: int = 5, region: Optional[str] = None) -> List[dict]:
    """
    Get the latest 6G technology news and analysis.
    
    Args:
        min_importance: Minimum importance score (0-10). Default 5.
        region: Filter by region (US, China, EU, Japan, Korea, India). Optional.
    
    Returns:
        List of articles with AI-powered analysis including impact scores,
        regional influence, emerging concepts, and key evidence.
    """
    data = load_digest()
    
    articles = [
        a for a in data.get("articles", [])
        if a.get("ai_insights", {}).get("overall_6g_importance", 0) >= min_importance
    ]
    
    if region:
        articles = [a for a in articles if a.get("ai_insights", {}).get("source_region") == region]
    
    return articles


@mcp.tool()
def get_3gpp_release21_status() -> dict:
    """
    Get current status of 3GPP Release 21 (6G/IMT-2030) standardization.
    
    Returns:
        Progress percentage, completed work items, working group breakdown,
        and data source indicator (live/cached/sample).
    """
    data = load_digest()
    
    progress = data.get("standardization", {}).get("release_21_progress", {})
    
    return {
        "progress_percentage": progress.get("progress_percentage", 0),
        "completed": progress.get("completed", 0),
        "total_work_items": progress.get("total_work_items", 0),
        "in_progress": progress.get("in_progress", 0),
        "postponed": progress.get("postponed", 0),
        "last_updated": progress.get("last_updated", ""),
        "data_source": progress.get("data_source", "unknown"),
        "working_groups": progress.get("work_items_by_group", {})
    }


@mcp.tool()
def get_recent_3gpp_meetings(working_group: Optional[str] = None) -> List[dict]:
    """
    Get recent 3GPP standardization meeting reports with key agreements.
    
    Args:
        working_group: Filter by WG (RAN1, RAN2, SA2, SA6, etc.). Optional.
    
    Returns:
        List of meeting summaries with agreements, TDoc references, and sentiment.
    """
    data = load_digest()
    
    meetings = data.get("standardization", {}).get("recent_meetings", [])
    
    if working_group:
        meetings = [m for m in meetings if m.get("working_group") == working_group.upper()]
    
    return meetings


@mcp.tool()
def search_6g_topics(topic: str, min_importance: int = 0) -> List[dict]:
    """
    Search for articles covering specific 6G topics or technologies.
    
    Args:
        topic: Topic keyword (e.g., "AI-RAN", "ISAC", "NTN", "terahertz", "quantum", "sub-THz")
        min_importance: Minimum importance score (0-10). Default 0.
    
    Returns:
        Matching articles with relevance to the topic, ranked by importance.
    """
    topic_lower = topic.lower()
    
    data = load_digest()
    
    matching = []
    for article in data.get("articles", []):
        insights = article.get("ai_insights", {})
        
        # Check topic in multiple fields
        topics_str = json.dumps(insights.get("6g_topics", [])).lower()
        concepts_str = json.dumps(insights.get("emerging_concepts", [])).lower()
        title_str = article.get("title", "").lower()
        summary_str = article.get("summary", "").lower()
        
        if (topic_lower in topics_str or 
            topic_lower in concepts_str or 
            topic_lower in title_str or 
            topic_lower in summary_str):
            
            if insights.get("overall_6g_importance", 0) >= min_importance:
                matching.append(article)
    
    # Sort by importance
    matching.sort(key=lambda a: a.get("ai_insights", {}).get("overall_6g_importance", 0), reverse=True)
    
    return matching


@mcp.tool()
def analyze_regional_momentum() -> dict:
    """
    Analyze regional 6G momentum and leadership based on recent articles.
    
    Returns:
        Aggregated scores showing which regions (US, China, EU, Japan, Korea, India)
        are leading in 6G development, with total impact scores.
    """
    data = load_digest()
    
    regional_scores = {
        "US": 0, "China": 0, "EU": 0, 
        "Japan": 0, "Korea": 0, "India": 0
    }
    
    article_count = {"US": 0, "China": 0, "EU": 0, "Japan": 0, "Korea": 0, "India": 0}
    
    for article in data.get("articles", []):
        world_power = article.get("ai_insights", {}).get("world_power_impact", {})
        for region, score in world_power.items():
            if region in regional_scores:
                regional_scores[region] += score
                if score > 0:
                    article_count[region] += 1
    
    # Calculate averages
    regional_avg = {
        region: round(score / article_count[region], 2) if article_count[region] > 0 else 0
        for region, score in regional_scores.items()
    }
    
    leader = max(regional_scores, key=regional_scores.get) if any(regional_scores.values()) else "None"
    
    return {
        "date": data.get("date", ""),
        "total_scores": regional_scores,
        "average_impact_per_article": regional_avg,
        "article_mentions": article_count,
        "leader": leader
    }


@mcp.tool()
def get_emerging_6g_concepts(min_frequency: int = 2) -> List[dict]:
    """
    Get emerging 6G concepts and technologies mentioned across articles.
    
    Args:
        min_frequency: Minimum times a concept must appear to be included. Default 2.
    
    Returns:
        List of concepts with frequency counts, sorted by popularity.
    """
    data = load_digest()
    
    all_concepts = []
    for article in data.get("articles", []):
        concepts = article.get("ai_insights", {}).get("emerging_concepts", [])
        all_concepts.extend(concepts)
    
    concept_counts = Counter(all_concepts)
    
    filtered = [
        {"concept": concept, "frequency": count}
        for concept, count in concept_counts.most_common()
        if count >= min_frequency
    ]
    
    return filtered


# === Resources ===

@mcp.resource("digest://latest")
def get_latest_digest_resource():
    """
    Full latest 6G intelligence digest as a resource.
    Contains all articles, standardization data, and metadata.
    """
    try:
        with open(DIGEST_FILE) as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps({"date": "", "articles": [], "standardization": {}})
    except Exception:
        return json.dumps({"date": "", "articles": [], "standardization": {}})


# === Run Server ===

if __name__ == "__main__":
    mcp.run()

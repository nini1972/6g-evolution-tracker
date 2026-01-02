import feedparser
import json
import hashlib
import time
import requests
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import google.genai as genai
import os

# 🌐 RSS sources to monitor
# Note: Some feeds may be temporarily unavailable or have parsing issues
FEEDS = {
    "Ericsson": "https://www.ericsson.com/en/blog/rss",  # Fixed: add back '/rss' suffix
    "Thales": "https://www.thalesgroup.com/en/rss.xml",
    "MDPI Engineering": "https://www.mdpi.com/rss",  # Already working
    "Nokia": "https://www.nokia.com/newsroom/feed/en-us/",  # Fixed: use newsroom feed path
    "IEEE Spectrum": "https://spectrum.ieee.org/feeds/feed.rss",
    "ArXiv CS Networking": "http://export.arxiv.org/rss/cs.NI",
    # Additional sources can be added as they become available:
    # "3GPP News": "https://www.3gpp.org/news-events/3gpp-news/rss",
    # "Samsung Research": "https://research.samsung.com/blog/rss",
    # "ITU News": "https://www.itu.int/en/mediacentre/Pages/feeds.aspx",
}

# 🔄 User agents for rotating to bypass bot detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]

# 🔍 Keywords with weighted priorities
HIGH_PRIORITY = ["IMT-2030", "AI-native", "terahertz", "6G"]
MEDIUM_PRIORITY = ["radio spectrum", "6G architecture", "Release 21", "millimeter wave", "sub-THz"]

# ⚙️ Configuration
CACHE_FILE = "seen_articles.json"
DATE = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = f"6g_digest_{DATE}.md"
RELEVANCE_THRESHOLD = 2
DAYS_LOOKBACK = 30
MAX_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# 🤖 Gemini AI Config
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
model="gemini-3-flash-preview"
def get_ai_summary(title, summary, site_name):
    """Get an AI-powered summary and 6G impact score from Gemini."""
       
    prompt = f"""
    You are a 6G strategy and technology analyst.  Analyze the following article for its relevance to 6G (IMT‑2030) and produce a structured geopolitical intelligence profile.

    Source: {site_name}
    Title: {title}
    Snippet: {summary}
    
    Your tasks:
    
    1. Determine if this article is genuinely relevant to 6G. If not, return:
    {{
      "is_6g_relevant": false
    }}
    
    2. If relevant, perform a deep analysis using the following definitions:
    
    **Source Region (Emitter Region):**
    Identify the region the article originates from based on the publisher or organization.
    Use one of:  US, EU, China, Japan, Korea, India, Other.
    
    **6G Topics (choose all that apply):**
    sub-THz, AI-native RAN, semantic communications, ISAC, NTN, zero-energy devices,
    security & trust fabrics, network automation, sustainability, spectrum & policy,
    standardization, device ecosystem, cloud-edge integration, Open RAN, quantum-safe networking. 
    
    **Impact Dimensions (0–5 scale):**
    - research_intensity
    - standardization_influence
    - industrial_deployment
    - spectrum_policy_signal
    - ecosystem_maturity
    
    **Time Horizon:**
    - near-term (<= 2028)
    - mid-term (2028–2032)
    - long-term (>= 2032)
    
    **World Power Impact (0–5 scale):**
    US, EU, China, Japan, Korea, India. 
    Score based on how the article affects each region's 6G position.
    
    **Overall 6G Importance (0–10):**
    A single score representing the strategic weight of this article. 
    
    **Emerging Concepts:**
    Extract 1–5 novel or forward-looking ideas mentioned in the article.
    
    **Key Evidence:**
    Extract 1–5 short bullet points quoting or paraphrasing the most important factual signals.
    
    Return ONLY valid JSON in this exact format:
    
    {{
      "is_6g_relevant": true,
      "source_region": "",
      "summary": "",
      "overall_6g_importance": 0,
      "6g_topics": [],
      "impact_dimensions": {{
        "research_intensity": 0,
        "standardization_influence": 0,
        "industrial_deployment": 0,
        "spectrum_policy_signal":  0,
        "ecosystem_maturity": 0
      }},
      "time_horizon":  "",
      "world_power_impact": {{
        "US": 0,
        "EU": 0,
        "China": 0,
        "Japan": 0,
        "Korea": 0,
        "India": 0
      }},
      "emerging_concepts": [],
      "key_evidence": []
    }}
    
    Return ONLY JSON.  No commentary.  No markdown. 

    """
    
    try:
        response = client.models.generate_content(
        model=model,
        contents=prompt
        )
        text = response.text.strip()

        # Remove markdown code blocks if present
        if "```json" in text: 
            # Find first occurrence of ```json and first ``` after it
            start_marker = text.find("```json") + len("```json")
            end_marker = text.find("```", start_marker)
            if end_marker != -1:
                text = text[start_marker:end_marker].strip()
        elif "```" in text:
            # Find first occurrence of ``` and first ``` after it
            start_marker = text.find("```") + len("```")
            end_marker = text.find("```", start_marker)
            if end_marker != -1:
                text = text[start_marker:end_marker].strip()
        elif "{" in text:
            # Fallback if markdown is missing but JSON is present
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        # Clean up any whitespace issues
        text = text.strip()
            
        data = json.loads(text)

        # Validate the response structure
        if not isinstance(data, dict):
            raise ValueError("AI response is not a valid JSON object")
            
        # Ensure is_6g_relevant is a boolean
        if "is_6g_relevant" in data:
            if isinstance(data["is_6g_relevant"], str):
                val = data["is_6g_relevant"].strip().lower()
                # Handle common string representations of boolean values
                if val in ("0", "false", "no", ""):
                    data["is_6g_relevant"] = False
                elif val in ("1", "true", "yes"):
                    data["is_6g_relevant"] = True
                else:
                    # For any other string value, default to False for safety
                    # (instead of using Python's truthiness where non-empty strings are True)
                    data["is_6g_relevant"] = False
            elif not isinstance(data["is_6g_relevant"], bool):
                data["is_6g_relevant"] = bool(data["is_6g_relevant"])

        return data
    except Exception as e:
        print(f"  ⚠️ AI Summary failed for '{title[:30]}...': {e}")
        return None

def load_cache():
    """Load the cache of previously seen articles."""
    cache_path = Path(CACHE_FILE)
    if cache_path.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading cache: {e}")
            return {}
    return {}

def save_cache(cache):
    """Save the cache of seen articles."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving cache: {e}")

def hash_url(url):
    """Generate a hash for an article URL."""
    return hashlib.md5(url.encode()).hexdigest()

def is_recent(entry):
    """Check if an article was published in the last DAYS_LOOKBACK days."""
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        # If no date info, assume it's recent to avoid filtering out
        return True
    
    try:
        published_date = datetime(*entry.published_parsed[:6])
        cutoff_date = datetime.now() - timedelta(days=DAYS_LOOKBACK)
        return published_date >= cutoff_date
    except Exception:
        return True

def relevance_score(entry):
    """Calculate relevance score based on weighted keywords in title and summary."""
    score = 0
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    
    for keyword in HIGH_PRIORITY:
        if keyword.lower() in text:
            score += 3
    
    for keyword in MEDIUM_PRIORITY:
        if keyword.lower() in text:
            score += 2
    
    return score

def find_rss_feed(url, headers):
    """
    Try to find RSS/Atom feed URL from an HTML page.
    Looks for <link> tags with type="application/rss+xml" or "application/atom+xml"
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check if it's already XML/RSS
        content_type = response.headers.get('content-type', '').lower()
        if 'xml' in content_type or 'rss' in content_type:
            return url
        
        # Parse HTML to find RSS feed links
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for RSS/Atom feed links
        for link in soup.find_all('link', rel='alternate'):
            link_type = link.get('type', '')
            # Check for common RSS/Atom MIME types
            if link_type in ['application/rss+xml', 'application/atom+xml', 'application/xml', 'text/xml']:
                feed_url = link.get('href')
                if feed_url:
                    # Handle relative URLs - urljoin handles both absolute and relative URLs
                    return urljoin(url, feed_url)
        
        return None
    except Exception:
        # Silently fail if auto-detection doesn't work
        return None

def fetch_feed_with_retry(source, url, retries=MAX_RETRIES):
    """Fetch a feed with retry logic, auto-detection, and better error handling."""
    
    for attempt in range(retries):
        # Rotate user agent on each retry
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        try:
            # Try to auto-detect RSS feed if URL points to HTML (only on first attempt)
            if attempt == 0:
                detected_feed_url = find_rss_feed(url, headers)
                if detected_feed_url and detected_feed_url != url:
                    print(f"🔍 Auto-detected RSS feed for {source}: {detected_feed_url}")
                    url = detected_feed_url
            
            # Fetch with requests to have more control
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'html' in content_type and 'xml' not in content_type:
                print(f"⚠️ {source} returned HTML instead of RSS/XML")
                return None
            
            # Parse the feed
            feed = feedparser.parse(response.content)
            
            # Check for parsing errors
            if hasattr(feed, 'bozo') and feed.bozo:
                exception = feed.get('bozo_exception', 'Unknown error')
                
                if attempt < retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ Parsing error for {source}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Persistent parsing error for {source}: {exception}")
                    return None
            
            # Verify we got actual entries
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                if attempt < retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ No entries found for {source}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️ {source}: Feed parsed but contains no entries")
                    return None
            
            return feed
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                if attempt < retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ 403 Forbidden for {source}, rotating user agent and retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Failed to fetch {source}: 403 Forbidden after {retries} attempts with different user agents")
                    return None
            else:
                if attempt < retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ HTTP error {e.response.status_code} for {source}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Failed to fetch {source} after {retries} attempts: {e}")
                    return None
                    
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⚠️ Timeout fetching {source}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Failed to fetch {source}: Connection timeout after {retries} attempts")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⚠️ Network error fetching {source}: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Failed to fetch {source} after {retries} attempts: {e}")
                return None
                
        except Exception as e:
            print(f"❌ Unexpected error for {source}: {type(e).__name__}: {e}")
            return None
    
    return None

def fetch_feed_wrapper(args):
    """Wrapper function for parallel feed fetching."""
    source, url = args
    return source, fetch_feed_with_retry(source, url)

def log_to_markdown(source, entries):
    """Log relevant entries to markdown file with enhanced details and duplicate check."""
    existing_content = ""
    if Path(LOG_FILE).exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            existing_content = f.read()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        # Only write the source header if it's not already there for today
        header = f"## {source} — {DATE}"
        if header not in existing_content:
            f.write(f"{header}\n\n")
        
        for entry in entries:
            title = entry.get("title", "No Title")
            link = entry.get("link", "#")
            
            # Skip if this specific link is already in the file
            if link in existing_content:
                continue
                
            score = entry.get("_relevance_score", 0)
            ai_data = entry.get("_ai_insights")
            
            summary = entry.get("summary", "")[:200]
            if len(entry.get("summary", "")) > 200:
                summary += "..."
            
            if ai_data:
                summary = ai_data.get("summary", summary)
                impact_score = ai_data.get("impact_score", "N/A")
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
            
            f.write(f"### [{title}]({link})\n")
            f.write(f"> **Relevance Score:** {score_str}{pub_date}\n\n")
            if summary:
                f.write(f"{summary}\n\n")
            f.write("---\n\n")
        f.write("\n")

def export_to_json(all_entries):
    """Export all processed entries to a JSON file for the dashboard."""
    output_data = {
        "date": DATE,
        "articles": all_entries
    }
    try:
        with open("latest_digest.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"📊 JSON data exported to latest_digest.json")
    except Exception as e:
        print(f"❌ JSON export failed: {e}")

def aggregate_momentum(articles):
    """Compute region-specific 6G momentum per quarterly time window."""
    
    regions = ["US", "EU", "China", "Japan", "Korea", "India"]
    aggregation = {}   # region -> quarter -> metrics
    
    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue
        
        # Determine region of origin
        src_region = ai.get("source_region")
        if src_region not in regions:
            continue
        
        # Determine quarter
        try:
            article_date = datetime.strptime(article["date"], "%Y-%m-%d")
            quarter = f"{article_date.year}-Q{(article_date.month - 1) // 3 + 1}"
        except:
            quarter = "unknown"
        
        # Extract dimensions
        dimensions = ai.get("impact_dimensions", {})
        importance = ai.get("overall_6g_importance", 1)
        
        # Compute article momentum (average of dimensions)
        dim_values = [v for v in dimensions.values() if isinstance(v, (int, float))]
        article_momentum = sum(dim_values) / len(dim_values) if dim_values else 0
        
        # Initialize region + quarter bucket
        if src_region not in aggregation:
            aggregation[src_region] = {}
        if quarter not in aggregation[src_region]:
            aggregation[src_region][quarter] = {
                "research_intensity": [],
                "standardization_influence": [],
                "industrial_deployment": [],
                "spectrum_policy_signal": [],
                "ecosystem_maturity": [],
                "momenta": []
            }
        
        bucket = aggregation[src_region][quarter]
        
        # Store weighted values
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
            entry = {
                "region": region,
                "time_window": quarter
            }
            
            # Momentum score
            if metrics["momenta"]:
                total = sum(m * w for m, w in metrics["momenta"])
                weight = sum(w for m, w in metrics["momenta"])
                entry["momentum_score"] = round(total / weight, 2)
            else:
                entry["momentum_score"] = 0
            
            # Dimensions
            for dim, values in metrics.items():
                if dim == "momenta":
                    continue
                if values:
                    total = sum(v * w for v, w in values)
                    weight = sum(w for v, w in values)
                    entry[dim] = round(total / weight, 2)
                else:
                    entry[dim] = 0
            
            final_data.append(entry)
    
    # Save output
    with open("momentum_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)
    
    print(f"📈 Region-specific momentum aggregated for {len(final_data)} region-quarter windows.")

    except Exception as e:
        print(f"❌ Momentum aggregation failed: {e}")

def generate_source_target_matrix(articles):
    regions = ["US", "EU", "China", "Japan", "Korea", "India"]
    matrix = {src: {tgt: 0 for tgt in regions} for src in regions}

    for article in articles:
        ai = article.get("ai_insights")
        if not ai or not ai.get("is_6g_relevant"):
            continue

        source_region = ai.get("source_region", "Other")
        if source_region not in regions:
            continue

        wp_impact = ai.get("world_power_impact", {})

        for target_region, score in wp_impact.items():
            if target_region in regions and score > 0:
                matrix[source_region][target_region] += 1

    with open("source_target_matrix.json", "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print("🌐 Source→Target matrix generated.")

def main():
    print("🚀 6G Sentinel started its monthly sweep.\n")
    
    # AI Status Check
    if not model:
        print("⚠️  Warning: GOOGLE_API_KEY not found in environment.")
        print("   AI insights and Rigorous Filtering are DISABLED.")
    else:
        print("🤖 Gemini AI Intelligence is ACTIVE. (Model: gemini-3-flash)")
    print()
    # Load cache
    cache = load_cache()
    new_articles_count = 0
    
    # Fetch feeds in parallel
    print(f"📡 Fetching {len(FEEDS)} RSS feeds in parallel...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {executor.submit(fetch_feed_wrapper, (source, url)): source 
                           for source, url in FEEDS.items()}
        
        feeds_data = {}
        for future in as_completed(future_to_source):
            try:
                source, feed = future.result()
                if feed and hasattr(feed, 'entries'):
                    feeds_data[source] = feed
                    print(f"✓ {source}: {len(feed.entries)} total entries fetched")
                else:
                    print(f"✗ {source}: Failed to fetch")
            except Exception as e:
                print(f"❌ Error fetching source: {e}")
    
    print()
    
    # Process each feed
    all_processed_entries = []
    for source, feed in feeds_data.items():
        relevant_entries = []
        
        for entry in feed.entries:
            # Check if article was already seen
            article_url = entry.get("link", "")
            if not article_url:
                continue
            
            url_hash = hash_url(article_url)
            if url_hash in cache:
                continue
            
            # Check if article is recent
            if not is_recent(entry):
                continue
            
            # Calculate relevance score
            score = relevance_score(entry)
            if score >= RELEVANCE_THRESHOLD:
                # Try to get AI summary and relevance check
                print(f"  ✨ Generating AI insights for: {entry.get('title')[:50]}...")
                ai_insights = get_ai_summary(entry.get("title", ""), entry.get("summary", ""), source)
                
                # Check for AI rejection
                if ai_insights and not ai_insights.get("is_6g_relevant", True):
                    print(f"  🚫 AI rejected as irrelevant: {entry.get('title')[:50]}")
                    continue
                
                # Map AI overall_6g_importance to impact_score for the dashboard
                if ai_insights:
                    ai_insights["impact_score"] = ai_insights.get("overall_6g_importance", 0)
                
                entry["_relevance_score"] = score
                entry["_ai_insights"] = ai_insights
                
                relevant_entries.append(entry)
                cache[url_hash] = {
                    "url": article_url,
                    "title": entry.get("title", ""),
                    "processed_date": DATE
                }
                new_articles_count += 1
        
        # Log and display results
        if relevant_entries:
            # Sort by relevance score (highest first)
            relevant_entries.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)
            
            print(f"🔎 {source}: {len(relevant_entries)} new relevant updates found.")
            for entry in relevant_entries:
                score = entry.get("_relevance_score", 0)
                print(f"  • [{score}] {entry.get('title')}")
                print(f"    {entry.get('link')}")
            print()
            
            log_to_markdown(source, relevant_entries)
            
            # Prepare for JSON export
            for entry in relevant_entries:
                ai = entry.get("_ai_insights")
                all_processed_entries.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "score": entry.get("_relevance_score", 0),
                    "ai_insights": ai,
                    "source_region": ai.get("source_region", "Other") if ai else "Other",
                    "summary": entry.get("summary", ""),
                    "date": datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d") if hasattr(entry, "published_parsed") and entry.published_parsed else DATE
                })
        else:
            print(f"📭 {source}: No new keyword-matching updates this cycle.\n")
    
    # Export for dashboard
    if all_processed_entries:
        export_to_json(all_processed_entries)
        # Deep Analysis Aggregation
        generate_source_target_matrix(all_processed_entries)
        aggregate_momentum(all_processed_entries)
    
    # Save cache
    save_cache(cache)
    
    print(f"✅ 6G Sentinel completed its sweep.")
    print(f"📊 Total new articles processed: {new_articles_count}")
    print(f"💾 Cache updated with {len(cache)} unique articles.")
    print("🔮 The future is still under construction.")

if __name__ == "__main__":
    main()


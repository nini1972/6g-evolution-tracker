import feedparser
import json
import hashlib
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 🌐 RSS sources to monitor
# Note: Some feeds may be temporarily unavailable or have parsing issues
FEEDS = {
    "Ericsson": "https://www.ericsson.com/en/blog/rss",
    "Thales": "https://www.thalesgroup.com/en/rss.xml",
    "MDPI Engineering": "https://www.mdpi.com/rss/journal/engineering",
    "Nokia": "https://www.nokia.com/about-us/news/rss/",
    "IEEE Spectrum": "https://spectrum.ieee.org/feeds/feed.rss",
    "ArXiv CS Networking": "http://export.arxiv.org/rss/cs.NI",
    # Additional sources can be added as they become available:
    # "3GPP News": "https://www.3gpp.org/news-events/3gpp-news/rss",
    # "Samsung Research": "https://research.samsung.com/blog/rss",
    # "ITU News": "https://www.itu.int/en/mediacentre/Pages/feeds.aspx",
}

# 🔍 Keywords with weighted priorities
HIGH_PRIORITY = ["IMT-2030", "AI-native", "terahertz"]
MEDIUM_PRIORITY = ["spectrum", "6G architecture", "Release 21"]

# ⚙️ Configuration
CACHE_FILE = "seen_articles.json"
DATE = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = f"6g_digest_{DATE}.md"
RELEVANCE_THRESHOLD = 2
DAYS_LOOKBACK = 30
MAX_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

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

def fetch_feed_with_retry(source, url, retries=MAX_RETRIES):
    """Fetch a feed with retry logic and exponential backoff."""
    for attempt in range(retries):
        try:
            feed = feedparser.parse(url)
            
            # Check for parsing errors
            if hasattr(feed, 'bozo') and feed.bozo:
                if attempt < retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ Parsing error for {source}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Persistent parsing error for {source}: {feed.get('bozo_exception', 'Unknown error')}")
                    return None
            
            return feed
            
        except Exception as e:
            if attempt < retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⚠️ Error fetching {source}: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to fetch {source} after {retries} attempts: {e}")
                return None
    
    return None

def fetch_feed_wrapper(args):
    """Wrapper function for parallel feed fetching."""
    source, url = args
    return source, fetch_feed_with_retry(source, url)

def log_to_markdown(source, entries):
    """Log relevant entries to markdown file with enhanced details."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"## {source} — {DATE}\n\n")
        for entry in entries:
            title = entry.get("title", "No Title")
            link = entry.get("link", "#")
            score = entry.get("_relevance_score", 0)
            summary = entry.get("summary", "")[:200]
            if len(entry.get("summary", "")) > 200:
                summary += "..."
            
            # Format published date if available
            pub_date = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                    pub_date = f" | 📅 {pub_date}"
                except Exception:
                    pass
            
            f.write(f"### [{title}]({link})\n")
            f.write(f"**Relevance Score:** {score}{pub_date}\n\n")
            if summary:
                f.write(f"{summary}\n\n")
            f.write("---\n\n")
        f.write("\n")

def main():
    print("🚀 6G Sentinel started its monthly sweep.\n")
    
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
            source, feed = future.result()
            if feed and hasattr(feed, 'entries'):
                feeds_data[source] = feed
                print(f"✓ {source}: {len(feed.entries)} total entries fetched")
            else:
                print(f"✗ {source}: Failed to fetch")
    
    print()
    
    # Process each feed
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
                entry["_relevance_score"] = score
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
        else:
            print(f"📭 {source}: No new keyword-matching updates this cycle.\n")
    
    # Save cache
    save_cache(cache)
    
    print(f"✅ 6G Sentinel completed its sweep.")
    print(f"📊 Total new articles processed: {new_articles_count}")
    print(f"💾 Cache updated with {len(cache)} unique articles.")
    print("🔮 The future is still under construction.")

if __name__ == "__main__":
    main()

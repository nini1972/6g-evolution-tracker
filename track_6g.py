import feedparser
from datetime import datetime

# 🌐 RSS sources to monitor
FEEDS = {
    "Ericsson": "https://www.ericsson.com/en/blog/rss",
    "Thales": "https://www.thalesgroup.com/en/rss.xml",
    "MDPI Engineering": "https://www.mdpi.com/rss/journal/engineering"
}

# 🔍 Keywords to filter relevant updates
KEYWORDS = ["IMT-2030", "AI-native", "Release 21", "spectrum", "terahertz", "6G architecture"]

# 📁 Markdown log file
DATE = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = f"6g_digest_{DATE}.md"

def contains_keywords(text):
    return any(keyword.lower() in text.lower() for keyword in KEYWORDS)

def fetch_feed(url):
    try:
        return feedparser.parse(url)
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def log_to_markdown(source, entries):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"## {source} — {DATE}\n")
        for entry in entries:
            title = entry.get("title", "No Title")
            link = entry.get("link", "#")
            f.write(f"- [{title}]({link})\n")
        f.write("\n")

def main():
    print("🚀 6G Sentinel started its monthly sweep.\n")
    for source, url in FEEDS.items():
        feed = fetch_feed(url)
        if not feed or not feed.entries:
            continue

        relevant_entries = [entry for entry in feed.entries if contains_keywords(entry.get("title", ""))]
        if relevant_entries:
            print(f"🔎 {source}: {len(relevant_entries)} relevant updates found.")
            for entry in relevant_entries:
                print(f"- {entry.get('title')}\n  {entry.get('link')}\n")
            log_to_markdown(source, relevant_entries)
        else:
            print(f"📭 {source}: No keyword-matching updates this cycle.\n")

    print("✅ 6G Sentinel completed its monthly sweep. The future is still under construction.")

if __name__ == "__main__":
    main()

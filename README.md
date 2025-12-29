# 6G Evolution Tracker

This repository is dedicated to tracking the evolution of 6G technologies.  
A scheduled Python script runs monthly using GitHub Actions to monitor news, publications, and updates related to 6G.

## 🚀 Features

### Intelligent Tracking
- **🎯 Weighted Keyword Scoring**: Articles are scored based on relevance with high-priority (weight 3) and medium-priority (weight 2) keywords
- **📅 Date Filtering**: Only processes articles from the last 30 days to focus on recent developments
- **🚫 Duplicate Prevention**: Maintains a cache (`seen_articles.json`) to prevent reprocessing of articles

### Performance Enhancements
- **⚡ Parallel Feed Fetching**: Uses concurrent processing to fetch multiple RSS feeds simultaneously (5 workers)
- **🔄 Retry Logic**: Implements exponential backoff with up to 3 retry attempts for transient failures
- **🛡️ Error Handling**: Robust error handling with feed validation and informative error messages

### Comprehensive Coverage
Monitors industry-leading 6G sources including:
- Ericsson Blog
- Thales Group
- MDPI Engineering
- Nokia
- IEEE Spectrum
- ArXiv (Computer Science - Networking)

Additional sources can be easily added by updating the `FEEDS` dictionary in the script.

### Enhanced Reporting
- **📊 Relevance Scores**: Each article includes a calculated relevance score
- **📝 Article Summaries**: Shows first 200 characters of article content
- **📅 Publication Dates**: Displays when articles were published
- **🎨 Improved Formatting**: Better markdown formatting for readability

## Workflow

- **Language:** Python
- **Schedule:** Monthly (via GitHub Actions)
- **Dependencies:**  
  - [feedparser](https://pypi.org/project/feedparser/)  
  - [requests](https://pypi.org/project/requests/)

## How it works

The main script `track_6g.py` performs the following:

1. **Loads Cache**: Reads `seen_articles.json` to identify previously processed articles
2. **Fetches Feeds**: Concurrently fetches RSS feeds from all configured sources
3. **Filters Articles**: 
   - Checks if article was previously seen
   - Verifies article is from the last 30 days
   - Calculates relevance score based on weighted keywords
   - Only processes articles with score ≥ 2
4. **Generates Report**: Creates a markdown digest file with enhanced details
5. **Updates Cache**: Saves processed article URLs to prevent future duplicates

### Keyword Scoring System

**High Priority Keywords** (weight: 3):
- IMT-2030
- AI-native
- terahertz

**Medium Priority Keywords** (weight: 2):
- spectrum
- 6G architecture
- Release 21

Articles must score at least 2 points to be included in the digest.

## Customization

To track additional sources, update the `FEEDS` dictionary in `track_6g.py`.  
You can also adjust keyword priorities, relevance thresholds, and date filtering in the configuration section.

## Getting Started

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. Run the script:
    ```bash
    python track_6g.py
    ```

The workflow will run automatically every month, and all logs are available in the GitHub Actions tab.

## Cache Management

The `seen_articles.json` file maintains a history of processed articles. This file:
- Is automatically created on first run
- Prevents duplicate processing across runs
- Is excluded from version control (via `.gitignore`)
- Can be safely deleted to reprocess all articles

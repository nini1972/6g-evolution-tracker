# 6G Evolution Tracker

This repository is dedicated to tracking the evolution of 6G technologies.  
A scheduled Python script runs monthly using GitHub Actions to monitor news, publications, and updates related to 6G, providing AI-powered insights and a premium web dashboard.

## 🚀 Features

### 🤖 AI-Powered Intelligence
- **Deep Intelligence Analysis**: Uses `gemini-3-flash-preview` to perform a 15-point strategic analysis per article.
- **World Power Mapping**: Tracks 6G momentum across the US, EU, China, Japan, Korea, and India.
- **Quarterly Momentum Tracking**: Aggregates data into stable quarterly trends to visualize technical and geopolitical shifts.
- **Interactive Dashboard**: Modern glassmorphism UI showing AI insights and impact scores.
- **Automated Workflow**: Fully automated monthly tracking via GitHub Actions.
- **🔍 Dynamic Filtering**: Instantly search by keyword or filter by source (Ericsson, Nokia, etc.).
- **📱 Responsive Design**: Optimized for both desktop and mobile viewing.

### 📊 3GPP Standardization Tracking (NEW)

The tracker monitors official 3GPP technical standardization activities:

- **Release 21 Progress**: Tracks completion percentage of 6G Work Items
- **Working Group Breakdown**: Monitor progress by RAN1, RAN2, SA2, etc.
- **Recent Meeting Reports**: Automated extraction of key agreements from 3GPP meetings
- **TDoc Reference Tracking**: Links to technical documents and proposals
- **Sentiment Analysis**: Positive, mixed, or negative signals from standardization activities
- **Quantitative Metrics**: Move beyond qualitative news to track actual standardization milestones

#### Data Sources
- **Live Data**: 3GPP FTP Server (https://www.3gpp.org/ftp/) accessed via HTTP
- **Fallback**: Sample data is used when FTP access is unavailable or restricted (403 errors)
- **Cache**: Downloaded data is cached for 24 hours to reduce server load

The dashboard displays a badge indicating whether data is from live sources, cached, or sample data.

#### Future Enhancement
The codebase includes `mcp-3gpp-ftp>=0.1.8` as a dependency for potential future integration with the MCP 3GPP FTP Explorer server, which would provide enhanced access to 3GPP technical documents including ZIP TDoc extraction and advanced Excel/Word parsing capabilities.

### Performance & Reliability
- **⚡ Parallel Fetching**: Concurrently fetches multiple RSS feeds simultaneously.
- **🚫 Duplicate Prevention**: Prevents reprocessing of articles and avoids double-logging in reports.
- **🔄 GitHub Actions**: Fully automated monthly runs with state persistence via cache.
- **🔐 Graceful Fallbacks**: Handles 3GPP FTP access restrictions gracefully

## Workflow

- **Language:** Python
- **AI Model:** Gemini 3 Flash
- **Dashboard:** Vanilla JS + CSS (Glassmorphism)
- **Schedule:** Monthly (via GitHub Actions)

## Setup & Configuration

### 🔑 API Key
To enable the AI summarization, add a `GOOGLE_API_KEY` to your GitHub Repository Secrets:
1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Add it to **Settings > Secrets and variables > Actions** as `GOOGLE_API_KEY`.

### 🖥️ Local Development
1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. Run the tracker:
    ```bash
    python track_6g.py
    ```

The dashboard can be viewed by opening `dashboard/index.html` (Note: for local view, ensure `latest_digest.json` is generated).

### 📦 Dependencies

Key dependencies:
- `google-genai` - AI-powered article analysis
- `mcp-3gpp-ftp>=0.1.8` - Specialized 3GPP FTP client for standardization data
- `httpx` - HTTP client with HTTP/2 support
- `playwright` - Browser automation for dynamic content
- `openpyxl` - Excel file parsing (fallback for Work Plan parsing)
- `beautifulsoup4` - HTML parsing
- `feedparser` - RSS feed parsing
- `structlog` - Structured logging

## 🤖 AI Agent Integration (MCP Server)

The 6G Evolution Tracker exposes its intelligence via a FastMCP server, allowing AI agents (Claude, ChatGPT, LangChain, etc.) to query 6G data programmatically.

### Available MCP Tools

1. **`get_latest_6g_news`** - Get recent 6G news with AI analysis
   - Parameters: `min_importance` (0-10), `region` (US/China/EU/Japan/Korea/India)
   
2. **`get_3gpp_release21_status`** - Get 3GPP Release 21 standardization progress
   - Returns: Progress percentage, work items, data source (live/cached/sample)
   
3. **`get_recent_3gpp_meetings`** - Get recent meeting summaries with agreements
   - Parameters: `working_group` (RAN1/RAN2/SA2/etc., optional)
   
4. **`search_6g_topics`** - Search for specific 6G topics/technologies
   - Parameters: `topic` (e.g., "AI-RAN", "ISAC", "terahertz"), `min_importance` (0-10)
   
5. **`analyze_regional_momentum`** - Analyze which regions are leading in 6G
   - Returns: Regional scores, average impact, leader
   
6. **`get_emerging_6g_concepts`** - Get trending 6G concepts
   - Parameters: `min_frequency` (minimum mentions, default 2)

### Usage with Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "6g-intelligence": {
      "command": "python",
      "args": ["/path/to/6g-evolution-tracker/api/mcp_server.py"]
    }
  }
}
```

Then in Claude:
```
"What's the current status of 3GPP Release 21?"
"Search for articles about AI-RAN"
"Which region is leading in 6G development?"
```

### Running the MCP Server Standalone

```bash
cd 6g-evolution-tracker
python api/mcp_server.py
```

The server runs on stdio transport by default, compatible with MCP protocol clients.

### Example Python Client

See `examples/mcp_client_example.py` for a Python example:

```bash
python examples/mcp_client_example.py
```

## Cache Management

The `seen_articles.json` file maintains a history of processed articles to prevent duplicates. This is automatically handled by the GitHub Action.

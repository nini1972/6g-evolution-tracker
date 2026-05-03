# 6G Evolution Tracker

This repository tracks the global evolution of 6G technologies using automated data collection, AI-powered analysis, and a modern interactive dashboard.
A scheduled Python workflow runs monthly via GitHub Actions to gather signals from industry, academia, and standards bodies — transforming them into geopolitical and technical intelligence.

## 🚀 Features

### 🤖 AI-Powered Intelligence Engine

**Deep Article Analysis**
Each article is processed using Gemini 3 Flash, producing a structured 6G intelligence profile including:

- 6G topic classification
- Impact dimensions (research, standardization, deployment, spectrum, ecosystem)
- Time horizon (near/mid/long-term)
- World power impact (US, EU, China, Japan, Korea, India)
- Emerging concepts and key evidence extraction
- Overall 6G importance score
- Source region (emitter)

**Geopolitical Mapping**
Tracks how different world powers influence and reference each other in 6G developments.

- **Source → Target Region Influence Matrix** — A 6×6 matrix showing which regions write about which other regions, revealing cross-regional influence patterns.
- **Quarterly Momentum Tracking** — Normalized, weighted momentum scores per region and quarter, based on AI-derived impact dimensions.

### 📊 3GPP Standardization Tracking

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

### 📊 Dashboard

A modern, responsive dashboard built with vanilla JS + CSS (glassmorphism style), featuring:

- AI-generated summaries and impact scores
- Dynamic search and source filtering
- Quarterly momentum data (normalized 0–5 scale)
- Source → Target Region Influence Map (heatmap)
- Automatic updates via GitHub Pages deployment

All data is generated automatically and published to the `gh-pages` branch.

### Performance & Reliability

- **⚡ Parallel Fetching**: Concurrently fetches multiple RSS feeds simultaneously.
- **🔄 Hybrid Strategy**: Tries fast HTTP first, falls back to Playwright browser automation for dynamic content.
- **🚫 Duplicate Prevention**: Prevents reprocessing of articles and avoids double-logging in reports.
- **🔐 Graceful Fallbacks**: Handles 3GPP FTP access restrictions gracefully.

## ⚙️ Workflow

- **Language:** Python
- **AI Model:** Gemini 3 Flash
- **Dashboard:** HTML + JS + CSS (Glassmorphism)
- **Automation:** GitHub Actions
- **Schedule:** Monthly (1st of each month)

The workflow:
1. Fetches RSS feeds in parallel
2. Filters articles using keyword relevance
3. Performs deep AI analysis
4. Generates output files (see [Output Files](#-output-files) below)
5. Updates the dashboard
6. Commits results back to the repository
7. Deploys the dashboard to GitHub Pages

## 🔑 Setup & Configuration

### API Key

To enable AI analysis, add a `GOOGLE_API_KEY` to your repository secrets:

1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Add it under: **Settings → Secrets and variables → Actions → New repository secret** as `GOOGLE_API_KEY`.

### 🖥️ Local Development

```bash
pip install -r requirements.txt
python track_6g.py
```

Then open `dashboard/index.html` (ensure `latest_digest.json` exists).

### 📦 Dependencies

Key dependencies:
- `google-genai` — AI-powered article analysis
- `mcp-3gpp-ftp>=0.1.8` — Specialized 3GPP FTP client for standardization data
- `httpx` — HTTP client with HTTP/2 support
- `playwright` — Browser automation for dynamic content
- `openpyxl` — Excel file parsing (fallback for Work Plan parsing)
- `beautifulsoup4` — HTML parsing
- `feedparser` — RSS feed parsing
- `structlog` — Structured logging

## 📁 Project Structure

```
6g-evolution-tracker/
├── track_6g.py              # Entry point — orchestrates the monthly run
├── config/                  # FEEDS list, AI prompt template
├── pipeline/                # Feed processor, exporters, markdown logger, utilities
├── fetchers/                # Hybrid HTTP + Playwright RSS fetchers
├── parsers/                 # Content parsers
├── api/                     # FastMCP server (mcp_server.py)
├── agents/
│   └── experimental/        # Prototype discovery agents (not yet wired in)
├── examples/                # MCP client usage examples
├── tests/                   # Unit tests (pytest)
├── dashboard/               # Vanilla JS dashboard (deployed to GitHub Pages)
├── digests/                 # Monthly AI digest Markdown files (auto-generated)
├── latest_digest.json       # All processed articles + AI insights
├── momentum_data.json       # Quarterly momentum scores per region
├── source_target_matrix.json# Source → target region influence map
├── historical_intelligence.json # Long-term trend data
└── seen_articles.json       # Cache of processed article hashes
```

## 📄 Output Files

| File | Purpose |
|---|---|
| `latest_digest.json` | All processed articles + AI insights |
| `momentum_data.json` | Quarterly momentum scores per region |
| `source_target_matrix.json` | Source → target region influence map |
| `historical_intelligence.json` | Long-term standardization & trend data |
| `digests/6g_digest_YYYY-MM-DD.md` | Human-readable monthly digest |
| `seen_articles.json` | Cache of processed articles (deduplication) |

All files are committed automatically when new data is found.

## 🤖 AI Agent Integration (MCP Server)

The 6G Evolution Tracker exposes its intelligence via a FastMCP server, allowing AI agents (Claude, ChatGPT, LangChain, etc.) to query 6G data programmatically.

### Available MCP Tools

1. **`get_latest_6g_news`** — Get recent 6G news with AI analysis
   - Parameters: `min_importance` (0–10), `region` (US/China/EU/Japan/Korea/India)

2. **`get_3gpp_release21_status`** — Get 3GPP Release 21 standardization progress
   - Returns: Progress percentage, work items, data source (live/cached/sample)

3. **`get_recent_3gpp_meetings`** — Get recent meeting summaries with agreements
   - Parameters: `working_group` (RAN1/RAN2/SA2/etc., optional)

4. **`search_6g_topics`** — Search for specific 6G topics/technologies
   - Parameters: `topic` (e.g., "AI-RAN", "ISAC", "terahertz"), `min_importance` (0–10)

5. **`analyze_regional_momentum`** — Analyze which regions are leading in 6G
   - Returns: Regional scores, average impact, leader

6. **`get_emerging_6g_concepts`** — Get trending 6G concepts
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

Then ask Claude:
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

See `examples/mcp_client_example.py`:

```bash
python examples/mcp_client_example.py
```

## 🗂 Cache Management

The `seen_articles.json` file maintains a history of processed articles to prevent duplicates. It is automatically cached and restored by GitHub Actions.

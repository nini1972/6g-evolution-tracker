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
- **Release 21 Progress**: Tracks completion percentage of 6G Work Items
- **Working Group Breakdown**: Monitor progress by RAN1, RAN2, SA2, etc.
- **Recent Meeting Reports**: Automated extraction of key agreements from 3GPP meetings
- **TDoc Reference Tracking**: Links to technical documents and proposals
- **Sentiment Analysis**: Positive, mixed, or negative signals from standardization activities
- **Quantitative Metrics**: Move beyond qualitative news to track actual standardization milestones

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

## Cache Management

The `seen_articles.json` file maintains a history of processed articles to prevent duplicates. This is automatically handled by the GitHub Action.

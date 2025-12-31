Updated README (ready to paste)
6G Evolution Tracker
This repository tracks the global evolution of 6G technologies using automated data collection, AI-powered analysis, and a modern interactive dashboard.
A scheduled Python workflow runs monthly via GitHub Actions to gather signals from industry, academia, and standards bodies — transforming them into geopolitical and technical intelligence.

🚀 Features
🤖 AI-Powered Intelligence Engine
Deep Article Analysis  
Each article is processed using Gemini 3 Flash, producing a structured 6G intelligence profile including:

6G topic classification

Impact dimensions (research, standardization, deployment, spectrum, ecosystem)

Time horizon (near/mid/long-term)

World power impact (US, EU, China, Japan, Korea, India)

Emerging concepts

Key evidence extraction

Overall 6G importance score

Source region (emitter)

Geopolitical Mapping  
Tracks how different world powers influence and reference each other in 6G developments.

Source → Target Region Influence Matrix  
A 6×6 matrix showing which regions write about which other regions — revealing cross‑regional influence patterns.

Quarterly Momentum Tracking  
Normalized, weighted momentum scores per region and per quarter, based on AI-derived impact dimensions.

📊 Dashboard
A modern, responsive dashboard built with vanilla JS + CSS (glassmorphism style), featuring:

AI‑generated summaries and impact scores

Dynamic search and source filtering

Quarterly momentum data (normalized 0–5 scale)

Source → Target Region Influence Map (heatmap)

Automatic updates via GitHub Pages deployment

All data is generated automatically and published to the gh-pages branch.

⚙️ Workflow
Language: Python

AI Model: Gemini 3 Flash

Dashboard: HTML + JS + CSS

Automation: GitHub Actions

Schedule: Monthly (1st of each month)

The workflow:

Fetches RSS feeds in parallel

Filters articles using keyword relevance

Performs deep AI analysis

Generates:

latest_digest.json

momentum_data.json

source_target_matrix.json

Markdown digest

Updates the dashboard

Commits results back to the repository

Deploys the dashboard to GitHub Pages

🔑 Setup & Configuration
API Key
To enable AI analysis, add a GOOGLE_API_KEY to your repository secrets:

Get a key from Google AI Studio

Add it under:
Settings → Secrets and variables → Actions → New repository secret

Local Development
bash
pip install -r requirements.txt
python track_6g.py
Then open:

Code
dashboard/index.html
(Ensure latest_digest.json exists.)

🗂 Cache Management
The file seen_articles.json stores hashes of processed articles to prevent duplicates.
This is automatically cached and restored by GitHub Actions.

🌐 Output Files
The tracker generates:

File	Purpose
latest_digest.json	All processed articles + AI insights
momentum_data.json	Quarterly momentum scores per region
source_target_matrix.json	Source → target region influence map
6g_digest_YYYY-MM-DD.md	Human-readable monthly digest
seen_articles.json	Cache of processed articles
All files are committed automatically when new data is found.
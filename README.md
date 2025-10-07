# 6G Evolution Tracker

This repository is dedicated to tracking the evolution of 6G technologies.  
A scheduled Python script runs monthly using GitHub Actions to monitor news, publications, and updates related to 6G.

## Workflow

- **Language:** Python
- **Schedule:** Monthly (via GitHub Actions)
- **Dependencies:**  
  - [feedparser](https://pypi.org/project/feedparser/)  
  - [requests](https://pypi.org/project/requests/)

## How it works

The main script `track_6g.py` (customizable) will fetch and process updates about 6G development.  
All workflow runs and logs will be available in the GitHub Actions tab.

## Customization

To track additional sources, update the `url` list in `track_6g.py`.  
You can also add keyword filtering or markdown logging for deeper insights.

## Getting Started

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. Run the script:
    ```bash
    python track_6g.py
    ```

The workflow will run automatically every month.

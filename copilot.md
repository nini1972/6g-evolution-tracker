 TEXT FOR ANTIGRAVITY — 6G DEEP‑ANALYSIS AGENT SPECIFICATION
Goal:
Upgrade the existing 6g-evolution-tracker so that each collected article is analyzed deeply and consistently, producing structured data that can be aggregated into a world‑power‑vs‑timeline visualization.

1. Agent Role Definition
Create an LLM‑based analysis module with the following role:
You are a 6G strategy and technology analyst. You analyze technical, industrial, policy, and research articles related to 6G and pre‑6G technologies. For each article, you identify relevant 6G topics, assess its impact, evaluate which world powers are affected, determine the time horizon, and output a structured JSON profile. Your output must be consistent, evidence‑based, and aligned with the 6G evolution timeline.

2. Required Output Schema (JSON)
For every article collected by the tracker, generate the following JSON:
{
  "article_id": "",
  "title": "",
  "url": "",
  "date": "",
  "source_region": "",

  "6g_topics": [],

  "impact_dimensions": {
    "research_intensity": 0,
    "standardization_influence": 0,
    "industrial_deployment": 0,
    "spectrum_policy_signal": 0,
    "ecosystem_maturity": 0
  },

  "time_horizon": "",

  "overall_6g_importance": 0,

  "world_power_impact": {
    "US": 0,
    "EU": 0,
    "China": 0,
    "Japan": 0,
    "Korea": 0,
    "India": 0
  },

  "emerging_concepts": [],

  "key_evidence": []
}

3. Definitions for Consistency
6G Topics (choose all that apply)
• 	sub‑THz / THz
• 	AI‑native RAN
• 	semantic communications
• 	integrated sensing & communication (ISAC)
• 	non‑terrestrial networks (NTN)
• 	zero‑energy devices
• 	security & trust fabrics
• 	network automation / intent‑based orchestration
• 	sustainability
• 	spectrum & policy
• 	standardization
• 	device ecosystem
• 	cloud‑edge integration
• 	open RAN
• 	quantum‑safe networking
Impact Dimensions (0–5 scale)
• 	0 = no relevance
• 	1 = weak signal
• 	3 = meaningful development
• 	5 = major strategic impact
Time Horizon
• 	near‑term (≤ 2028)
• 	mid‑term (2028–2032)
• 	long‑term (≥ 2032)
World Powers
• 	US
• 	EU
• 	China
• 	Japan
• 	Korea
• 	India
Each scored 0–5 based on how the article affects their 6G position.

4. Aggregation Logic for the Dashboard
After generating JSON for each article:
A. Group articles by:
• 	world power
• 	time window (year or half‑year)

B. For each region + time window:
Compute:
momentum_score = weighted average of all impact_dimensions
weight = overall_6g_importance

C. Store results as:
{
  "region": "",
  "time_window": "",
  "research_intensity": 0,
  "standardization_influence": 0,
  "industrial_deployment": 0,
  "spectrum_policy_signal": 0,
  "ecosystem_maturity": 0,
  "momentum_score": 0
}

5. Visuals to Generate Later
The structured data should support:
• 	Heatmap timeline (regions vs time, color = momentum)
• 	Radar charts per region per year
• 	Stacked line chart showing momentum evolution
No visual generation needed now — only prepare the data model.

6. Integration Instructions
1. 	Keep the existing GitHub Action that collects articles.
2. 	After each article is fetched, pass its text to the analysis agent.
3. 	Store the resulting JSON in the existing dataset.
4. 	Add an aggregation step to compute world‑power momentum per time window.
5. 	Expose aggregated data to the GitHub Pages dashboard.

7. Flexibility Requirements
• 	The agent must detect new emerging concepts and classify them under existing topics.
• 	The schema must allow adding new world powers or dimensions later.
• 	The analysis must remain deterministic and consistent across runs.

END OF TEXT FOR ANTIGRAVITY
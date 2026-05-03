"""
RSS feed sources to monitor for 6G news and research.
Organised by category for better coverage of the 6G ecosystem.
Add or remove entries here without touching core pipeline logic.
"""

FEEDS = {
    # === Telecom Equipment Vendors ===
    "Ericsson": "https://www.ericsson.com/en/blog/rss",
    "Nokia": "https://www.nokia.com/newsroom/feed/en-us/",
    "Thales": "https://www.thalesgroup.com/en/rss.xml",

    # === Research & Academia ===
    "MDPI Engineering": "https://www.mdpi.com/rss",
    "IEEE Spectrum": "https://spectrum.ieee.org/feeds/feed.rss",
    "ArXiv CS Networking": "https://export.arxiv.org/rss/cs.NI",

    # === Regional Initiatives & Alliances ===
    "Next G Alliance": "https://www.nextgalliance.org/feed/",   # North America 6G initiative
    "SNS JU": "https://smart-networks.europa.eu/feed/",         # EU Smart Networks Joint Undertaking

    # === Telecom Industry News ===
    "6GWorld": "https://www.6gworld.com/feed/",
    "RCR Wireless": "https://www.rcrwireless.com/feed",
    "Fierce Wireless": "https://www.fiercewireless.com/rss/xml",
    "Mobile World Live": "https://www.mobileworldlive.com/feed/",
    "ZDNet 5G": "https://www.zdnet.com/topic/5g/rss.xml",
}

# 🔍 Keywords with weighted priorities
HIGH_PRIORITY = ["IMT-2030", "AI-native", "terahertz", "6G"]
MEDIUM_PRIORITY = ["radio spectrum", "6G architecture", "Release 21", "millimeter wave", "sub-THz"]

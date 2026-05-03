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
    "NEC Global": "https://www.nec.com/en/press/rss.xml",          # Japan: NEC R&D and enterprise tech

    # === Research & Academia ===
    "MDPI Engineering": "https://www.mdpi.com/rss",
    "IEEE Spectrum": "https://spectrum.ieee.org/feeds/feed.rss",
    "ArXiv CS Networking": "https://export.arxiv.org/rss/cs.NI",
    "ETRI Journal": "https://onlinelibrary.wiley.com/feed/22337326/most-recent",  # Korea: Electronics and Telecom Research Institute

    # === Regional Initiatives & Alliances ===
    "Next G Alliance": "https://www.nextgalliance.org/feed/",   # North America 6G initiative
    "SNS JU": "https://smart-networks.europa.eu/feed/",         # EU Smart Networks Joint Undertaking
    "GSMA Newsroom": "https://www.gsma.com/newsroom/feed/",     # Global: industry body covering all regions

    # === Asia-Pacific Operators & Vendors ===
    # Korea
    "Samsung Newsroom": "https://news.samsung.com/global/feed",   # Korea: Samsung R&D, network equipment
    "SK Telecom News": "https://news.sktelecom.com/feed",         # Korea: SK Telecom operator news

    # === Telecom Industry News ===
    "6GWorld": "https://www.6gworld.com/feed/",
    "RCR Wireless": "https://www.rcrwireless.com/feed",
    "Fierce Wireless": "https://www.fiercewireless.com/rss/xml",
    "Mobile World Live": "https://www.mobileworldlive.com/feed/",
    "Light Reading": "https://www.lightreading.com/rss.xml",      # Broad telecom coverage incl. Asia-Pacific
    "ZDNet 5G": "https://www.zdnet.com/topic/5g/rss.xml",
}

# Sources whose primary language is not English.
# Entries from these sources bypass the English keyword filter and are sent
# directly to the AI for relevance screening (is_6g_relevant gate).
# NOTE: The feeds currently in FEEDS (Samsung, SK Telecom, NEC, ETRI Journal) are
# English-language and should NOT be listed here — they use the standard keyword
# scoring path.  Add a source here only when it publishes primarily in a non-English
# language (e.g., a Chinese or Japanese news site).
SOURCE_LANGUAGE = {
    # Add non-English sources here as they are discovered, e.g.:
    # "CAICT": "zh",      # Chinese
    # "IMT-2030": "zh",   # Chinese
    # "KDDI": "ja",       # Japanese
}

# 🔍 Keywords with weighted priorities
# English keywords (scored +3 for high, +2 for medium)
HIGH_PRIORITY = ["IMT-2030", "AI-native", "terahertz", "6G"]
MEDIUM_PRIORITY = ["radio spectrum", "6G architecture", "Release 21", "millimeter wave", "sub-THz"]

# Multilingual keyword aliases — allow non-English articles that slip through
# to score above the relevance threshold even without English keywords.
# Each entry carries the same weight as its English HIGH/MEDIUM equivalent.
HIGH_PRIORITY_INTL = [
    # Chinese
    "第六代移动",   # 6th-generation mobile (Chinese)
    "六代移动通信",  # 6G mobile communications (Chinese)
    # Korean
    "6세대",        # 6th generation (Korean)
    # Japanese
    "第6世代",       # 6th generation (Japanese)
    "第六世代",      # 6th generation alt (Japanese)
]

MEDIUM_PRIORITY_INTL = [
    # Chinese
    "移动通信",        # mobile communications (Chinese simplified)
    "6G移动通信",      # 6G mobile communications (Chinese)
    "第六代移动通信",  # 6th-generation mobile communications (Chinese)
    # Korean
    "이동통신",        # mobile communications (Korean)
    "6G 이동통신",    # 6G mobile communications (Korean)
    # Japanese
    "移動通信",        # mobile communications (Japanese/traditional)
    "6G移動通信",      # 6G mobile communications (Japanese)
]

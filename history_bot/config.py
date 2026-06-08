# History & Mysteries Bot — Configuration
# ─────────────────────────────────────────

import os
from dotenv import load_dotenv

# Load .env from workspace root (one folder up)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY   = os.getenv("PEXELS_API_KEY")

CHANNEL_NAME     = "The Vault"

DEFAULT_TOPIC    = ""

# Viral topics that perform exceptionally well for US mystery audiences
TOPIC_POOL = [
    "The Missing Soviet Submarine That Vanished Without a Trace",
    "Japan's Most Disturbing Unsolved Disappearance",
    "The WW2 Experiment So Horrific It Was Classified for 50 Years",
    "The Dark Side of Antarctica: What They're Not Telling You",
    "The Family That Disappeared From a Locked House in 1959",
    "Siberia's Strangest Valley — Scientists Can't Explain It",
    "The $2 Billion Treasure That's Never Been Found",
    "The Last Radio Transmission Before 157 People Vanished",
    "How 3 Men Escaped The World's Most Secure Prison",
    "The Nuclear Bomb Still Sitting on the Bottom of the Atlantic"
]

# ─── VIDEO FORMATS ────────────────────────────────────────────────────────────
VIDEO_FORMATS = {
    "mystery":     "a deep-dive mystery documentary about an unexplained historical event or place",
    "conspiracy":  "an exploration of a famous historical conspiracy theory with facts and evidence",
    "dark_history":"a revealing documentary about a dark, lesser-known event in human history",
    "ancient":     "a documentary about an ancient civilisation, lost city, or archaeological mystery",
    "disappear":   "a chilling documentary about a famous real-world disappearance or unsolved case",
}

# config.py

import os
from dotenv import load_dotenv

# Load .env from workspace root (one folder up)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

VIDEO_FORMATS = {
    "news": "a daily FIFA 2026 news update covering squad news, player form, and breaking stories",
    "prediction": "a bold FIFA 2026 prediction video forecasting match results or tournament outcomes",
    "ranking": "a Top 5 ranking video — rank teams, players, or storylines in an engaging way",
    "stats": "a stats deep-dive analyzing a specific player or team heading into FIFA 2026",
}

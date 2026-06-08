import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = "@fifa2026_football_scores_matches"

DESCRIPTION = "🏆 Official FIFA World Cup 2026 Live Updates! Get instant live scores, breaking football news, team analysis, and real-time alerts. ⚽ Join the ultimate community for soccer fans! #FIFA2026 #WorldCup #Football #LiveScores #Soccer #FIFA"

url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setChatDescription"
payload = {"chat_id": CHANNEL_USERNAME, "description": DESCRIPTION}

response = requests.post(url, data=payload)
print("Status Code:", response.status_code)
print("Response:", response.text)

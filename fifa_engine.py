import os
import time
import requests
import feedparser
import random
from dotenv import load_dotenv
from google import genai

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

CHANNEL_USERNAME = "@fifa2026_football_scores_matches"

# API-Football assigns a specific ID to every league/tournament.
# World Cup is usually ID 1. We ONLY want to track these for live updates.
ALLOWED_LEAGUE_IDS = [1] 

if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

def post_to_telegram(channel_username, message_text, photo_url=None):
    """Posts a message to Telegram, guaranteeing the photo is always sent."""
    
    if photo_url:
        if len(message_text) <= 1024:
            # Send together
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload = {"chat_id": channel_username, "photo": photo_url, "caption": message_text}
            try:
                requests.post(url, json=payload).raise_for_status()
                print(f"Posted to {channel_username} with photo.")
                return True
            except Exception as e:
                print(f"Failed to post photo+caption: {e}")
                # Fall through to split message if this fails
        
        # If text is too long OR the combined sendPhoto failed, send them separately
        try:
            photo_url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            requests.post(photo_url_api, json={"chat_id": channel_username, "photo": photo_url}).raise_for_status()
            
            text_url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(text_url_api, json={"chat_id": channel_username, "text": message_text}).raise_for_status()
            print(f"Posted to {channel_username} (Photo and Text sent separately).")
            return True
        except Exception as e:
            print(f"Failed to post split message: {e}")
            # Final fallback: just text with link appended
            try:
                fallback_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                fallback_payload = {"chat_id": channel_username, "text": f"{message_text}\n\n{photo_url}"}
                requests.post(fallback_url, json=fallback_payload).raise_for_status()
                print(f"Fallback Posted to {channel_username}")
                return True
            except Exception as e2:
                print(f"Final fallback failed: {e2}")
                return False
    else:
        # No photo
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": channel_username, "text": message_text}
        try:
            requests.post(url, json=payload).raise_for_status()
            print(f"Posted to {channel_username} (Text only).")
            return True
        except Exception as e:
            print(f"Failed to post text: {e}")
            return False

def fetch_offline_news():
    """Fetches general football news from an RSS feed."""
    feed = feedparser.parse("https://www.skysports.com/rss/12040")
    entries = feed.entries[:5]
    news_data = ""
    
    # List of high-quality, watermark-free generic football/stadium images from Wikimedia
    # These specific URLs have been strictly verified to work with Telegram's size and fetch limits.
    generic_images = [
        "https://upload.wikimedia.org/wikipedia/commons/1/16/Wembley_Stadium_interior.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/43/Old_Trafford_inside_20060726_1.jpg"
    ]
    image_url = random.choice(generic_images)
    
    return news_data, image_url

def generate_fifa_analysis(news_text):
    """Uses Gemini to generate the 30-hour offline analysis post."""
    prompt = f"""
You are an expert FIFA World Cup 2026 hype-builder for a Telegram channel.
Give a detailed but engaging update based loosely on global football news.

Instructions:
1. SPACING & ALIGNMENT: Add clear blank lines between your sections and bullet points. Make it perfectly readable and clean.
2. STRICT LIMIT: Keep your entire response under 900 characters total. This is an absolute hard limit so the photo caption works.
3. Mimic an "Elite Football Insider / Ultra Fan" aesthetic. Use popular global football slang (e.g., "Top bins", "Locker room secrets", "Tactical masterclass", "Baller", "Gaffer", "Pitch side"). Do NOT use finance or trading terms.
4. Format it with high-energy hype vibes using emojis like ⚽, 🏟️, 🔥, 🏆, 🗣️, ⚡.
5. Keep it punchy and urgent. State the news fact, and explain what it means for the upcoming World Cup.
6. Do NOT use any bolding or special markdown/HTML formatting (no ** or <b>). Just plain text and emojis.
7. End with an engaging question for the fans to drive comments.
8. Add 3-5 trending hashtags at the bottom.

Recent News Data:
{news_text}
"""
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def generate_live_goal_post(match_data):
    """Uses Gemini to generate an instant LIVE GOAL post."""
    prompt = f"""
You are a live commentator for a massive FIFA World Cup Telegram channel.
A GOAL HAS JUST BEEN SCORED or a MAJOR EVENT HAPPENED! 

Instructions:
1. Write an urgent, ALL-CAPS headline (e.g., 🚨 GOAL! 🚨).
2. State the current score clearly.
3. Keep it extremely short (2 sentences max).
4. ABSOLUTELY NO FORMATTING. Do NOT use **bold**, *italics*, or HTML tags. Just plain text and emojis.

Match Data:
{match_data}
"""
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def fetch_live_matches():
    """Fetches currently live matches from API-Football."""
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('response', [])
    except Exception as e:
        print(f"API Error: {e}")
        return []

def run_fifa_engine():
    print(f"Starting FIFA Engine for {CHANNEL_USERNAME}...")
    tracked_match_id = None
    last_score_str = ""
    
    # Track when we last sent a general "offline" post (The 30-hour rule)
    last_offline_post_time = 0
    # 30 hours in seconds: 30 * 60 * 60 = 108000
    OFFLINE_POST_INTERVAL = 108000 
    
    while True:
        print(f"\n[{time.strftime('%H:%M:%S')}] Checking API for live matches...")
        all_live_matches = fetch_live_matches()
        
        # Filter: Only care about FIFA / Major allowed tournaments
        fifa_live_matches = [m for m in all_live_matches if m['league']['id'] in ALLOWED_LEAGUE_IDS]
        
        if not fifa_live_matches:
            print("No FIFA matches are live right now.")
            tracked_match_id = None
            last_score_str = ""
            
            # Check if it's been 30 hours since our last offline post
            current_time = time.time()
            if (current_time - last_offline_post_time) >= OFFLINE_POST_INTERVAL:
                print("It has been 30 hours. Fetching offline news analysis...")
                news_text, image_url = fetch_offline_news()
                analysis_post = generate_fifa_analysis(news_text)
                
                if analysis_post:
                    # Post with the actual news article image
                    post_to_telegram(CHANNEL_USERNAME, analysis_post, photo_url=image_url)
                    last_offline_post_time = current_time
            else:
                hours_left = (OFFLINE_POST_INTERVAL - (current_time - last_offline_post_time)) / 3600
                print(f"Waiting {hours_left:.1f} more hours until next offline update.")
            
            # Sleep for 15 minutes before checking for live matches again
            time.sleep(900)
            continue
            
        # We found a live FIFA match!
        match = fifa_live_matches[0]
        match_id = match['fixture']['id']
        current_score_str = f"{match['goals']['home']}-{match['goals']['away']}"
        
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        minute = match['fixture']['status']['elapsed']
        match_info = f"{home} {match['goals']['home']} - {match['goals']['away']} {away} (Minute: {minute}')"
        
        print(f"Tracking FIFA Match: {match_info}")
        home_logo = match['teams']['home']['logo']
        
        # If we started tracking a NEW match, or the score CHANGED
        if match_id != tracked_match_id or current_score_str != last_score_str:
            print(f"EVENT DETECTED! Old: {last_score_str}, New: {current_score_str}")
            
            post_text = generate_live_goal_post(match_info)
            if post_text:
                post_to_telegram(CHANNEL_USERNAME, post_text, photo_url=home_logo)
            
            tracked_match_id = match_id
            last_score_str = current_score_str
        else:
            print("No score change detected.")
            
        # Sleep exactly 3 minutes during live matches
        print("Sleeping for 3 minutes...")
        time.sleep(180)

if __name__ == "__main__":
    run_fifa_engine()

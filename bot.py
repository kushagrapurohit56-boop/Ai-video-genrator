import os
import time
import requests
import feedparser
import schedule
import re
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# -----------------------------------------------------------------
# Configuration for your channels
# -----------------------------------------------------------------
CHANNELS = {
    "crypto": {
        "name": "Global Crypto",
        "username": "@finance_crypto_trading_news",
        "feeds": [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptopotato.com/feed/",
        ],
        "prompt": """
You are an elite, underground crypto trader running an exclusive Telegram channel.
You need to convert the provided news into a "Crypto Matrix" style post.

Instructions:
1. SPACING & ALIGNMENT: Add clear blank lines between your sections and bullet points. Make it perfectly readable and clean.
2. STRICT LIMIT: Keep your entire response under 900 characters total. This is an absolute hard limit so the photo caption works.
3. Mimic the "Escape The Matrix" aesthetic. Use terms like "The Matrix", "Smart Money", "Alpha", or "The Elites".
4. Format it with dark/hacker vibes using emojis like 💊, 👁️, 🟩, ⚠️, 🚨, 🧠, 💻.
5. Keep it punchy and urgent. State the news fact, and explain why the masses are missing it.
6. Do NOT use any bolding or special markdown/HTML formatting (no ** or <b>). Just plain text and emojis.
7. End with an urgent call to action.
8. Add 3-5 trending hashtags at the bottom.

News Items:
"""
    },
    "indian": {
        "name": "Indian Stock Market",
        "username": "@Nifty50_stock_Sensex_zerohero",
        "feeds": [
            "https://www.moneycontrol.com/rss/marketreports.xml",
            "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms",
            "https://www.livemint.com/rss/markets"
        ],
        "prompt": """
You are an elite, underground Indian Stock Market trader running an exclusive Telegram channel.
You need to convert the provided news into a "Finance Matrix" style post.

Instructions:
1. SPACING & ALIGNMENT: Add clear blank lines between your sections and bullet points. Make it perfectly readable and clean.
2. STRICT LIMIT: Keep your entire response under 900 characters total. This is an absolute hard limit so the photo caption works.
3. Mimic the "Escape The Matrix" aesthetic. Use terms like "Operators", "Smart Money", or "Retail Trap".
4. Format it with dark/hacker vibes using emojis like 💊, 👁️, 🟩, ⚠️, 🚨, 🧠, 💻.
5. Keep it punchy and actionable. Tell them what the "smart money" is actually doing based on this news.
6. Do NOT use any bolding or special markdown/HTML formatting (no ** or <b>). Just plain text and emojis.
7. End with an urgent call to action.
8. Add 3-5 trending hashtags at the bottom.

News Items:
"""
    }
}

def fetch_latest_news(feeds, max_items_per_feed=2):
    """Fetches the latest news articles and tries to extract an image."""
    news_items = []
    best_image_url = None
    
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items_per_feed]:
                title = entry.title
                summary = entry.get("summary", "")
                link = entry.link
                
                # Clean up HTML tags from summary
                summary = re.sub('<[^<]+?>', '', summary)
                
                # Attempt to extract an image URL
                # 1. Check media_content
                if not best_image_url and 'media_content' in entry:
                    for media in entry.media_content:
                        if 'url' in media and media.get('medium') == 'image':
                            best_image_url = media['url']
                            break
                # 2. Check links array for image/jpeg
                if not best_image_url and 'links' in entry:
                    for l in entry.links:
                        if 'type' in l and l['type'].startswith('image/'):
                            best_image_url = l['href']
                            break
                
                news_items.append({
                    "title": title,
                    "summary": summary[:200] + "...",
                    "link": link
                })
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
            
    return news_items, best_image_url

def format_news_with_gemini(news_items, base_prompt):
    """Uses Gemini to summarize and format the news."""
    if not client:
        print("Gemini API key not configured. Cannot format news.")
        return None
        
    prompt = base_prompt
    for idx, item in enumerate(news_items):
        prompt += f"\n{idx+1}. Title: {item['title']}\nSummary: {item['summary']}\nLink: {item['link']}\n"
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

def post_to_telegram(channel_username, text, image_url=None):
    """Posts the message to Telegram, guaranteeing the photo is always sent."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Telegram bot token not configured.")
        return
        
    if image_url:
        if len(text) <= 1024:
            # Send together
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload = {"chat_id": channel_username, "photo": image_url, "caption": text}
            try:
                requests.post(url, json=payload).raise_for_status()
                print(f"Successfully posted to {channel_username} with photo!")
            except Exception as e:
                print(f"Error posting photo+caption: {e}")
        else:
            # Text too long. Send photo first, then text!
            try:
                photo_url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                requests.post(photo_url_api, json={"chat_id": channel_username, "photo": image_url}).raise_for_status()
                
                text_url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                requests.post(text_url_api, json={"chat_id": channel_username, "text": text}).raise_for_status()
                print(f"Successfully posted to {channel_username} (Photo and Text sent separately).")
            except Exception as e:
                print(f"Error posting split message: {e}")
    else:
        # Fallback to pure text
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": channel_username, "text": text, "disable_web_page_preview": False}
        try:
            requests.post(url, json=payload).raise_for_status()
            print(f"Successfully posted to {channel_username} (Text only).")
        except Exception as e:
            print(f"Error posting text: {e}")

def job_crypto():
    print(f"[{time.strftime('%X')}] Running Crypto news fetch job...")
    channel = CHANNELS["crypto"]
    news, image_url = fetch_latest_news(channel["feeds"])
    
    if not image_url:
        image_url = "https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg"
    
    if not news:
        print("No crypto news found.")
        return
        
    formatted_message = format_news_with_gemini(news, channel["prompt"])
    if formatted_message:
        post_to_telegram(channel["username"], formatted_message, image_url)

def job_indian():
    print(f"[{time.strftime('%X')}] Running Indian Market news fetch job...")
    channel = CHANNELS["indian"]
    news, image_url = fetch_latest_news(channel["feeds"])
    
    if not image_url:
        image_url = "https://upload.wikimedia.org/wikipedia/commons/b/b8/BSE_Building.jpg"
    
    if not news:
        print("No Indian market news found.")
        return
        
    formatted_message = format_news_with_gemini(news, channel["prompt"])
    if formatted_message:
        post_to_telegram(channel["username"], formatted_message, image_url)


def main():
    print("Bot module loaded. Run job_crypto() or job_indian() directly.")

if __name__ == "__main__":
    main()

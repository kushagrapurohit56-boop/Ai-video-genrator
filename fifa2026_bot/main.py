"""
FIFA 2026 YouTube Automation Bot
Generates script → voiceover → video → uploads to YouTube
"""

import os
import sys
import json
import random
import requests
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

from groq import Groq
from duckduckgo_search import DDGS
from config import GROQ_API_KEY, ELEVENLABS_API_KEY, VIDEO_FORMATS

# ─── SETTINGS ────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS = 24
OUTPUT_FILE = "output_video.mp4"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ─── COLORS ──────────────────────────────────────────────────────────────────
BG_COLOR      = (10, 20, 15)       # dark pitch green-black
ACCENT_COLOR  = (29, 158, 117)     # FIFA green
TEXT_COLOR    = (255, 255, 255)    # white
SUB_COLOR     = (200, 220, 210)    # soft white for subtitles
GOLD_COLOR    = (255, 193, 37)     # gold for highlights


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — GENERATE SCRIPT WITH GROQ API
# ══════════════════════════════════════════════════════════════════════════════

def generate_script(format_key: str, topic: str = "") -> dict:
    """Call Groq API to generate a complete video package."""

    formats = {
        "news":       "a daily FIFA 2026 news update covering squad news, player form, and breaking stories",
        "prediction": "a bold FIFA 2026 prediction video forecasting match results or tournament outcomes",
        "ranking":    "a Top 5 ranking video — rank teams, players, or storylines in an engaging way",
        "stats":      "a stats deep-dive analyzing a specific player or team heading into FIFA 2026",
    }

    topic_line = f'The specific angle is: "{topic}".' if topic else "Pick the most interesting trending angle yourself."

    print(f"\n[1/4] Generating script via Groq API...")

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = (
        "You are a YouTube content strategist for a FIFA 2026 football channel. "
        "Respond ONLY with valid JSON in this exact shape: "
        '{"title": "catchy YouTube title under 60 chars", '
        '"script": "full spoken script 300-400 words with strong hook, 3 key points, call to action", '
        '"description": "SEO YouTube description 150 words with keywords, end with Subscribe line", '
        '"tags": "comma-separated list of 15 YouTube tags", '
        '"image_queries": ["query 1", "query 2", "query 3", "query 4", "query 5"]}'
    )
    
    user_prompt = f"Create a video package for {formats[format_key]}. {topic_line}"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            data = json.loads(response.choices[0].message.content)
            print(f"    [OK] Title: {data['title']}")
            return data
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to generate valid JSON from Groq after 3 attempts: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — GENERATE VOICEOVER WITH ELEVENLABS
# ══════════════════════════════════════════════════════════════════════════════

def generate_voiceover(script_text: str, output_path: str = "voiceover.mp3") -> str:
    """Convert script to speech using Microsoft Edge TTS (Free, Unlimited)."""
    import os
    print("\n[2/4] Generating voiceover via Edge TTS...")

    with open("temp_script.txt", "w", encoding="utf-8") as f:
        f.write(script_text)

    # en-US-GuyNeural is a great male voice for news/sports
    VOICE = "en-US-GuyNeural"
    
    exit_code = os.system(f'edge-tts -f temp_script.txt --write-media {output_path} --voice {VOICE}')
    
    if exit_code != 0:
        raise RuntimeError(f"Edge TTS failed with exit code {exit_code}")

    if os.path.exists("temp_script.txt"):
        os.remove("temp_script.txt")

    print(f"    [OK] Voiceover saved -> {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — CREATE VIDEO WITH MOVIEPY + PILLOW
# ══════════════════════════════════════════════════════════════════════════════

def make_background_frame(title: str) -> np.ndarray:
    """Create a single branded background image as numpy array."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Subtle grid lines (pitch effect)
    for x in range(0, WIDTH, 120):
        draw.line([(x, 0), (x, HEIGHT)], fill=(20, 40, 30), width=1)
    for y in range(0, HEIGHT, 120):
        draw.line([(0, y), (WIDTH, y)], fill=(20, 40, 30), width=1)

    # Center circle
    cx, cy, r = WIDTH // 2, HEIGHT // 2, 220
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(25, 50, 35), width=2)
    draw.line([(0, HEIGHT // 2), (WIDTH, HEIGHT // 2)], fill=(25, 50, 35), width=2)

    # Top accent bar
    draw.rectangle([0, 0, WIDTH, 8], fill=ACCENT_COLOR)

    # FIFA 2026 watermark top-left
    try:
        font_sm = ImageFont.truetype("arialbd.ttf", 28)
    except Exception:
        font_sm = ImageFont.load_default()

    draw.text((40, 28), "⚽  FIFA 2026", font=font_sm, fill=ACCENT_COLOR)

    # Channel watermark top-right (edit with your channel name)
    draw.text((WIDTH - 280, 28), "YOUR CHANNEL", font=font_sm, fill=(100, 130, 115))

    # Title box at bottom
    draw.rectangle([0, HEIGHT - 160, WIDTH, HEIGHT], fill=(5, 12, 8))
    draw.rectangle([0, HEIGHT - 164, WIDTH, HEIGHT - 158], fill=ACCENT_COLOR)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 52)
    except Exception:
        font_title = ImageFont.load_default()

    # Word-wrap title
    wrapped = textwrap.fill(title.upper(), width=55)
    draw.text((60, HEIGHT - 145), wrapped, font=font_title, fill=TEXT_COLOR)

    return np.array(img)


def add_subtitle_to_frame(base_frame: np.ndarray, subtitle: str) -> np.ndarray:
    """Overlay subtitle text onto a frame."""
    img = Image.fromarray(base_frame.copy())
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except Exception:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(subtitle, width=70)
    lines = wrapped.split("\n")

    # Semi-transparent subtitle background
    line_h = 56
    box_h = len(lines) * line_h + 24
    box_y = HEIGHT - 220 - box_h
    draw.rectangle([60, box_y, WIDTH - 60, box_y + box_h], fill=(0, 0, 0, 180))

    for i, line in enumerate(lines):
        draw.text((80, box_y + 12 + i * line_h), line, font=font, fill=SUB_COLOR)

    return np.array(img)


def download_stock_videos(queries: list) -> list:
    """Download one HD MP4 per query using Pexels."""
    print("\n[  ] Downloading stock videos from Pexels...")
    import requests
    from config import PEXELS_API_KEY
    os.makedirs("videos", exist_ok=True)
    downloaded_paths = []
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    for i, query in enumerate(queries):
        print(f"    Searching Pexels: {query}")
        try:
            safe_query = query + " football soccer"
            res = requests.get(
                f"https://api.pexels.com/videos/search?query={safe_query}&per_page=5&orientation=landscape&size=medium",
                headers=headers,
                timeout=10
            )
            data = res.json()
            if "videos" in data and len(data["videos"]) > 0:
                video_files = data["videos"][0]["video_files"]
                best_file = max(video_files, key=lambda x: x["width"] * x["height"] if x["file_type"] == "video/mp4" else 0)
                video_url = best_file["link"]
                
                path = f"videos/v_{i}.mp4"
                r = requests.get(video_url, stream=True, timeout=15)
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                downloaded_paths.append(path)
            else:
                print("    No Pexels results, skipping.")
        except Exception as e:
            print(f"    Failed: {e}")
                
    return downloaded_paths


def create_overlay_for_chunk(title: str, subtitle: str) -> Image.Image:
    """Pre-render the text and dark background for a chunk to prevent memory leaks."""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 160))
    draw = ImageDraw.Draw(overlay)
    
    draw.rectangle([0, 0, WIDTH, 8], fill=ACCENT_COLOR)

    try:
        font_sm = ImageFont.truetype("arialbd.ttf", 20)
    except Exception:
        font_sm = ImageFont.load_default()

    draw.text((25, 18), "⚽  FIFA 2026", font=font_sm, fill=ACCENT_COLOR)
    draw.text((WIDTH - 180, 18), "YOUR CHANNEL", font=font_sm, fill=(100, 130, 115))

    draw.rectangle([0, HEIGHT - 110, WIDTH, HEIGHT], fill=(5, 12, 8))
    draw.rectangle([0, HEIGHT - 114, WIDTH, HEIGHT - 108], fill=ACCENT_COLOR)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 34)
    except Exception:
        font_title = ImageFont.load_default()

    wrapped_title = textwrap.fill(title.upper(), width=55)
    draw.text((40, HEIGHT - 100), wrapped_title, font=font_title, fill=TEXT_COLOR)

    try:
        font_sub = ImageFont.truetype("arialbd.ttf", 46)
    except Exception:
        font_sub = ImageFont.load_default()

    wrapped_sub = textwrap.fill(subtitle.upper(), width=40)
    
    left_sub, top_sub, right_sub, bottom_sub = draw.textbbox((0, 0), wrapped_sub, font=font_sub)
    text_w = right_sub - left_sub
    text_h = bottom_sub - top_sub
    
    x = (WIDTH - text_w) // 2
    y = (HEIGHT - text_h) // 2 - 80
    
    draw.multiline_text((x+4, y+4), wrapped_sub, font=font_sub, fill=(0,0,0), align="center")
    draw.multiline_text((x, y), wrapped_sub, font=font_sub, fill=(255, 255, 255), align="center")

    return overlay


def create_video(script_text: str, title: str, audio_path: str, output_path: str, video_paths: list) -> str:
    """Build the final MP4 from video B-roll + subtitles + audio."""
    from moviepy import VideoFileClip, AudioFileClip, ColorClip, concatenate_videoclips, vfx

    print("\n[3/4] Building video...")

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    words = script_text.split()
    chunk_size = 8
    chunks = [" ".join(words[i: i + chunk_size]) for i in range(0, len(words), chunk_size)]
    chunk_dur = total_duration / len(chunks)

    clips = []
    video_cache = {}

    for i, chunk in enumerate(chunks):
        clip = None
        if video_paths:
            vid_path = video_paths[i % len(video_paths)]
            if vid_path not in video_cache:
                try:
                    raw_clip = VideoFileClip(vid_path)
                    
                    bg_ratio = raw_clip.w / raw_clip.h
                    target_ratio = WIDTH / HEIGHT
                    
                    if bg_ratio > target_ratio:
                        new_h = HEIGHT
                        new_w = int(HEIGHT * bg_ratio)
                    else:
                        new_w = WIDTH
                        new_h = int(WIDTH / bg_ratio)
                        
                    raw_clip = raw_clip.with_effects([vfx.Resize(new_size=(new_w, new_h))])
                    
                    left = (new_w - WIDTH) // 2
                    top = (new_h - HEIGHT) // 2
                    raw_clip = raw_clip.with_effects([vfx.Crop(x1=left, y1=top, x2=left+WIDTH, y2=top+HEIGHT)])
                    
                    raw_clip = raw_clip.with_effects([vfx.Loop(duration=max(raw_clip.duration, total_duration))])
                    video_cache[vid_path] = raw_clip
                except Exception as e:
                    print(f"Failed to process {vid_path}: {e}")
                    video_cache[vid_path] = None
                    
            base_clip = video_cache[vid_path]
            if base_clip is not None:
                start_time = (i * chunk_dur) % max(1, base_clip.duration - chunk_dur - 1)
                clip = base_clip.subclipped(start_time, start_time + chunk_dur)
        
        if clip is None:
            clip = ColorClip(size=(WIDTH, HEIGHT), color=(5, 12, 8), duration=chunk_dur)
            
        # Pre-render the overlay once for this chunk to save memory
        chunk_overlay = create_overlay_for_chunk(title, chunk)
        
        def apply_overlay(frame, overlay=chunk_overlay):
            if frame.dtype != np.uint8:
                frame = np.array(frame, dtype=np.uint8)
            img = Image.fromarray(frame).convert("RGBA")
            if img.width != WIDTH or img.height != HEIGHT:
                img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            img.alpha_composite(overlay)
            return np.array(img.convert("RGB"))
            
        clip = clip.image_transform(apply_overlay)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="chain")
    video = video.with_audio(audio)

    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac"
    )

    print(f"    [OK] Video saved -> {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — UPLOAD TO YOUTUBE
# ══════════════════════════════════════════════════════════════════════════════

def get_youtube_client():
    """Authenticate and return YouTube API client. Saves token for reuse."""
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", YOUTUBE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path: str, title: str, description: str, tags: list) -> str:
    """Upload video file to YouTube channel."""

    print("\n[4/4] Authenticating with YouTube...")

    youtube = get_youtube_client()
    
    print("\n    [OK] YouTube Authenticated! Starting upload...")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "17",  # Sports category
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=5)
            if status:
                pct = int(status.progress() * 100)
                print(f"    Uploading... {pct}%", end="\r")
        except Exception as e:
            print(f"\n    [!] Network error during upload: {e}. Retrying in 10s...")
            import time
            time.sleep(10)

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n    [OK] Uploaded! Watch at: {url}")
    return url


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — RUN THE FULL PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(format_key: str = "news", topic: str = ""):
    print("=" * 55)
    print("  FIFA 2026 YouTube Bot — Full Pipeline")
    print("=" * 55)

    # 1. Generate script
    data = generate_script(format_key, topic)

    # 2. Generate voiceover
    audio_path = generate_voiceover(data["script"])

    # 2.5 Download dynamic videos
    video_queries = data.get("image_queries", ["FIFA World Cup 2026", "Soccer Stadium", "Lionel Messi", "Cristiano Ronaldo", "Football Fans"])
    video_paths = download_stock_videos(video_queries)

    # 3. Create video
    video_path = create_video(data["script"], data["title"], audio_path, OUTPUT_FILE, video_paths)

    # 4. Upload to YouTube
    tags_list = [t.strip() for t in data["tags"].split(",")]
    url = upload_to_youtube(video_path, data["title"], data["description"], tags_list)

    print("\n" + "=" * 55)
    print("  [DONE] Video is live on your channel.")
    print(f"  Link: {url}")
    print("=" * 55)

    # Cleanup temp files
    for f in ["voiceover.mp3"]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    # Edit these before running
    FORMAT  = "news"      # news | prediction | ranking | stats
    TOPIC   = ""          # Leave blank for AI to choose, or type a topic

    run_pipeline(FORMAT, TOPIC)

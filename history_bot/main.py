"""
Hidden Histories — YouTube Automation Bot
Generates a 10-15 minute documentary script → voiceover → video → uploads to YouTube
Niche: History & Mysteries
"""

import os
import json
import random
import asyncio
import requests
import textwrap
import pickle
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, AudioFileClip, ColorClip,
    concatenate_videoclips, ImageClip, CompositeVideoClip, vfx
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import edge_tts
from groq import Groq

from config import GROQ_API_KEY, PEXELS_API_KEY, CHANNEL_NAME, VIDEO_FORMATS, TOPIC_POOL

# ─── SETTINGS ────────────────────────────────────────────────────────────────
WIDTH, HEIGHT   = 1280, 720     # 720p landscape
FPS             = 24
OUTPUT_FILE     = "output_video.mp4"
YOUTUBE_SCOPES  = ["https://www.googleapis.com/auth/youtube.upload"]
TTS_VOICE       = "en-US-GuyNeural"   # Deep, authoritative documentary voice

# ─── COLORS (Dark cinematic theme) ───────────────────────────────────────────
BG_COLOR        = (8, 6, 12)           # near-black purple
ACCENT_COLOR    = (180, 130, 60)       # aged gold / parchment
TEXT_COLOR      = (240, 230, 210)      # warm white
SUBTITLE_COLOR  = (255, 255, 255)      # pure white
SHADOW_COLOR    = (0, 0, 0)

client = Groq(api_key=GROQ_API_KEY)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — GENERATE SCRIPT WITH GROQ API
# ══════════════════════════════════════════════════════════════════════════════

def generate_script(format_key: str = "mystery", topic: str = "") -> dict:
    """Generate a full 20-25 minute documentary script (~2500-3000 words) using multi-stage Groq calls."""

    print("\n[1/4] Generating documentary script via Groq...")

    if not topic:
        topic = random.choice(TOPIC_POOL)
        print(f"    Selected random viral topic: '{topic}'")

    formats = VIDEO_FORMATS
    
    # SYSTEM PROMPTS
    system_prompt_meta = f"""You are a world-class YouTube documentary director and VFX producer for '{CHANNEL_NAME}'.
You create highly engaging, cinematic mystery/history documentary structures.

Write in a dramatic, suspenseful, and professional tone.
CRITICAL RULES:
1. Open with a powerful curiosity-driven title based on viral formulas:
   - "The [Thing] That [Shocking Outcome]"
   - "[Country]'s [Superlative] Unsolved Mystery"
   - "[Number] [People] Witnessed Something They Could Never Speak About"
   - "The Dark Side Of [Place/Topic]"
2. Define exactly 5 distinct chapters/segments that build a compelling investigation.
3. Provide 15 stock-footage friendly search queries for Pexels (general words like: "dark stormy ocean", "ancient stone artifact", "secret document file", "foggy forest night").

Return ONLY a JSON object with these exact keys:
- title: A shocking, curiosity-driven YouTube title (max 70 chars)
- description: A 200-word YouTube video description with keywords
- tags: 15 comma-separated YouTube tags
- pexels_queries: A list of 15 stock-footage-friendly search terms
- chapters: A list of 5 chapter titles for the description timestamps"""

    user_prompt_meta = f"Create the outline and metadata for a documentary on: '{topic}' under category: {formats[format_key]}."
    
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt_meta},
                    {"role": "user", "content": user_prompt_meta},
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.75,
                max_tokens=2000,
            )
            meta_data = json.loads(response.choices[0].message.content)
            break
        except Exception as e:
            print(f"    [!] Metadata generation attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"Failed to generate metadata outline: {e}")
            time.sleep(2)

    print(f"    [OK] Title: {meta_data['title']}")
    print(f"    [OK] Outline: {', '.join(meta_data['chapters'])}")

    # Call 2: First part of the script (Intro & Chapters 1-2)
    print("    Generating script Part 1 (Introduction & Chapters 1-2)...")
    system_prompt_part1 = f"""You are an elite YouTube documentary scriptwriter.
Write the first half of a script for the title: "{meta_data['title']}".
Structure it as:
- A gripping, intense cinematic Hook (first 3-4 sentences must create immense tension and suspense, drawing the viewer in completely).
- Background/Setup.
- Chapter 1: {meta_data['chapters'][0]} (elaborate deeply with dramatic facts and high-level suspense).
- Chapter 2: {meta_data['chapters'][1]} (elaborate deeply).

Tone must be dark, atmospheric, immersive, and slow-paced storytelling that makes viewers unable to look away.
Write in raw paragraph form, no actor/director cues, no formatting headers. Simply write the narrative text directly.
Target length: 1,300 to 1,500 words."""

    for attempt in range(3):
        try:
            response_part1 = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt_part1},
                    {"role": "user", "content": "Write the first half of the documentary script now."},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=4000,
            )
            part1_text = response_part1.choices[0].message.content.strip()
            break
        except Exception as e:
            print(f"    [!] Part 1 generation attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"Part 1 generation failed: {e}")
            time.sleep(2)

    # Call 3: Second part of the script (Chapters 3-5 & Conclusion & CTA)
    print("    Generating script Part 2 (Chapters 3-5, Conclusion & Outro)...")
    system_prompt_part2 = f"""You are an elite YouTube documentary scriptwriter.
Continue writing the second half of the script for the title: "{meta_data['title']}".
The script must pick up seamlessly from where the previous part left off.
Structure:
- Chapter 3: {meta_data['chapters'][2]}
- Chapter 4: {meta_data['chapters'][3]}
- Chapter 5: {meta_data['chapters'][4]}
- Compelling theories or resolution.
- Intense open-ended conclusion.
- CTA: Ask the audience what they think, to comment their theories, like, and subscribe.

Previous script text ended with. Continue writing the final chapters and conclusion in the same dark, immersive narrative style. Do not include any meta commentary, headers, or cues. Write the narrative directly.
Target length: 1,300 to 1,500 words."""

    for attempt in range(3):
        try:
            response_part2 = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt_part2},
                    {"role": "user", "content": f"Write the second half of the script starting after: ...{part1_text[-200:]}"},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=4000,
            )
            part2_text = response_part2.choices[0].message.content.strip()
            break
        except Exception as e:
            print(f"    [!] Part 2 generation attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise RuntimeError(f"Part 2 generation failed: {e}")
            time.sleep(2)

    full_script = part1_text + "\n\n" + part2_text
    word_count = len(full_script.split())
    print(f"    [OK] Complete script generated: {word_count} words (~{word_count // 130} min)")

    meta_data["script"] = full_script
    return meta_data


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — GENERATE VOICEOVER WITH EDGE TTS
# ══════════════════════════════════════════════════════════════════════════════

def generate_voiceover(script_text: str, output_path: str = "voiceover.mp3") -> str:
    """Convert script to MP3 using Microsoft Edge TTS (free, high quality)."""

    print("\n[2/4] Generating voiceover via Edge TTS...")

    async def _run():
        communicate = edge_tts.Communicate(script_text, TTS_VOICE, rate="-5%")
        await communicate.save(output_path)

    asyncio.run(_run())
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"    [OK] Voiceover saved -> {output_path} ({size_mb:.1f} MB)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3A — DOWNLOAD PEXELS STOCK VIDEOS
# ══════════════════════════════════════════════════════════════════════════════

# Fallback cinematic queries if Pexels returns nothing for a query
FALLBACK_QUERIES = [
    "ancient ruins stone", "dark forest fog", "ocean waves dramatic",
    "castle medieval stone", "desert sand dunes", "stormy sky clouds",
    "candle flame dark", "mountain landscape mist", "river valley aerial",
]

def download_stock_videos(queries: list) -> list:
    """Download 3 HD MP4 clips per query for maximum visual variety."""

    print("\n[  ] Downloading cinematic stock videos from Pexels...")
    os.makedirs("videos", exist_ok=True)

    # Wipe old clips so we don't mix with previous run
    for old in os.listdir("videos"):
        try:
            os.remove(os.path.join("videos", old))
        except Exception:
            pass

    downloaded = []
    headers = {"Authorization": PEXELS_API_KEY}
    clip_index = 0

    all_queries = queries + random.sample(FALLBACK_QUERIES, min(4, len(FALLBACK_QUERIES)))

    for query in all_queries:
        print(f"    Searching: '{query}'")
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                params={"query": query, "per_page": 15, "orientation": "landscape", "size": "medium"},
                headers=headers,
                timeout=15,
            )
            videos = resp.json().get("videos", [])
            if not videos:
                print(f"         No results.")
                continue

            # Download up to 3 different videos per query
            downloaded_this_query = 0
            random.shuffle(videos)
            for video in videos:
                if downloaded_this_query >= 3:
                    break
                try:
                    mp4_files = [f for f in video["video_files"]
                                 if f.get("file_type") == "video/mp4" and f.get("width", 0) >= 640]
                    if not mp4_files:
                        continue
                    best = max(mp4_files, key=lambda f: f.get("width", 0) * f.get("height", 0))
                    url = best["link"]

                    path = f"videos/clip_{clip_index:03d}.mp4"
                    r = requests.get(url, stream=True, timeout=30)
                    with open(path, "wb") as fp:
                        for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):
                            fp.write(chunk)

                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    print(f"         [OK] clip_{clip_index:03d}.mp4 ({size_mb:.1f} MB) — {query}")
                    downloaded.append(path)
                    clip_index += 1
                    downloaded_this_query += 1
                except Exception as e:
                    print(f"         [!] {e}")

        except Exception as e:
            print(f"         [!] Query failed: {e}")

    random.shuffle(downloaded)  # Randomise order so related clips don't cluster
    print(f"    [OK] {len(downloaded)} unique video clips ready.")
    return downloaded


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3B — BUILD OVERLAY FRAME (text over video frame)
# ══════════════════════════════════════════════════════════════════════════════

def build_overlay(title: str, subtitle: str) -> Image.Image:
    """Pre-render title bar + subtitle text as a transparent RGBA overlay."""

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # ── Top gradient bar ──────────────────────────────────────────────────────
    for y in range(80):
        alpha = int(180 * (1 - y / 80))
        draw.rectangle([0, y, WIDTH, y + 1], fill=(0, 0, 0, alpha))

    # ── Bottom gradient bar (for subtitle) ───────────────────────────────────
    for y in range(HEIGHT - 150, HEIGHT):
        alpha = int(220 * ((y - (HEIGHT - 150)) / 150))
        draw.rectangle([0, y, WIDTH, y + 1], fill=(0, 0, 0, alpha))

    # ── Gold accent top line ──────────────────────────────────────────────────
    draw.rectangle([0, 0, WIDTH, 4], fill=(*ACCENT_COLOR, 255))

    # ── Channel name top left ─────────────────────────────────────────────────
    try:
        font_ch = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        font_ch = ImageFont.load_default()

    draw.text((18, 12), f"⚡ {CHANNEL_NAME.upper()}", font=font_ch, fill=(*ACCENT_COLOR, 230))

    # ── Subtitle text (centered, bottom) ─────────────────────────────────────
    try:
        font_sub = ImageFont.truetype("arialbd.ttf", 40)
    except Exception:
        font_sub = ImageFont.load_default()

    wrapped = textwrap.fill(subtitle, width=52)
    lines = wrapped.split("\n")
    line_h = 50
    total_h = len(lines) * line_h
    y_start = HEIGHT - 130 - total_h // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_sub)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        # Shadow
        draw.text((x + 2, y_start + 2), line, font=font_sub, fill=(0, 0, 0, 220))
        # Main text
        draw.text((x, y_start), line, font=font_sub, fill=(255, 255, 255, 255))
        y_start += line_h

    return overlay


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3C — ASSEMBLE VIDEO
# ══════════════════════════════════════════════════════════════════════════════

def download_background_music(url: str = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gathering%20Darkness.mp3", output_path: str = "background_music.mp3"):
    """Download background music if not already present."""
    if os.path.exists(output_path):
        return output_path
    print("    Downloading cinematic background music...")
    try:
        r = requests.get(url, timeout=60)
        with open(output_path, "wb") as f:
            f.write(r.content)
        print(f"    [OK] Background music downloaded: {output_path}")
        return output_path
    except Exception as e:
        print(f"    [!] Failed to download background music: {e}")
        return None

def create_video(script_text: str, title: str, audio_path: str, output_path: str, video_paths: list) -> str:
    """Stitch Pexels video clips with overlays, voiceover, and background music into final MP4."""

    print("\n[3/4] Assembling documentary video...")

    voiceover = AudioFileClip(audio_path)
    total_duration = voiceover.duration
    print(f"    Voiceover duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    # ── Pre-load and normalise all clips ─────────────────────────────────────
    print(f"    Pre-loading {len(video_paths)} source clips...")
    loaded_clips = []
    for path in video_paths:
        try:
            raw = VideoFileClip(path)
            raw_ratio = raw.w / raw.h
            target_ratio = WIDTH / HEIGHT
            if raw_ratio > target_ratio:
                new_h = HEIGHT
                new_w = int(HEIGHT * raw_ratio)
            else:
                new_w = WIDTH
                new_h = int(WIDTH / raw_ratio)
            raw = raw.with_effects([vfx.Resize(new_size=(new_w, new_h))])
            lft = (new_w - WIDTH) // 2
            top = (new_h - HEIGHT) // 2
            raw = raw.with_effects([vfx.Crop(x1=lft, y1=top, x2=lft + WIDTH, y2=top + HEIGHT)])
            if raw.duration >= 2:
                loaded_clips.append(raw)
        except Exception as e:
            print(f"    [!] Skipping {path}: {e}")

    if not loaded_clips:
        print("    [!] No usable clips — using solid background.")

    # ── Sentence-level subtitle chunks (natural breaks) ───────────────────────
    import re
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    chunks = []
    for sent in sentences:
        words = sent.split()
        for j in range(0, len(words), 12):
            chunks.append(" ".join(words[j: j + 12]))
    chunks = [c for c in chunks if c.strip()]

    chunk_dur = total_duration / len(chunks)
    print(f"    {len(chunks)} subtitle chunks @ {chunk_dur:.1f}s each | {len(loaded_clips)} source clips")

    # ── Assemble Background Video (Transitions every 4 seconds) ──────────────────
    print("    Assembling visual background clips (cutting every 4 seconds)...")
    bg_duration = 4.0
    num_bg_segments = int(total_duration / bg_duration) + 1
    bg_clips = []
    
    if loaded_clips:
        for i in range(num_bg_segments):
            src = random.choice(loaded_clips)
            max_start = max(0.0, src.duration - bg_duration - 0.1)
            st = round(random.uniform(0.0, max_start), 2)
            end = st + bg_duration
            
            try:
                sub = src.subclipped(st, end)
                if sub.duration < bg_duration:
                    sub = sub.with_effects([vfx.Loop(duration=bg_duration)])
                bg_clips.append(sub)
            except Exception as e:
                print(f"    [!] Subclip failed on segment {i}: {e}. Retrying with fallback color.")
                bg_clips.append(ColorClip(size=(WIDTH, HEIGHT), color=BG_COLOR, duration=bg_duration))
        
        bg_video = concatenate_videoclips(bg_clips, method="chain").subclipped(0, total_duration)
    else:
        bg_video = ColorClip(size=(WIDTH, HEIGHT), color=BG_COLOR, duration=total_duration)

    # ── Pre-render Subtitle Overlay Images ──────────────────────────────────────
    print(f"    Pre-rendering subtitle overlays in memory...")
    subtitle_overlays = []
    for i, chunk in enumerate(chunks):
        start_t = i * chunk_dur
        end_t = start_t + chunk_dur
        overlay_img = build_overlay(title, chunk)
        overlay_arr = np.array(overlay_img)
        subtitle_overlays.append((start_t, end_t, overlay_arr))

    # A single frame-level function that dynamically selects and overlays the text based on current time
    def draw_subtitles(get_frame, t):
        frame = get_frame(t)
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
            
        # Find matching overlay
        active_ov = None
        for start_t, end_t, ov_arr in subtitle_overlays:
            if start_t <= t < end_t:
                active_ov = ov_arr
                break
                
        if active_ov is None:
            return frame

        # Apply overlay using PIL
        bg = Image.fromarray(frame).convert("RGBA")
        if bg.width != WIDTH or bg.height != HEIGHT:
            bg = bg.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        bg.alpha_composite(Image.fromarray(active_ov))
        return np.array(bg.convert("RGB"))

    # Apply the transform to the background video
    final_video = bg_video.transform(draw_subtitles)

    # ── Mix Background Music & Voiceover ─────────────────────────────────────
    print("    Mixing audio track with background music...")
    bg_music_path = download_background_music()
    if bg_music_path and os.path.exists(bg_music_path):
        try:
            bg_audio = AudioFileClip(bg_music_path)
            # Loop bg audio to cover total duration
            audio_segments = [bg_audio] * (int(total_duration / bg_audio.duration) + 1)
            from moviepy.audio.AudioClip import concatenate_audioclips
            bg_audio_looped = concatenate_audioclips(audio_segments).subclipped(0, total_duration)
            bg_audio_final = bg_audio_looped.multiply_volume(0.12)
            
            from moviepy.audio.AudioClip import CompositeAudioClip
            mixed_audio = CompositeAudioClip([voiceover, bg_audio_final])
            final_video = final_video.with_audio(mixed_audio)
            print("    [OK] Background music mixed in successfully.")
        except Exception as e:
            print(f"    [!] Failed to mix background music: {e}. Using raw voiceover.")
            final_video = final_video.with_audio(voiceover)
    else:
        final_video = final_video.with_audio(voiceover)

    # ── Render Video ─────────────────────────────────────────────────────────
    print(f"    Rendering to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        logger=None,
    )

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"    [OK] Video saved -> {output_path} ({size_mb:.1f} MB)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — UPLOAD TO YOUTUBE
# ══════════════════════════════════════════════════════════════════════════════

def get_youtube_client():
    """Authenticate and return YouTube API client. Reuses saved token."""
    creds = None
    token_path = "token.pickle"

    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path: str, title: str, description: str, tags: list, chapters: list) -> str:
    """Upload the final video to YouTube with full metadata."""

    print("\n[4/4] Uploading to YouTube...")
    youtube = get_youtube_client()
    print("    [OK] Authenticated!")

    # Build chapter timestamps for description
    chapter_text = "\n\n⏱️ CHAPTERS:\n0:00 Introduction"
    if chapters:
        minutes = 1
        for ch in chapters:
            chapter_text += f"\n{minutes}:00 {ch}"
            minutes += 2

    full_description = description + chapter_text + "\n\n#History #Mysteries #Documentary"

    body = {
        "snippet": {
            "title": title,
            "description": full_description,
            "tags": tags,
            "categoryId": "27",      # Education category — better CPM than Entertainment
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=5)
            if status:
                pct = int(status.progress() * 100)
                print(f"    Uploading... {pct}%", end="\r")
        except Exception as e:
            print(f"\n    [!] Upload error: {e}. Retrying in 15s...")
            time.sleep(15)

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n    [OK] Uploaded! Watch at: {url}")
    return url


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(format_key: str = "mystery", topic: str = ""):
    print("=" * 58)
    print("  The Vault — YouTube Documentary Bot")
    print("=" * 58)

    # 1. Generate script
    data = generate_script(format_key, topic)

    # 2. Generate voiceover
    audio_path = generate_voiceover(data["script"])

    # 3. Download Pexels video clips
    queries = data.get("pexels_queries", [
        "ancient ruins stone",
        "dark forest fog night",
        "stormy ocean dramatic",
        "old library books candle",
        "mysterious cave underground",
        "medieval castle stone"
    ])
    video_paths = download_stock_videos(queries)

    # 4. Assemble video
    video_path = create_video(
        data["script"], data["title"], audio_path, OUTPUT_FILE, video_paths
    )

    # Build chapter timestamps for description
    chapter_text = "\n\n⏱️ CHAPTERS:\n0:00 Introduction"
    chapters = data.get("chapters", [])
    if chapters:
        minutes = 2
        for ch in chapters:
            chapter_text += f"\n{minutes}:00 {ch}"
            minutes += 4

    full_description = data["description"] + chapter_text + "\n\n#History #Mysteries #Documentary"

    # Save Upload Metadata to a text file for manual upload convenience
    meta_file = "upload_metadata.txt"
    try:
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(f"TITLE:\n{data['title']}\n\n")
            f.write(f"DESCRIPTION:\n{full_description}\n\n")
            f.write(f"TAGS:\n{data['tags']}\n")
        print(f"\n[OK] Upload metadata saved to: {meta_file}")
    except Exception as e:
        print(f"    [!] Failed to save upload metadata file: {e}")

    print("\n" + "=" * 58)
    print("  [DONE] Documentary video generation complete!")
    print(f"  Video file: {os.path.abspath(video_path)}")
    print(f"  Metadata file: {os.path.abspath(meta_file)}")
    print(f"  Use the title, description, and tags in {meta_file} when uploading.")
    print("=" * 58)

    # Cleanup temp audio
    for f in ["voiceover.mp3"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


if __name__ == "__main__":
    # ── Choose a format ──────────────────────────────────────────────────────
    # mystery | conspiracy | dark_history | ancient | disappear
    FORMAT = "mystery"

    # ── Leave blank for AI to choose topic, or set a specific one ───────────
    TOPIC  = ""     # e.g. "The Bermuda Triangle" or "The Dyatlov Pass incident"

    run_pipeline(FORMAT, TOPIC)

import os
import sys
import re
import json
import tempfile
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from cross_linker import find_related_notes, inject_related_section

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
DICT_FILE = os.path.join(VAULT_PATH, "Tag Dictionary.md")
DEST_FOLDER = os.environ.get("DESTINATION_FOLDER", "Knowledge").strip("/")
KNOWLEDGE_DIR = os.path.join(VAULT_PATH, DEST_FOLDER) if DEST_FOLDER else VAULT_PATH
TRANSCRIPT_DIR = os.path.join(VAULT_PATH, "Attachments", "Youtube Transcripts")

def clean_for_filename(text):
    clean_text = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower())
    return clean_text.strip('-')[:80]

def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    raise ValueError("Could not extract YouTube Video ID from URL.")

def get_video_title(url):
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        match = re.search(r'<title>(.*?)</title>', response.text)
        if match:
            return match.group(1).replace(" - YouTube", "").strip()
    except Exception:
        pass
    return "YouTube Video"

def load_dictionary():
    core_tags = []
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r'-\s*`([^`]+)`', line)
                if match:
                    core_tags.append(match.group(1).strip())
    return core_tags

def call_llm_for_note(transcript_text, title, url, core_tags):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found in .env.")

    current_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    prompt = f"""
You are an expert analyst extracting knowledge for a personal Obsidian "Second Brain".
Here is the raw, messy, unpunctuated text transcript of a YouTube video titled "{title}":

{transcript_text[:15000]}

Your goal is to extract the core value and output a PERFECTLY formatted Markdown note.

REQUIREMENTS:
1. Select exactly 2 to 4 TOPIC TAGS. You MUST prioritize these tags from the Master Dictionary: {', '.join(core_tags)}. Do not use format tags like 'youtube', 'video'.
2. Follow the exact Markdown template below.

---
type: Transcript
title: "{title}"
description: "{{One-sentence summary of the video's core message}}"
domain: Knowledge
tags: [tag1, tag2]
timestamp: {current_timestamp}
---

# 🎥 {title}

## 📌 3-Line Summary
[Provide a punchy 3-line summary of the video's core message]

## 💡 Key Takeaways
- **[Concept]** : [Explanation]
- **[Concept]** : [Explanation]

## 🚀 Actionable Advice
- **[Action]** : [Explanation]

---
**🔗 Links & Appendix:**
- 📺 Original Video : {url}
- 📜 Raw Transcript : [[{clean_for_filename(title)}-raw-transcript]]
"""

    print("🧠 OpenAI is reading the transcript and generating the note...")
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert knowledge synthesizer. Output ONLY the raw markdown text for the note. Do not wrap it in ```markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }
    
    response = requests.post(api_url, headers=headers, json=data)
    response.raise_for_status()
    note_content = response.json()["choices"][0]["message"]["content"]
    
    if note_content.startswith("```markdown"):
        note_content = note_content[11:]
    if note_content.startswith("```"):
        note_content = note_content[3:]
    if note_content.endswith("```"):
        note_content = note_content[:-3]
        
    return note_content.strip()

def whisper_fallback(url, video_id):
    """Download audio via yt-dlp and transcribe via OpenAI Whisper API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env. Cannot use Whisper fallback.")
        return None

    tmp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(tmp_dir, f"{video_id}.m4a")

    print("📥 Downloading audio track via yt-dlp...")
    cmd = ["yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", audio_path, "--no-playlist", url]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(audio_path):
        # Try finding yt-dlp in python's bin directory
        py_bin_ytdlp = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
        if os.path.exists(py_bin_ytdlp):
            cmd[0] = py_bin_ytdlp
            result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(audio_path):
        print(f"❌ yt-dlp download failed: {result.stderr[:200]}")
        return None

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"✅ Audio downloaded ({file_size_mb:.1f} MB)")

    # Whisper API 25MB limit - trim if needed
    if file_size_mb > 25:
        print("⚠️ Audio file exceeds 25MB. Trimming to first 60 minutes...")
        trimmed_path = os.path.join(tmp_dir, f"{video_id}_trimmed.m4a")
        subprocess.run(
            ["ffmpeg", "-i", audio_path, "-t", "3600", "-c", "copy", trimmed_path, "-y"],
            capture_output=True
        )
        if os.path.exists(trimmed_path):
            audio_path = trimmed_path

    print("🎤 Sending to OpenAI Whisper for transcription...")
    try:
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (os.path.basename(audio_path), audio_file, "audio/m4a")},
                data={"model": "whisper-1", "response_format": "text"}
            )
            response.raise_for_status()
            transcript_text = response.text
    except Exception as e:
        print(f"❌ Whisper API failed: {e}")
        return None
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"✅ Whisper transcription complete ({len(transcript_text)} characters)")
    return transcript_text

def parse_tags_from_yaml(content):
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not yaml_match:
        return []
    tags_match = re.search(r'tags:\s*\[(.*?)\]', yaml_match.group(1))
    if not tags_match:
        return []
    return [t.strip().strip('"').strip("'").lower() for t in tags_match.group(1).split(',') if t.strip()]

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 youtube_workflow.py <URL>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    print(f"\n🎥 Step 1: Extracting YouTube data for {target_url}...")
    video_id = extract_video_id(target_url)
    title = get_video_title(target_url)
    safe_title = clean_for_filename(title)
    
    print(f"✅ Found Video: {title}")
    
    transcript_text = None
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list_obj = ytt_api.list(video_id)
        
        # Try French, English, or fallback to first available transcript
        try:
            transcript = transcript_list_obj.find_transcript(['fr', 'en'])
        except Exception:
            transcript = next(iter(transcript_list_obj))
            
        transcript_data = transcript.fetch()
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_data)
        print("✅ Successfully downloaded raw transcript from YouTube.")
    except Exception as e:
        print(f"⚠️ Transcript API failed: {e}")
        print("🎤 Falling back to audio download + Whisper transcription...")
        transcript_text = whisper_fallback(target_url, video_id)
        if not transcript_text:
            print("❌ Both transcript methods failed. Cannot process this video.")
            sys.exit(1)
        
    print("\n🧠 Step 2: LLM Processing (Summarization & Tagging)...")
    core_tags = load_dictionary()
    note_content = call_llm_for_note(transcript_text, title, target_url, core_tags)
    
    print("\n💾 Step 3: Saving to Obsidian...")
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    knowledge_file = os.path.join(KNOWLEDGE_DIR, f"{safe_title}.md")
    with open(knowledge_file, 'w', encoding='utf-8') as f:
        f.write(note_content)
        
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    raw_transcript_file = os.path.join(TRANSCRIPT_DIR, f"{safe_title}-raw-transcript.md")
    with open(raw_transcript_file, 'w', encoding='utf-8') as f:
        f.write(f"# Raw Transcript: {title}\n\nOriginal Video: {target_url}\n\n---\n\n")
        f.write(transcript_text)
        
    print(f"🎉 Workflow complete!")
    print(f"📄 Summary saved to: Knowledge/{safe_title}.md")
    print(f"📜 Raw transcript saved to: Attachments/Youtube Transcripts/{safe_title}-raw-transcript.md")
    
    # Cross-link: find related notes by tag overlap
    print("\n🔗 Step 4: Cross-linking with related notes...")
    note_tags = parse_tags_from_yaml(note_content)
    if note_tags:
        matches = find_related_notes(note_tags, exclude_filename=safe_title)
        if matches:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            linked_content = inject_related_section(saved_content, matches)
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                f.write(linked_content)
            print(f"✅ Linked to {len(matches)} related note(s).")
        else:
            print("ℹ️ No related notes found (need >= 2 shared tags).")

if __name__ == "__main__":
    main()

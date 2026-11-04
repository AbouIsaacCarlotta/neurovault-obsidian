import os
import sys
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
from pydub import AudioSegment
from dotenv import load_dotenv
from cross_linker import find_related_notes, inject_related_section

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
DICT_FILE = os.path.join(VAULT_PATH, "Tag Dictionary.md")
KNOWLEDGE_DIR = os.path.join(VAULT_PATH, "Knowledge")
ATTACHMENTS_DIR = os.path.join(VAULT_PATH, "Attachments", "Podcasts Transcripts")

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==========================================
# UTILS
# ==========================================

def clean_for_match(text):
    """Cleans text for RSS feed matching (lowercase, alphanumeric only)."""
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

def clean_for_filename(text):
    """Cleans text to make a valid filename (using dashes)."""
    clean_text = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower())
    return clean_text.strip('-')[:80]

def load_dictionary():
    core_tags = []
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r'-\s*`([^`]+)`', line)
                if match:
                    core_tags.append(match.group(1).strip())
    return core_tags

# ==========================================
# STEP 1: EXTRACT MP3 URL
# ==========================================

def get_podcast_mp3_url(apple_url):
    """
    Extracts the direct MP3 file URL from an Apple Podcasts link.
    """
    match_id = re.search(r'id(\d+)', apple_url)
    if not match_id:
        raise ValueError("Could not find podcast ID in the URL.")
    
    podcast_id = match_id.group(1)
    match_slug = re.search(r'podcast/([^/]+)/id', apple_url)
    target_slug = unquote(match_slug.group(1)) if match_slug else None

    url_api = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
    response_api = requests.get(url_api, headers=BROWSER_HEADERS).json()
    
    if not response_api['results']:
        raise ValueError("Podcast not found on iTunes.")
        
    url_rss = response_api['results'][0]['feedUrl']
    response_rss = requests.get(url_rss, headers=BROWSER_HEADERS)
    root = ET.fromstring(response_rss.content)
    
    for item in root.findall('.//item'):
        title = item.find('title').text
        if not title:
            continue
            
        if target_slug:
            clean_title = clean_for_match(title)
            clean_slug = clean_for_match(target_slug)
            if clean_slug in clean_title or clean_title in clean_slug:
                audio_tag = item.find('enclosure')
                if audio_tag is not None:
                    return {"title": title, "mp3_url": audio_tag.get('url')}
        else:
            audio_tag = item.find('enclosure')
            if audio_tag is not None:
                return {"title": title, "mp3_url": audio_tag.get('url')}
                
    raise ValueError("No matching MP3 found in the RSS feed.")


# ==========================================
# STEP 2: DOWNLOAD AUDIO
# ==========================================

def download_mp3(mp3_url, output_filename="podcast.mp3", output_dir="Audio files"):
    """
    Downloads the MP3 file using streaming to avoid high RAM usage.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, output_filename)
    
    print(f"📥 Downloading from: {mp3_url}")
    
    with requests.get(mp3_url, headers=BROWSER_HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
    print(f"✅ File successfully downloaded to: {file_path}")
    return file_path


# ==========================================
# STEP 3: TRANSCRIPTION (OPENAI WHISPER)
# ==========================================

def transcribe_audio(file_path, api_key=None):
    """
    Transcribes a long audio file into text using OpenAI Whisper API via requests.
    Splits the audio into chunks if the file exceeds the 25MB limit.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API key is missing. Set OPENAI_API_KEY in .env.")
    
    def call_whisper_api(chunk_path):
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {key}"}
        with open(chunk_path, "rb") as audio_file:
            files = {"file": audio_file}
            data = {"model": "whisper-1"}
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            return response.json()["text"]

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"🎙️ Starting transcription. File size: {file_size_mb:.2f} MB")
    
    if file_size_mb <= 24:
        return call_whisper_api(file_path)

    print("✂️ File exceeds 25MB, chunking in progress (this will take a moment)...")
    audio = AudioSegment.from_file(file_path)
    
    chunk_length_ms = 20 * 60 * 1000 
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    
    full_transcript = ""
    
    for i, chunk in enumerate(chunks):
        chunk_name = f"chunk_{i}.mp3"
        chunk.export(chunk_name, format="mp3")
        print(f"   -> Transcribing part {i+1}/{len(chunks)}...")
        
        text_part = call_whisper_api(chunk_name)
        full_transcript += text_part + " "
            
        try:
            os.remove(chunk_name)
        except Exception:
            pass
        
    print("✅ Transcription fully completed!")
    return full_transcript.strip()


# ==========================================
# STEP 4: SUMMARY & NOTE CREATION (OBSIDIAN)
# ==========================================

def generate_obsidian_note(transcript, podcast_title, original_url, core_tags, api_key=None):
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API key is missing in .env.")

    print("🧠 AI is analyzing and summarizing the podcast (takes about 10-20 seconds)...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    safe_title = clean_for_filename(podcast_title)
    current_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    prompt = f"""
You are an expert assistant tasked with extracting the core value from a podcast.
Here is the complete transcript of a podcast titled "{podcast_title}".
Create a clear, structured note ready to be integrated into the user's Obsidian "Second Brain".

REQUIREMENTS:
1. Select exactly 2 to 4 TOPIC TAGS. You MUST prioritize these tags from the Master Dictionary: {', '.join(core_tags)}. Do not use format tags like 'podcast', 'transcript'.
2. Follow the exact Markdown template below.

---
type: Transcript
title: "{podcast_title}"
description: "{{One-sentence summary of the podcast episode's core message}}"
domain: Knowledge
tags: [tag1, tag2]
timestamp: {current_timestamp}
---

# 🎙️ {podcast_title}

## 📌 3-Line Summary
[Provide a punchy 3-line summary of the episode]

## 💡 Main Ideas
- **[Concept Name]** : [Explanation]

## ✍️ Memorable Quotes
- "[Quote]"

## 🚀 Actions / Takeaways
- **[Action]** : [Explanation]

---
**🔗 Links & Appendix:**
- 📄 Full Transcript : [[{safe_title}.txt]]
- 🎧 Original Link : {original_url}

**Linked Concepts:** 
[[Knowledge MOC]]
"""

    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert in information synthesis. Output ONLY the raw markdown note without markdown code blocks."},
            {"role": "user", "content": prompt + f"\n\nHere is the transcript:\n{transcript[:15000]}"}
        ],
        "temperature": 0.4
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    note_content = response.json()["choices"][0]["message"]["content"]

    if note_content.startswith("```markdown"):
        note_content = note_content[11:]
    if note_content.startswith("```"):
        note_content = note_content[3:]
    if note_content.endswith("```"):
        note_content = note_content[:-3]
    
    return note_content.strip()


def parse_tags_from_yaml(content):
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not yaml_match:
        return []
    tags_match = re.search(r'tags:\s*\[(.*?)\]', yaml_match.group(1))
    if not tags_match:
        return []
    return [t.strip().strip('"').strip("'").lower() for t in tags_match.group(1).split(',') if t.strip()]


# ==========================================
# WORKFLOW EXECUTION
# ==========================================
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) < 2:
        print("Usage: python3 podcast_workflow.py <APPLE_PODCAST_URL>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    try:
        print("\n--- Step 1: Extracting MP3 URL ---")
        podcast_info = get_podcast_mp3_url(target_url)
        title = podcast_info['title']
        safe_title = clean_for_filename(title)
        print(f"Title found: {title}")
        
        print("\n--- Step 2: Downloading Audio ---")
        mp3_path = download_mp3(podcast_info['mp3_url'], output_filename=f"{safe_title}.mp3", output_dir="Audio files")
        
        print("\n--- Step 3: Transcribing Audio ---")
        full_transcript = transcribe_audio(mp3_path)
        
        print("\n--- Step 4: Saving Transcript & Generating Obsidian Note ---")
        os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
        transcript_path = os.path.join(ATTACHMENTS_DIR, f"{safe_title}.txt")
        with open(transcript_path, "w", encoding='utf-8') as f:
            f.write(full_transcript)
            
        core_tags = load_dictionary()
        note_content = generate_obsidian_note(full_transcript, title, target_url, core_tags)
        
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        knowledge_file = os.path.join(KNOWLEDGE_DIR, f"{safe_title}.md")
        with open(knowledge_file, "w", encoding='utf-8') as f:
            f.write(note_content)
        print(f"📝 Obsidian note successfully created: {knowledge_file}")

        # Cross-linking
        print("\n🔗 Step 5: Cross-linking with related notes...")
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

        print(f"\n🎉 Workflow complete! Your note is ready at: {knowledge_file}")

    except Exception as e:
        print(f"❌ Error: {e}")

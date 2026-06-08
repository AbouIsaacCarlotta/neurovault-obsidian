import os
import sys
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()
VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")

# ==========================================
# UTILS
# ==========================================

def clean_for_match(text):
    """Cleans text for RSS feed matching (lowercase, alphanumeric only)."""
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

def clean_for_filename(text):
    """Cleans text to make a valid filename (using dashes)."""
    clean_text = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower())
    return clean_text.strip('-')

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
    response_api = requests.get(url_api).json()
    
    if not response_api['results']:
        raise ValueError("Podcast not found on iTunes.")
        
    url_rss = response_api['results'][0]['feedUrl']
    response_rss = requests.get(url_rss)
    root = ET.fromstring(response_rss.content)
    
    for item in root.findall('.//item'):
        title = item.find('title').text
        if not title: continue
            
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
    
    with requests.get(mp3_url, stream=True) as r:
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
        raise ValueError("OpenAI API key is missing. Set the OPENAI_API_KEY environment variable.")
    
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
            
        os.remove(chunk_name)
        
    print("✅ Transcription fully completed!")
    return full_transcript.strip()


# ==========================================
# STEP 4: SUMMARY & NOTE CREATION (OBSIDIAN)
# ==========================================

def generate_obsidian_note(transcript, podcast_title, original_url, api_key=None, output_dir=None):
    """
    Sends the transcript to OpenAI to generate a structured summary in Markdown format.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API key is missing.")
        
    if output_dir is None:
        output_dir = os.path.join(VAULT_PATH, "Knowledge")

    print("🧠 AI is analyzing and summarizing the podcast (takes about 10-20 seconds)...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    safe_title = clean_for_filename(podcast_title)
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    prompt = f"""
You are an expert assistant tasked with extracting the core value from a podcast.
Here is the complete transcript of a podcast titled "{podcast_title}".
Create a clear, structured note ready to be integrated into the user's Obsidian "Second Brain".

You MUST strictly follow this exact Markdown template, replacing the bracketed placeholders with your analysis:

---
type: Transcript
domain: Knowledge
tags: [podcast, transcript]
date_saved: {current_date}
---

# 🎙️ {podcast_title}

## 📌 3-Line Summary
[Provide a punchy 3-line summary of the episode]

## 💡 Main Ideas
[List the main ideas using this format:]
- **[Idea Name]** : [Explanation]

## ✍️ Memorable Quotes
[List memorable quotes if applicable:]
- "[Quote]"

## 🚀 Actions / Takeaways
[List actionable takeaways:]
- **[Action]** : [Explanation]

---
**🔗 Links & Appendix:**
- 📄 Full Transcript : [[{safe_title}.txt]]
- 🎧 Original Link : {original_url}

**Linked Concepts:** 
[[Knowledge MOC]]

---
Here is the transcript:
{transcript}
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert in information synthesis."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    note_content = response.json()["choices"][0]["message"]["content"]
    
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{safe_title}.md")
    
    with open(file_path, "w") as f:
        f.write(note_content)
        
    print(f"📝 Obsidian note successfully created: {file_path}")
    return file_path


# ==========================================
# WORKFLOW EXECUTION
# ==========================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: doppler run -- python3 podcast_workflow.py <APPLE_PODCAST_URL>")
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
        # Save transcript to attachments folder
        os.makedirs("attachments", exist_ok=True)
        transcript_path = os.path.join("attachments", f"{safe_title}.txt")
        with open(transcript_path, "w") as f:
            f.write(full_transcript)
        print("\n--- Step 4: Generating Obsidian Note ---")
        note_path = generate_obsidian_note(full_transcript, title, target_url)
        print(f"\n🎉 Workflow complete! Your note is ready at: {note_path}")
        
        # Play a sound and show a desktop notification
        os.system('osascript -e \'display notification "Podcast Workflow Complete! Your note is ready." with title "Podcast Automation" sound name "Glass"\'')

    except Exception as e:
        print(f"Error: {e}")

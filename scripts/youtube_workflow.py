import os
import sys
import re
import json
import requests
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
DICT_FILE = os.path.join(VAULT_PATH, "Tag Dictionary.md")
KNOWLEDGE_DIR = os.path.join(VAULT_PATH, "Knowledge")
TRANSCRIPT_DIR = os.path.join(VAULT_PATH, "Attachments", "Youtube Transcripts")

def clean_for_filename(text):
    clean_text = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower())
    return clean_text.strip('-')

def extract_video_id(url):
    # Matches youtu.be/ID, youtube.com/watch?v=ID, etc.
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    raise ValueError("Could not extract YouTube Video ID from URL.")

def get_video_title(url):
    try:
        response = requests.get(url)
        match = re.search(r'<title>(.*?)</title>', response.text)
        if match:
            # YouTube titles usually end with " - YouTube"
            title = match.group(1).replace(" - YouTube", "").strip()
            return title
    except Exception:
        pass
    return "YouTube Video"

def load_dictionary():
    core_tags = []
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, 'r') as f:
            for line in f:
                match = re.search(r'-\s*`([^`]+)`', line)
                if match:
                    core_tags.append(match.group(1).strip())
    return core_tags

def call_llm_for_note(transcript_text, title, url, core_tags):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found. Run via Doppler.")

    prompt = f"""
You are an expert analyst extracting knowledge for a personal Obsidian "Second Brain".
Here is the raw, messy, unpunctuated text transcript of a YouTube video titled "{title}":

{transcript_text[:15000]}

Your goal is to extract the core value and output a PERFECTLY formatted Markdown note.

REQUIREMENTS:
1. Select exactly 2 to 4 TOPIC TAGS. You MUST prioritize these tags from the Master Dictionary: {', '.join(core_tags)}. Do not use format tags like 'youtube'.
2. Follow the exact Markdown template below.

---
type: Transcript
domain: Knowledge
tags: [tag1, tag2]
date_saved: {{current_date}}
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

**Linked Concepts:** 
[[Knowledge MOC]]
"""

    current_date = datetime.now().strftime('%Y-%m-%d')
    prompt = prompt.replace("{{current_date}}", current_date)

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

def main():
    if len(sys.argv) < 2:
        print("Usage: doppler run -- python3 youtube_workflow.py <URL>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    print(f"\n🎥 Step 1: Extracting YouTube data for {target_url}...")
    video_id = extract_video_id(target_url)
    title = get_video_title(target_url)
    safe_title = clean_for_filename(title)
    
    print(f"✅ Found Video: {title}")
    
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list_obj = ytt_api.list(video_id)
        
        # Prioritize French, then fallback to English
        transcript = transcript_list_obj.find_transcript(['fr', 'en'])
        transcript_data = transcript.fetch()
        
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_data)
        print("✅ Successfully downloaded raw transcript from YouTube.")
    except Exception as e:
        print(f"❌ Error downloading transcript: {e}")
        print("Note: If the video has subtitles disabled, this will fail.")
        sys.exit(1)
        
    print("\n🧠 Step 2: LLM Processing (Summarization & Tagging)...")
    core_tags = load_dictionary()
    note_content = call_llm_for_note(transcript_text, title, target_url, core_tags)
    
    print("\n💾 Step 3: Saving to Obsidian...")
    
    # Save the polished Knowledge Note
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    knowledge_file = os.path.join(KNOWLEDGE_DIR, f"{safe_title}.md")
    with open(knowledge_file, 'w') as f:
        f.write(note_content)
        
    # Save the messy raw transcript
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    raw_transcript_file = os.path.join(TRANSCRIPT_DIR, f"{safe_title}-raw-transcript.md")
    with open(raw_transcript_file, 'w') as f:
        f.write(f"# Raw Transcript: {title}\n\nOriginal Video: {target_url}\n\n---\n\n")
        f.write(transcript_text)
        
    print(f"🎉 Workflow complete!")
    print(f"📄 Summary saved to: Knowledge/{safe_title}.md")
    print(f"📜 Raw transcript saved to: Attachments/Youtube Transcripts/{safe_title}-raw-transcript.md")
    
    os.system(f'osascript -e \'display notification "YouTube video summarized and saved to Vault!" with title "YouTube Workflow Complete" sound name "Glass"\'')

if __name__ == "__main__":
    main()

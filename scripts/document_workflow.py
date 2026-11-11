import os
import sys
import re
import requests
from datetime import datetime
from markitdown import MarkItDown
from dotenv import load_dotenv
from cross_linker import find_related_notes, inject_related_section

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
DICT_FILE = os.path.join(VAULT_PATH, "Tag Dictionary.md")
DEST_FOLDER = os.environ.get("DESTINATION_FOLDER", "Knowledge").strip("/")
KNOWLEDGE_DIR = os.path.join(VAULT_PATH, DEST_FOLDER) if DEST_FOLDER else VAULT_PATH
TRANSCRIPT_DIR = os.path.join(VAULT_PATH, "Attachments", "Document Transcripts")

def clean_for_filename(text):
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

def call_llm_for_note(document_text, filename, core_tags):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found in .env.")

    current_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    prompt = f"""
You are an expert analyst extracting knowledge for a personal Obsidian "Second Brain".
Here is the raw Markdown content extracted from a document titled "{filename}":

{document_text[:15000]}

Your goal is to extract the core value and output a PERFECTLY formatted Markdown note.

REQUIREMENTS:
1. Extract the actual Title of the document from its content (do not just use the raw filename).
2. Classify the content. Is it an "Article" (a research paper, essay, news, thought piece) or a "Resource" (a technical manual, dataset, company deck)?
3. Select exactly 2 to 4 TOPIC TAGS. You MUST prioritize these tags from the Master Dictionary: {', '.join(core_tags)}. Do not use format tags like 'pdf', 'doc', 'document'.
4. Follow the exact Markdown template below.

---
type: {{Classify as either "Article" or "Resource"}}
title: "{{TITLE}}"
description: "{{One-sentence summary of the document}}"
domain: Knowledge
tags: [tag1, tag2]
timestamp: {current_timestamp}
---

# 📄 {{TITLE}}

## 📌 3-Line Summary
[Provide a punchy 3-line summary of what this document is about]

## 💡 Main Ideas / Core Value
- **[Concept Name]** : [Explanation]

## 🚀 Actions / Takeaways
- **[Action]** : [Explanation]

---
**🔗 Links & Appendix:**
- 📁 Source File : [[{filename}]]
- 📜 Raw Text : [[{clean_for_filename(filename)}-raw-text]]
"""

    print("🧠 OpenAI is reading the document and generating the note...")
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert knowledge synthesizer. Output ONLY the raw markdown note without code block fences."},
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

def extract_title_from_note(note_content):
    match = re.search(r'# 📄 (.*)', note_content)
    if match:
        return match.group(1).strip()
    return "Document Note"

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
        print("Usage: python3 document_workflow.py <FILE_PATH>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        sys.exit(1)
        
    filename = os.path.basename(file_path)
    safe_title = clean_for_filename(filename)
    
    print(f"\n📄 Step 1: Converting document to Markdown with MarkItDown ({filename})...")
    md = MarkItDown()
    result = md.convert(file_path)
    document_text = result.text_content
    print("✅ Successfully parsed document into Markdown.")
    
    print("\n🧠 Step 2: LLM Processing (Summarization & Tagging)...")
    core_tags = load_dictionary()
    note_content = call_llm_for_note(document_text, filename, core_tags)
    
    print("\n💾 Step 3: Saving to Obsidian...")
    
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    knowledge_file = os.path.join(KNOWLEDGE_DIR, f"{safe_title}.md")
    with open(knowledge_file, 'w', encoding='utf-8') as f:
        f.write(note_content)
        
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    raw_text_file = os.path.join(TRANSCRIPT_DIR, f"{safe_title}-raw-text.md")
    with open(raw_text_file, 'w', encoding='utf-8') as f:
        f.write(f"# Raw Text: {filename}\n\n---\n\n")
        f.write(document_text)
        
    print(f"🎉 Workflow complete!")
    print(f"📄 Summary saved to: Knowledge/{safe_title}.md")
    print(f"📜 Raw text saved to: Attachments/Document Transcripts/{safe_title}-raw-text.md")
    
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

import os
import sys
import re
import json
import asyncio
import requests
from datetime import datetime
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv
from cross_linker import find_related_notes, inject_related_section

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
DICT_FILE = os.path.join(VAULT_PATH, "Tag Dictionary.md")
DEST_FOLDER = os.environ.get("DESTINATION_FOLDER", "Knowledge").strip("/")
OUTPUT_DIR = os.path.join(VAULT_PATH, DEST_FOLDER) if DEST_FOLDER else VAULT_PATH

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

def call_llm_for_note(markdown_content, url, core_tags):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found in .env.")

    current_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    prompt = f"""
You are an expert analyst extracting knowledge for a personal Obsidian "Second Brain".
Here is the raw Markdown content of an article scraped from the web:

{markdown_content[:15000]}

Your goal is to extract the core value and output a PERFECTLY formatted Markdown note.

REQUIREMENTS:
1. Extract the actual Title of the content.
2. Classify the content. Is it an "Article" (a blog post, essay, news, thought piece) or a "Resource" (a tool, GitHub repo, product landing page, dataset, company site)?
3. Select exactly 2 to 4 TOPIC TAGS. You MUST prioritize these tags from the Master Dictionary: {', '.join(core_tags)}. Do not use format tags like 'article', 'resource', 'web'.
4. Follow the exact Markdown template below.

---
type: {{Classify as either "Article" or "Resource"}}
title: "{{TITLE}}"
description: "{{One-sentence summary of the content}}"
domain: Knowledge
tags: [tag1, tag2]
timestamp: {current_timestamp}
---

# 📄 {{TITLE}}

## 📌 3-Line Summary
[Provide a punchy 3-line summary of what this is]

## 💡 Main Ideas / Core Value
- **[Point Name]** : [Explanation of the concept, feature, or idea]

## 🚀 Actions / Takeaways / Use Cases
- **[Action]** : [Explanation]

---
**🔗 Links & Appendix:**
- 🌐 Original Link : {url}
"""

    print("🧠 OpenAI is reading the article and generating the note...")
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert knowledge synthesizer. Output ONLY the raw markdown note without code block fencing."},
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
    return "Web Note"

def parse_tags_from_yaml(content):
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not yaml_match:
        return []
    tags_match = re.search(r'tags:\s*\[(.*?)\]', yaml_match.group(1))
    if not tags_match:
        return []
    return [t.strip().strip('"').strip("'").lower() for t in tags_match.group(1).split(',') if t.strip()]

async def crawl_url(url):
    print(f"\n🌐 Step 1: Crawling URL ({url})...")
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            print("✅ Successfully extracted clean Markdown from the website.")
            return result.markdown
        else:
            raise RuntimeError(f"Crawl failed: {result.error_message}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 url_workflow.py <URL>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    markdown = asyncio.run(crawl_url(target_url))
    
    print("\n🧠 Step 2: LLM Processing (Summarization & Tagging)...")
    core_tags = load_dictionary()
    note_content = call_llm_for_note(markdown, target_url, core_tags)
    
    print("\n💾 Step 3: Saving to Obsidian...")
    title = extract_title_from_note(note_content)
    safe_title = clean_for_filename(title)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUT_DIR, f"{safe_title}.md")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(note_content)
        
    # Cross-link: find related notes by tag overlap
    print("\n🔗 Step 4: Cross-linking with related notes...")
    note_tags = parse_tags_from_yaml(note_content)
    if note_tags:
        matches = find_related_notes(note_tags, exclude_filename=safe_title)
        if matches:
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            linked_content = inject_related_section(saved_content, matches)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(linked_content)
            print(f"✅ Linked to {len(matches)} related note(s).")
        else:
            print("ℹ️ No related notes found (need >= 2 shared tags).")

    print(f"🎉 Workflow complete! Your note is ready at: {file_path}")

if __name__ == "__main__":
    main()

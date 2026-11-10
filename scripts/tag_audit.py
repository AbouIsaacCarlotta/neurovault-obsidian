import os
import sys
import re
import json
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

VAULT = os.environ.get("VAULT_ABSOLUTE_PATH", "")
KNOWLEDGE_DIR = os.path.join(VAULT, "Knowledge") if VAULT else ""
DICT_FILE = os.path.join(VAULT, "Tag Dictionary.md") if VAULT else ""

BANNED_FORMAT_TAGS = {"podcast", "transcript", "article", "video", "book", "pdf", "resource"}
EXCLUDED_FILES = {"Tag Dictionary.md", "Task Dashboard.md", "Dashboard.md", "Knowledge MOC.md", "NeuroVault_ErrorLogs.md"}


def normalize_tag(tag):
    """Normalize a tag to lowercase kebab-case."""
    cleaned = tag.strip().strip('"').strip("'").lstrip("#").lower()
    cleaned = re.sub(r'[^a-z0-9-]+', '-', cleaned)
    return re.sub(r'-+', '-', cleaned).strip('-')


def load_dictionary():
    core_tags = set()
    mappings = {}

    if not DICT_FILE or not os.path.exists(DICT_FILE):
        return core_tags, mappings

    with open(DICT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    for line in content.split('\n'):
        match = re.search(r'-\s*`([^`]+)`', line)
        if match:
            master_tag = normalize_tag(match.group(1))
            if not master_tag:
                continue
            core_tags.add(master_tag)

            map_match = re.search(r'\*\(Maps:\s*(.*?)\)\*', line)
            if map_match:
                aliases = [normalize_tag(x) for x in map_match.group(1).split(',')]
                for alias in aliases:
                    if alias:
                        mappings[alias] = master_tag

    return core_tags, mappings


def get_all_notes(scan_all=False):
    """Return Markdown notes inside Knowledge/ by default (or entire vault if scan_all=True)."""
    notes = []
    if not VAULT or not os.path.isdir(VAULT):
        return notes

    target_dir = VAULT if scan_all else KNOWLEDGE_DIR
    if not target_dir or not os.path.isdir(target_dir):
        return notes

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("Attachments", "Templates", ".trash")]
        for file in files:
            if file.endswith(".md") and file not in EXCLUDED_FILES:
                notes.append(os.path.join(root, file))
    return notes


def parse_yaml_tags(content):
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not yaml_match:
        return [], None, content

    yaml_block = yaml_match.group(1)
    tags_match = re.search(r'tags:\s*\[(.*?)\]', yaml_block)
    if not tags_match:
        return [], yaml_block, content

    tag_str = tags_match.group(1)
    if not tag_str.strip():
        return [], yaml_block, content

    tags = [t.strip() for t in tag_str.split(',') if t.strip()]
    return tags, yaml_block, content


def update_yaml_tags(content, new_tags):
    tag_array = f"[{', '.join(new_tags)}]"

    def repl(m):
        yaml_inner = m.group(1)
        if 'tags:' in yaml_inner:
            new_yaml = re.sub(r'tags:\s*\[.*?\]', f'tags: {tag_array}', yaml_inner)
        else:
            new_yaml = yaml_inner + f'\ntags: {tag_array}'
        return f"---\n{new_yaml}\n---"

    return re.sub(r'^---\n(.*?)\n---', repl, content, count=1, flags=re.DOTALL)


def call_llm(content, core_tags, orphan_tags):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found in .env. Skipping LLM pass.")
        return []

    prompt = f"""
You are an expert taxonomy librarian for a personal knowledge base.
Analyze the following Markdown note.

Your task is to assign 2 to 4 highly relevant TOPIC tags to this note.
1. You MUST prioritize using tags from the Master Dictionary.
2. If the note covers a completely new domain, generate 1 new provisional tag (lowercase, kebab-case).
3. Do NOT use format tags (podcast, article, transcript, pdf, resource).
4. Review the current "orphan tags" (if any) and decide whether to map them, delete them (if junk), or keep them (if a valid new topic).

MASTER DICTIONARY:
{', '.join(sorted(core_tags))}

CURRENT ORPHAN TAGS:
{', '.join(orphan_tags)}

Respond ONLY with a valid JSON array of strings representing the final tags.
Example: ["agentic-ai", "startups"]

--- NOTE CONTENT ---
{content[:2500]}
"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a data librarian. Output strictly a JSON array of strings."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]

        match = re.search(r'\[.*?\]', reply, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
    except Exception as e:
        print(f"LLM Error: {e}")
        return []


def main(dry_run=False, scan_all=False):
    if not VAULT or not os.path.isdir(VAULT):
        print("❌ VAULT_ABSOLUTE_PATH is missing or invalid in .env.")
        sys.exit(1)

    scope_label = "entire vault" if scan_all else "Knowledge/"
    print(f"🚀 Starting Tag Audit Job (scope: {scope_label})..." + (" [DRY RUN]" if dry_run else ""))
    core_tags, mappings = load_dictionary()
    print(f"📚 Loaded Master Dictionary: {len(core_tags)} core tags, {len(mappings)} mappings.")

    notes = get_all_notes(scan_all=scan_all)
    print(f"📂 Found {len(notes)} note(s) in {scope_label}.")
    all_unknown_tags = []

    print(f"🔍 Scanning {scope_label} for provisional tags...")
    for path in notes:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        tags, _, _ = parse_yaml_tags(content)
        for t in tags:
            t_norm = normalize_tag(t)
            if not t_norm:
                continue
            if t_norm in mappings:
                t_norm = mappings[t_norm]
            if t_norm not in core_tags and t_norm not in BANNED_FORMAT_TAGS:
                all_unknown_tags.append(t_norm)

    tag_counts = Counter(all_unknown_tags)

    new_graduates = []
    for tag, count in tag_counts.items():
        if count >= 3:
            new_graduates.append(tag)
            core_tags.add(tag)

    if new_graduates:
        print(f"🎓 Graduating {len(new_graduates)} new tags to the Master Dictionary: {', '.join(new_graduates)}")
        if not dry_run and DICT_FILE and os.path.exists(DICT_FILE):
            with open(DICT_FILE, 'a', encoding='utf-8') as f:
                f.write("\n\n## 🆕 Newly Graduated Tags\n")
                for g in new_graduates:
                    f.write(f"- `{g}`\n")

    print("🧹 Cleaning and pruning notes...")
    llm_count = 0
    mapped_count = 0

    for path in notes:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        tags, yaml_block, _ = parse_yaml_tags(content)
        if yaml_block is None:
            continue

        original_tags = list(tags)
        new_tags = []
        orphan_tags = []

        for t in tags:
            t_low = normalize_tag(t)
            if not t_low or t_low in BANNED_FORMAT_TAGS:
                continue

            if t_low in mappings:
                new_tags.append(mappings[t_low])
            elif t_low in core_tags:
                new_tags.append(t_low)
            else:
                orphan_tags.append(t_low)

        new_tags = list(dict.fromkeys(new_tags))
        orphan_tags = list(dict.fromkeys(orphan_tags))

        needs_llm = (len(new_tags) == 0 and len(orphan_tags) == 0) or bool(orphan_tags)

        if needs_llm:
            print(f"🧠 LLM Pruning Pass for: {os.path.basename(path)} (orphans: {orphan_tags})")
            llm_count += 1
            if not dry_run:
                llm_tags = call_llm(content, core_tags, orphan_tags)
                if llm_tags:
                    final_tags = [normalize_tag(t) for t in llm_tags if normalize_tag(t) and normalize_tag(t) not in BANNED_FORMAT_TAGS][:5]
                    if final_tags:
                        new_content = update_yaml_tags(content, final_tags)
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
            continue

        final_tags = list(dict.fromkeys(new_tags + orphan_tags))[:5]
        if final_tags != original_tags:
            mapped_count += 1
            print(f"♻️ Normalized/mapped tags for: {os.path.basename(path)}")
            if not dry_run:
                new_content = update_yaml_tags(content, final_tags)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

    print(f"✅ Tag Audit Complete! (scanned={len(notes)}, graduated={len(new_graduates)}, llm_retagged={llm_count}, mapped={mapped_count})")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    scan_all = "--all" in sys.argv
    main(dry_run=dry_run, scan_all=scan_all)

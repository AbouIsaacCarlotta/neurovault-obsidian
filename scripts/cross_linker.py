"""
cross_linker.py — Shared module for cross-linking Obsidian notes.

Provides two functions:
1. find_related_notes(tags, exclude_filename) — Used at ingestion time to find
   existing notes sharing >= 2 tags with a newly created note.
2. batch_cross_link() — Used to scan the entire vault and inject
   bi-directional [[wikilinks]] between all notes sharing >= 2 tags.
"""
import os
import re
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH = os.environ.get("VAULT_ABSOLUTE_PATH", "")
RELATED_SECTION_HEADER = "## 🔗 Related Notes"
EXCLUDED_DIRS = {".obsidian", "Attachments", "Templates", ".trash", ".system_generated", ".git", "Archive"}
EXCLUDED_FILES = {"Tag Dictionary.md", "Task Dashboard.md", "Dashboard.md", "NeuroVault_ErrorLogs.md"}


def parse_note_metadata(filepath):
    """Extract tags and title from a note's YAML frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not yaml_match:
        return None

    yaml_block = yaml_match.group(1)
    tags_match = re.search(r'tags:\s*\[(.*?)\]', yaml_block)
    tags = []
    if tags_match and tags_match.group(1).strip():
        tags = [t.strip().strip('"').strip("'").lower() for t in tags_match.group(1).split(',')]

    # Extract title from first heading
    title_match = re.search(r'^# .+? (.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.splitext(os.path.basename(filepath))[0]

    filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]

    return {
        "path": filepath,
        "filename": filename_no_ext,
        "title": title,
        "tags": set(tags),
        "content": content,
    }


def scan_vault():
    """Scan all notes across the entire vault (excluding system/attachment/template/MOC files) and return metadata."""
    notes = []
    if not VAULT_PATH or not os.path.exists(VAULT_PATH):
        return notes

    for root, dirs, files in os.walk(VAULT_PATH):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in EXCLUDED_DIRS]
        for file in files:
            if file.endswith(".md") and file not in EXCLUDED_FILES and not file.endswith("MOC.md"):
                meta = parse_note_metadata(os.path.join(root, file))
                if meta and meta["tags"]:
                    notes.append(meta)
    return notes


def find_related_notes(new_tags, exclude_filename=None, min_shared=2):
    """
    Find existing vault notes sharing >= min_shared tags with the given tag set.
    Returns a list of (filename, shared_tags) tuples, sorted by overlap descending.
    Used at INGESTION TIME for lightweight one-directional linking.
    """
    if isinstance(new_tags, list):
        new_tags = set(t.lower() for t in new_tags)

    vault_notes = scan_vault()
    matches = []

    for note in vault_notes:
        if exclude_filename and note["filename"] == exclude_filename:
            continue
        shared = new_tags & note["tags"]
        if len(shared) >= min_shared:
            matches.append((note["filename"], sorted(shared)))

    # Sort by number of shared tags descending
    matches.sort(key=lambda x: len(x[1]), reverse=True)
    return matches


def format_related_section(matches):
    """Format a list of matches into a Markdown section."""
    if not matches:
        return ""

    lines = [RELATED_SECTION_HEADER]
    for filename, shared_tags in matches:
        tags_str = ", ".join(f"`#{t}`" for t in shared_tags)
        lines.append(f"- [[{filename}]] — shared: {tags_str}")
    lines.append("")
    return "\n".join(lines)


def inject_related_section(content, matches):
    """
    Inject or replace the ## 🔗 Related Notes section in note content.
    Places it just before the final '---' or 'Linked Concepts:' if possible,
    otherwise appends to the end.
    """
    section = format_related_section(matches)
    if not section:
        return content

    # If the section already exists, replace it
    pattern = rf'{re.escape(RELATED_SECTION_HEADER)}.*?(?=\n## |\n---|\n\*\*Linked Concepts|\Z)'
    if re.search(pattern, content, re.DOTALL):
        return re.sub(pattern, section + "\n", content, flags=re.DOTALL)

    # Place before "**Linked Concepts:**" if present
    if "**Linked Concepts:**" in content:
        parts = content.split("**Linked Concepts:**")
        return parts[0] + section + "\n**Linked Concepts:**" + parts[1]

    # Place before final "---" if present
    last_sep = content.rfind("\n---")
    if last_sep > 0 and last_sep > content.find("---", 3):
        return content[:last_sep] + "\n" + section + content[last_sep:]

    # Fallback: append to end
    return content.rstrip() + "\n\n" + section


def batch_cross_link(min_shared=2, dry_run=False):
    """Scan the entire vault and establish bi-directional links between notes."""
    print("🔍 Scanning vault for notes...")
    notes = scan_vault()
    print(f"   Found {len(notes)} notes with valid tags.")

    tag_to_notes = {}
    for note in notes:
        for tag in note["tags"]:
            tag_to_notes.setdefault(tag, []).append(note)

    links_to_add = {n["path"]: [] for n in notes}
    total_links = 0

    for i, note_a in enumerate(notes):
        candidate_notes = set()
        for tag in note_a["tags"]:
            candidate_notes.update(n["path"] for n in tag_to_notes.get(tag, []))
        candidate_notes.discard(note_a["path"])

        note_map = {n["path"]: n for n in notes}

        for path_b in candidate_notes:
            note_b = note_map[path_b]
            shared = note_a["tags"] & note_b["tags"]
            if len(shared) >= min_shared:
                links_to_add[note_a["path"]].append((note_b["filename"], sorted(shared)))
                total_links += 1

    for path in links_to_add:
        links_to_add[path].sort(key=lambda x: len(x[1]), reverse=True)

    print(f"\n📊 Cross-Linking Summary:")
    print(f"   Total bi-directional link connections found: {total_links}")

    notes_with_links = sum(1 for p, l in links_to_add.items() if l)
    print(f"   Notes that will receive links: {notes_with_links}/{len(notes)}")

    if dry_run:
        print("\n🧪 DRY RUN — No files modified.")
        return total_links

    updated_count = 0
    for note in notes:
        matches = links_to_add.get(note["path"], [])
        if not matches:
            continue

        new_content = inject_related_section(note["content"], matches)
        if new_content != note["content"]:
            with open(note["path"], 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated_count += 1

    print(f"✅ Successfully updated {updated_count} notes.")
    return total_links


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    batch_cross_link(dry_run=dry_run)

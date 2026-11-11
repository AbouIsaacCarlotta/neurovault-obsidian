# NeuroVault (Obsidian Second Brain)

Welcome to **NeuroVault**, the open-source foundation of an automated, AI-powered Second Brain built inside Obsidian.

This repository provides a clean Obsidian vault structure (Folders, Templates, and a native **Obsidian Bases** dashboard) as well as the Python automation scripts that power the workflows (Podcast summarization, YouTube extraction, web scraping, raw text ingestion, auto-tagging, and automatic knowledge graph cross-linking).

## 🚀 Features
- **Zero Third-Party Plugins Required:** Powered natively by **Obsidian Bases** (`NeuroVault.base` + `Dashboard.md`) — no Dataview or community plugins needed.
- **Strict Taxonomy:** Pre-configured with a Master Tag Dictionary enforcing lowercase kebab-case and max 5 tags per note.
- **Open Knowledge Format (OKF v0.1):** All generated notes use standardized YAML frontmatter (`title`, `description`, `timestamp`, `type`, `domain`, `tags`).
- **Auto Knowledge Graph Cross-Linking:** `cross_linker.py` connects notes sharing >= 2 tags via bidirectional `[[wikilinks]]` at ingestion time and in batch.
- **AI Automations:** 
  - `podcast_workflow.py`: Download Apple Podcasts (with Cloudflare bypass headers), transcribe via Whisper, and generate a structured note.
  - `youtube_workflow.py`: Extract YouTube transcripts, with automatic Whisper audio fallback via `yt-dlp` if captions are disabled.
  - `url_workflow.py`: Scrape web articles and resources with `crawl4ai` and generate clean Markdown summaries.
  - `document_workflow.py`: Parse local `.pdf`, `.docx`, and `.pptx` documents into clean Markdown summaries using Microsoft's MarkItDown.
  - `text_workflow.py`: Ingest raw pasted text blocks, articles, or meeting notes directly into your vault.
  - `archivist.py`: Universal router that automatically detects URLs, document files, or raw text and runs the right workflow.
  - `tag_audit.py`: Clean, normalize, graduate, and consolidate tags across your entire vault against the Master Tag Dictionary.
  - `cross_linker.py`: Scan and bi-directionally cross-link related notes across all folders in your vault.
  - `maintain.py`: One-command maintenance runner combining `tag_audit.py` + `cross_linker.py` (supports `--dry-run`).

---

## 🛠️ Setup Instructions (Tier 1 - Self-Hosted)

### 1. Requirements
- **Obsidian:** Download and install [Obsidian](https://obsidian.md/) (enable the built-in **Bases** core plugin — enabled by default).
- **Python 3.10+:** Installed on your system.
- **FFmpeg:** Required by `pydub` to manipulate audio files (e.g., `brew install ffmpeg` on macOS).

### 2. Configure Your Vault
1. Clone or download this repository to your local machine.
2. Open your terminal and navigate to the `scripts` folder:
   ```bash
   cd neurovault-obsidian/scripts
   ```
3. Run the interactive Setup Wizard to personalize your vault (it will create your folders and `Tag Dictionary.md`):
   ```bash
   python setup_vault.py
   ```
4. Open Obsidian and select **"Open folder as vault"**. Choose the `neurovault-obsidian` folder.
5. Your personalized vault is now ready!

### 3. Configure the Python Automations
To use the AI automations, configure your environment variables:

1. Navigate to the `scripts` folder in your terminal:
   ```bash
   cd scripts
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Copy the `.env.example` file to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
4. Open `.env` and fill in your details:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `VAULT_ABSOLUTE_PATH`: The absolute path to this vault on your computer (e.g., `/Users/yourname/Documents/neurovault-obsidian`).
   - `DESTINATION_FOLDER`: Folder where generated notes are saved (default: `Knowledge`; leave blank for vault root).

### 4. Running the Workflows

You can run the universal archivist script to automatically detect the type of input:
```bash
# Web article or resource
python archivist.py "https://example.com/article"

# YouTube video (with automatic Whisper fallback if no subtitles)
python archivist.py "https://youtube.com/watch?v=..."

# Apple Podcast
python archivist.py "https://podcasts.apple.com/..."

# Local Document (PDF, Word, PowerPoint)
python archivist.py "/Users/yourname/Documents/Report.pdf"

# Raw text snippet
python archivist.py "Here is a note or article snippet I want to summarize..."
```

Or run individual scripts directly:
```bash
python url_workflow.py "https://example.com/article"
python youtube_workflow.py "https://youtube.com/watch?v=..."
python podcast_workflow.py "https://podcasts.apple.com/..."
python document_workflow.py "/path/to/document.pdf"
python text_workflow.py "/path/to/raw_text.txt"
python tag_audit.py
python cross_linker.py
python maintain.py            # Run tag cleaning + cross-linking across your vault
python maintain.py --dry-run  # Preview changes without modifying files
```

---

## 🧠 Don't want to deal with Python and API keys? (Tier 2)

We are building a managed SaaS version of NeuroVault! 
With the **NeuroVault Obsidian Plugin**, you can run all of these automations natively inside Obsidian with a single click—no Python, no terminal, and no OpenAI API key required.

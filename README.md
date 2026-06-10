# NeuroVault (Obsidian Second Brain)

Welcome to **NeuroVault**, the open-source foundation of an automated, AI-powered Second Brain built inside Obsidian.

This repository provides the "Empty Vault" structure (Folders, MOCs, Templates, and Dataview scripts) as well as the Python automation scripts that power the workflows (Podcast summarization, YouTube extraction, and auto-tagging).

## 🚀 Features
- **Strict Taxonomy:** Pre-configured with a Master Tag Dictionary.
- **Dynamic MOCs (Maps of Content):** Dashboards for Knowledge, Work, Ideas, etc., powered by Dataview.
- **AI Automations:** 
  - `podcast_workflow.py`: Download Apple Podcasts, transcribe via Whisper, and generate a structured note.
  - `youtube_workflow.py`: Extract YouTube transcripts and summarize them (no video download required).
  - `document_workflow.py`: Parse local `.pdf`, `.docx`, and `.pptx` documents into clean Markdown summaries using Microsoft's MarkItDown.
  - `url_workflow.py`: Scrape web articles and summarize them into the vault.
  - `tag_audit.py`: Scan the vault to consolidate duplicate tags and enforce the Master Tag Dictionary.

---

## 🛠️ Setup Instructions (Tier 1 - Self-Hosted)

### 1. Requirements
- **Obsidian:** Download and install [Obsidian](https://obsidian.md/).
- **Community Plugins:** You will need to install the `Dataview` plugin inside Obsidian and enable it.
- **Python 3.9+:** Installed on your system.
- **FFmpeg:** Required by `pydub` to manipulate audio files. (e.g., `brew install ffmpeg` on macOS).

### 2. Configure Your Vault
1. Clone or download this repository to your local machine.
2. Open your terminal and navigate to the `scripts` folder:
   ```bash
   cd neurovault-obsidian/scripts
   ```
3. Run the interactive Setup Wizard to personalize your vault (it will generate your MOCs and Tag Dictionary):
   ```bash
   python setup_vault.py
   ```
4. Open Obsidian and select **"Open folder as vault"**. Choose the `neurovault-obsidian` folder.
5. Your personalized vault is now ready!

### 3. Configure the Python Automations
To use the AI automations, you need to configure your environment variables.

1. Navigate to the `scripts` folder in your terminal:
   ```bash
   cd scripts
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `.env.example` file to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
4. Open `.env` and fill in your details:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `VAULT_ABSOLUTE_PATH`: The absolute path to this vault on your computer (e.g., `/Users/yourname/Documents/neurovault-obsidian`).

### 4. Running the Workflows

You can run the archivist script to automatically detect the type of URL and run the correct workflow:
```bash
python archivist.py "https://podcasts.apple.com/..."
```

Or run individual scripts:
```bash
python podcast_workflow.py "https://podcasts.apple.com/..."
python youtube_workflow.py "https://youtube.com/watch?v=..."
python document_workflow.py "/Users/yourname/Desktop/Report.pdf"
python tag_audit.py
```

---

## 🧠 Don't want to deal with Python and API keys? (Tier 2)

We are building a managed SaaS version of NeuroVault! 
With the **NeuroVault Obsidian Plugin**, you can run all of these automations natively inside Obsidian with a single click—no Python, no terminal, and no OpenAI API key required.

*(Link coming soon)*

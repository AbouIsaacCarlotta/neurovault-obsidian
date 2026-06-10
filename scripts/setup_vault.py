import os

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"📁 Created directory: {path}")

def create_file(path, content):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(content)
        print(f"📄 Created file: {path}")
    else:
        print(f"⚠️ File already exists, skipping: {path}")

def generate_moc_content(domain):
    return f"""---
type: MOC
domain: {domain}
---

# 🗺️ {domain} Map of Content

Welcome to your {domain} dashboard. Here is a dynamic view of all notes related to {domain}.

## 📌 Recent Notes
```dataview
TABLE tags, date_saved
FROM "{domain}"
WHERE type != "MOC"
SORT date_saved DESC
LIMIT 10
```
"""

def generate_tag_dictionary(domains):
    content = "# 🏷️ Master Tag Dictionary\n\nThis is the strict taxonomy for your Second Brain. The AI automations will use this dictionary to retroactively tag your notes.\n\n## 📂 Core Domains\n"
    for domain in domains:
        content += f"- **{domain}**: Main category for {domain.lower()} related items.\n"
    
    content += """
## 🏷️ Approved Tags
- #podcast : Notes generated from podcast transcriptions.
- #youtube : Notes generated from YouTube videos.
- #article : Web articles and written content.
- #book : Book summaries and notes.
- #idea : Raw thoughts and concepts.

## 📝 The Rule of 3 (Incubation)
When a new concept arises, do not create a permanent tag immediately. Wait until you have at least 3 distinct notes about the same concept before adding it to this Master Tag Dictionary.
"""
    return content

def main():
    print("🧠 Welcome to the NeuroVault Setup Wizard!")
    print("Let's personalize your Second Brain.\n")
    
    # Get the parent directory (the root of the vault)
    vault_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    print("Which core domains do you want to track? (Comma-separated)")
    print("Default: Knowledge, Projects, Personal, Ideas")
    user_input = input("> ").strip()
    
    if not user_input:
        domains = ["Knowledge", "Projects", "Personal", "Ideas"]
    else:
        domains = [d.strip() for d in user_input.split(",") if d.strip()]
        
    print("\n🚀 Building your NeuroVault...\n")
    
    # Create required system folders
    create_directory(os.path.join(vault_path, "Archive"))
    create_directory(os.path.join(vault_path, "Tasks"))
    create_directory(os.path.join(vault_path, "Attachments"))
    create_directory(os.path.join(vault_path, "Attachments", "PDFs"))
    create_directory(os.path.join(vault_path, "Attachments", "Transcripts"))
    
    # Create Domain folders and MOCs
    for domain in domains:
        domain_path = os.path.join(vault_path, domain)
        create_directory(domain_path)
        moc_path = os.path.join(domain_path, f"{domain} MOC.md")
        create_file(moc_path, generate_moc_content(domain))
        
    # Create Tag Dictionary
    dict_path = os.path.join(vault_path, "Tag Dictionary.md")
    create_file(dict_path, generate_tag_dictionary(domains))
    
    print("\n✅ NeuroVault Setup Complete!")
    print(f"Your vault is ready at: {vault_path}")
    print("You can now open this folder in Obsidian.")

if __name__ == "__main__":
    main()

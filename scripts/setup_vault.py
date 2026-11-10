import os


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"📁 Created directory: {path}")


def create_file(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Created file: {path}")
    else:
        print(f"⚠️ File already exists, skipping: {path}")


def generate_tag_dictionary(domains):
    content = "# 🏷️ Master Tag Dictionary\n\nThis is the strict taxonomy for your Second Brain. The AI automations use this dictionary to tag and consolidate your notes.\n\n## 📂 Core Domains\n"
    for domain in domains:
        content += f"- **{domain}**: Notes related to {domain.lower()}.\n"

    content += """
## 🏷️ Approved Topic Tags
- `ai`
- `productivity`
- `startups`
- `technology`
- `personal-growth`

## 📜 Tag Rules
- Always lowercase, kebab-case (`ai`, never `AI`; `product-management`, never `product management`).
- Never use format tags (`podcast`, `transcript`, `article`, `video`, `pdf`, `resource`) — YAML `type:` already tracks the format.
- Max 5 tags per note.

## 📝 The Rule of 3 (Incubation)
When a new topic tag appears on at least 3 distinct notes, `tag_audit.py` automatically graduates it into this Master Tag Dictionary.
"""
    return content


def main():
    print("🧠 Welcome to the NeuroVault Setup Wizard!")
    print("Let's personalize your Second Brain.\n")

    vault_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    print("Which folders do you want to start with? (Comma-separated)")
    print("Default: Knowledge, Projects, Personal, Ideas")
    user_input = input("> ").strip()

    if not user_input:
        domains = ["Knowledge", "Projects", "Personal", "Ideas"]
    else:
        domains = [d.strip() for d in user_input.split(",") if d.strip()]

    print("\n🚀 Building your NeuroVault...\n")

    create_directory(os.path.join(vault_path, "Archive"))
    create_directory(os.path.join(vault_path, "Tasks"))
    create_directory(os.path.join(vault_path, "Attachments"))
    create_directory(os.path.join(vault_path, "Attachments", "PDFs"))
    create_directory(os.path.join(vault_path, "Attachments", "Transcripts"))

    for domain in domains:
        create_directory(os.path.join(vault_path, domain))

    dict_path = os.path.join(vault_path, "Tag Dictionary.md")
    create_file(dict_path, generate_tag_dictionary(domains))

    print("\n✅ NeuroVault Setup Complete!")
    print(f"Your vault is ready at: {vault_path}")
    print("Open this folder in Obsidian and check Dashboard.md / NeuroVault.base (powered natively by Obsidian Bases).")


if __name__ == "__main__":
    main()

import os
import sys
import tempfile

def is_url(s):
    return s.startswith("http://") or s.startswith("https://")

def is_file_path(s):
    return os.path.isfile(s)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 archivist.py <URL | FILE_PATH | RAW_TEXT>")
        sys.exit(1)
        
    target = " ".join(sys.argv[1:])
    
    # Force the working directory so imports and paths resolve correctly
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    python_bin = sys.executable
    
    if is_url(target):
        print(f"🚦 Archivist is routing the URL: {target}")
        
        if "podcasts.apple.com" in target:
            print("🎙️ Target identified as an Apple Podcast! Firing up podcast_workflow.py...")
            os.system(f'"{python_bin}" podcast_workflow.py "{target}"')
        elif "youtube.com" in target or "youtu.be" in target:
            print("🎥 Target identified as a YouTube Video! Firing up youtube_workflow.py...")
            os.system(f'"{python_bin}" youtube_workflow.py "{target}"')
        else:
            print("🌐 Target identified as a standard URL! Firing up url_workflow.py...")
            os.system(f'"{python_bin}" url_workflow.py "{target}"')
            
    elif is_file_path(target):
        print(f"🚦 Archivist is routing the file: {target}")
        print("📄 Target identified as a local Document! Firing up document_workflow.py...")
        os.system(f'"{python_bin}" document_workflow.py "{target}"')
        
    else:
        # Raw text — write to temp file and route to text_workflow.py
        print("🚦 Archivist detected raw text input.")
        print("📝 Target identified as raw text! Firing up text_workflow.py...")
        
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', prefix='archivist_text_', 
                                          dir='/tmp', delete=False, encoding='utf-8')
        tmp.write(target)
        tmp.close()
        
        os.system(f'"{python_bin}" text_workflow.py "{tmp.name}"')

if __name__ == "__main__":
    main()

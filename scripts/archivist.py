import os
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: doppler run -- python3 archivist.py <URL>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    # Force the working directory so imports and paths resolve correctly
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    print(f"🚦 Archivist is routing the URL: {target_url}")
    
    if "podcasts.apple.com" in target_url:
        print("🎙️ Target identified as an Apple Podcast! Firing up podcast_workflow.py...")
        os.system(f'{sys.executable} podcast_workflow.py "{target_url}"')
    elif "youtube.com" in target_url or "youtu.be" in target_url:
        print("🎥 Target identified as a YouTube Video! Firing up youtube_workflow.py...")
        os.system(f'{sys.executable} youtube_workflow.py "{target_url}"')
    else:
        print("📄 Target identified as a standard URL! Firing up url_workflow.py...")
        os.system(f'{sys.executable} url_workflow.py "{target_url}"')

if __name__ == "__main__":
    main()

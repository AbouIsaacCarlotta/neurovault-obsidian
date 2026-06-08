import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote

def clean_for_match(text):
    # Enlève les caractères spéciaux pour faciliter la comparaison
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

def apple_url_to_mp3(apple_url):
    # 1. Extraire l'ID du podcast
    match_id = re.search(r'id(\d+)', apple_url)
    if not match_id:
        return "Erreur : Impossible de trouver l'ID dans l'URL."
    podcast_id = match_id.group(1)
    
    # Extraire le "slug" (titre dans l'URL) pour trouver le bon épisode
    match_slug = re.search(r'podcast/([^/]+)/id', apple_url)
    target_slug = unquote(match_slug.group(1)) if match_slug else None

    # 2. Interroger l'API iTunes Lookup
    url_api = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
    reponse_api = requests.get(url_api).json()
    
    if not reponse_api['results']:
        return "Erreur : Podcast introuvable sur iTunes."
        
    url_rss = reponse_api['results'][0]['feedUrl']
    
    # 3. Parser le flux RSS
    reponse_rss = requests.get(url_rss)
    racine = ET.fromstring(reponse_rss.content)
    
    # 4. Chercher le bon épisode
    for item in racine.findall('.//item'):
        titre = item.find('title').text
        if titre is None:
            continue
            
        # Si l'URL contient un titre spécifique, on cherche la correspondance
        if target_slug:
            # On nettoie le titre RSS et le slug URL pour les comparer facilement
            clean_titre = clean_for_match(titre)
            clean_slug = clean_for_match(target_slug)
            
            # Si le slug de l'URL est dans le titre de l'épisode (ou inversement)
            if clean_slug in clean_titre or clean_titre in clean_slug:
                balise_audio = item.find('enclosure')
                if balise_audio is not None:
                    return {"titre": titre, "mp3_url": balise_audio.get('url')}
        else:
            # Comportement par défaut : on prend le premier épisode si pas de slug spécifique
            balise_audio = item.find('enclosure')
            if balise_audio is not None:
                return {"titre": titre, "mp3_url": balise_audio.get('url')}
                
    return "Erreur : Aucun MP3 correspondant trouvé."

# Tes URLs
url_real_vision = "https://podcasts.apple.com/pg/podcast/the-next-2-years-will-change-everything/id1581019716?i=1000763255853"
url_greg = "https://podcasts.apple.com/us/podcast/the-next-%24100b-market-selling-to-ai-agents/id1593424985?i=1000770824481"

print(apple_url_to_mp3(url_real_vision))
print(apple_url_to_mp3(url_greg))

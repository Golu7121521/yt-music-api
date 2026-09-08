from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

app = FastAPI(title="Spotify-Style Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def decrypt_url(encrypted_url):
    if not encrypted_url:
        return ""
    try:
        secret_key = b"38346591"
        iv = b""
        k = des(secret_key, ECB, iv, pad=None, padmode=PAD_PKCS5)
        decrypted_url = k.decrypt(base64.b64decode(encrypted_url)).decode('utf-8')
        
        if decrypted_url.startswith("http://"):
            decrypted_url = decrypted_url.replace("http://", "https://", 1)
            
        if "_96.mp4" in decrypted_url:
            decrypted_url = decrypted_url.replace("_96.mp4", "_160.mp4")
            
        return decrypted_url
    except Exception:
        return ""

def format_song_item(item):
    if not isinstance(item, dict):
        return None
    more_info = item.get("more_info", {})
    enc_url = more_info.get("encrypted_media_url")
    playable_url = decrypt_url(enc_url)
    
    if not playable_url:
        return None

    return {
        "id": item.get("id"),
        "title": item.get("title") or item.get("song"),
        "artist": more_info.get("singers") or item.get("primary_artists") or item.get("subtitle") or "Unknown",
        "album": more_info.get("album"),
        "year": str(item.get("year") or more_info.get("year") or ""),
        "language": (item.get("language") or more_info.get("language") or "hindi").lower(),
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "stream_url": playable_url
    }

@app.get("/")
def home():
    return {"message": "Recommendation Engine Live"}

@app.get("/search")
def search_songs(query: str, page: int = 1):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&p={page}&n=25"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers).json()
        
        songs = response.get("results", []) if isinstance(response, dict) else []
        formatted = [format_song_item(s) for s in songs if format_song_item(s)]
        return {"status": "success", "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/home-feed")
def get_home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers).json()
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lyrics")
def get_lyrics(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return {"status": "success", "lyrics": data.get("lyrics", "Lyrics not available.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Smart Vibe Matching (Filtering out irrelevant/genre-leaking songs)
@app.get("/smart-radio")
def smart_vibe_radio(song_id: str, artist: str = "", era_decade: str = "", page: int = 1):
    headers = {"User-Agent": "Mozilla/5.0"}
    raw_candidates = []
    
    # Layer 1: Specific Song Entity Radio
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&pid={song_id}"
        data = requests.get(url, headers=headers).json()
        items = data if isinstance(data, list) else data.get("songs", [])
        for s in items:
            it = format_song_item(s)
            if it: raw_candidates.append(it)
    except Exception:
        pass

    # Layer 2: Targeted Era/Artist Query Fallback
    if len(raw_candidates) < 10 and artist:
        try:
            target_query = f"{artist.split(',')[0].strip()} {era_decade} hits".strip()
            url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={target_query}&_format=json&_marker=0&api_version=4&p={page}&n=25"
            res = requests.get(url, headers=headers).json()
            items = res.get("results", []) if isinstance(res, dict) else []
            for s in items:
                it = format_song_item(s)
                if it: raw_candidates.append(it)
        except Exception:
            pass

    # Layer 3: Heuristic Filtering (Blocking Bhakti / Devotional / Era Mismatch)
    blacklist_keywords = ["aarti", "bhajan", "chalisa", "mantra", "katha", "devotional", "shri", "krishna", "ram", "hanuman"]
    filtered_results = []
    
    for song in raw_candidates:
        title_lower = song["title"].lower()
        
        # Drop devotional contamination unless user explicitly plays bhakti
        if any(w in title_lower for w in blacklist_keywords):
            continue
            
        # Era check (e.g. If 90s, keep 1988-2002 range)
        if era_decade == "90s" and song["year"]:
            try:
                y = int(song["year"])
                if y < 1988 or y > 2002:
                    continue
            except ValueError:
                pass
                
        if not any(f["id"] == song["id"] for f in filtered_results):
            filtered_results.append(song)

    return {"status": "success", "results": filtered_results}

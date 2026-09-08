from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

app = FastAPI(title="JioSaavn Full API")

# CORS middleware taaki kisi bhi browser/origin se request block na ho
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
        
        # Browser security ke liye https zaroori hai
        if decrypted_url.startswith("http://"):
            decrypted_url = decrypted_url.replace("http://", "https://", 1)
            
        # 160kbps sabhi gaano par available aur bina buffering chalta hai
        if "_96.mp4" in decrypted_url:
            decrypted_url = decrypted_url.replace("_96.mp4", "_160.mp4")
            
        return decrypted_url
    except Exception:
        return ""

def format_song_item(item):
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
        "duration": more_info.get("duration"),
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "stream_url": playable_url
    }

@app.get("/")
def home():
    return {"message": "JioSaavn API is running smoothly!"}

# 1. Search Songs
@app.get("/search")
def search_songs(query: str, page: int = 1):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&p={page}&n=20"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        songs = []
        if isinstance(data, dict):
            songs = data.get("results", []) or data.get("data", [])
        
        formatted = []
        for s in songs:
            formatted_item = format_song_item(s)
            if formatted_item:
                formatted.append(formatted_item)
            
        return {"status": "success", "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Home Tab Feed
@app.get("/home-feed")
def get_home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Get Lyrics
@app.get("/lyrics")
def get_lyrics(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return {"status": "success", "lyrics": data.get("lyrics", "Lyrics not available.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Unlimited Recommendations / Similar Songs
@app.get("/radio")
def get_song_radio(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=reco.getreco&api_version=4&_format=json&_marker=0&pid={song_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        data = res.json()
        
        raw_songs = data if isinstance(data, list) else data.get("songs", [])
        
        formatted = []
        for s in raw_songs:
            formatted_item = format_song_item(s)
            if formatted_item:
                formatted.append(formatted_item)
                
        return {"status": "success", "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

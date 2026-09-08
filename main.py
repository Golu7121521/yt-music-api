from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

app = FastAPI(title="JioSaavn Full Featured API")

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
        decrypted_url = decrypted_url.replace("_96.mp4", "_320.mp4")
        return decrypted_url
    except Exception:
        return ""

@app.get("/")
def home():
    return {"message": "JioSaavn Full API is live and running!"}

# 1. Search Songs
@app.get("/search")
def search_songs(query: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&n=10"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        songs = []
        if isinstance(data, dict):
            songs = data.get("results", [])
            if not songs and "data" in data:
                songs = data.get("data", [])
        
        formatted_songs = []
        for song in songs:
            more_info = song.get("more_info", {})
            enc_url = more_info.get("encrypted_media_url")
            playable_url = decrypt_url(enc_url)
            
            formatted_songs.append({
                "id": song.get("id"),
                "title": song.get("title") or song.get("song"),
                "artist": more_info.get("singers") or song.get("subtitle"),
                "album": more_info.get("album"),
                "duration": more_info.get("duration"),
                "image": (song.get("image") or "").replace("150x150", "500x500"),
                "stream_url": playable_url
            })
            
        return {"status": "success", "results": formatted_songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Home Tab Feed (Trending, New Releases, Charts, etc.)
@app.get("/home-feed")
def get_home_feed():
    try:
        # JioSaavn Home webapi endpoint
        url = "https://www.jiosaavn.com/api.php?__call=webapi.get&token=home&type=playlist&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Get Lyrics by Song ID
@app.get("/lyrics")
def get_lyrics(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        lyrics_text = data.get("lyrics", "Lyrics not available.")
        return {"status": "success", "lyrics": lyrics_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

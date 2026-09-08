from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

app = FastAPI(title="JioSaavn Full Featured API")

# CORS setup taaki frontend (HTML) se requests block na hon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL Decryption logic for JioSaavn
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
    return {"message": "JioSaavn Full API is live and running smoothly!"}

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

# 2. Home Tab Feed (Updated with correct getLaunchData endpoint)
@app.get("/home-feed")
def get_home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
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

# 4. Get Radio / Similar Songs Queue for Auto-Play
@app.get("/radio")
def get_song_radio(song_id: str):
    try:
        station_url = f"https://www.jiosaavn.com/api.php?__call=webradio.createStation&entity_id={song_id}&entity_type=song&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(station_url, headers=headers)
        station_data = res.json()
        
        station_id = station_data.get("stationid")
        if not station_id:
            return {"status": "error", "message": "Could not create radio station"}
            
        songs_url = f"https://www.jiosaavn.com/api.php?__call=webradio.getSong&stationid={station_id}&k=20&_format=json&_marker=0&api_version=4"
        songs_res = requests.get(songs_url, headers=headers)
        songs_data = songs_res.json()
        
        formatted_songs = []
        items = songs_data.values() if isinstance(songs_data, dict) else songs_data
        
        for item in items:
            if isinstance(item, dict):
                more_info = item.get("more_info", {})
                enc_url = more_info.get("encrypted_media_url")
                playable_url = decrypt_url(enc_url)
                
                if playable_url:
                    formatted_songs.append({
                        "id": item.get("id"),
                        "title": item.get("title") or item.get("song"),
                        "artist": more_info.get("singers") or item.get("subtitle"),
                        "image": (item.get("image") or "").replace("150x150", "500x500"),
                        "stream_url": playable_url
                    })
                    
        return {"status": "success", "results": formatted_songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

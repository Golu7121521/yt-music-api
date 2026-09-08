from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

app = FastAPI(title="JioSaavn Authentic Radio API")

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
        "year": item.get("year") or more_info.get("year") or "",
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "stream_url": playable_url
    }

@app.get("/")
def home():
    return {"message": "Radio API is online"}

# 1. Search Songs
@app.get("/search")
def search_songs(query: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&n=25"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        songs = []
        if isinstance(data, dict):
            songs = data.get("results", []) or data.get("data", [])
        
        formatted = []
        for s in songs:
            item = format_song_item(s)
            if item:
                formatted.append(item)
            
        return {"status": "success", "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Home Feed
@app.get("/home-feed")
def get_home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Lyrics
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

# 4. Authentic Entity Radio (Zero random/bhakti contamination)
@app.get("/radio")
def get_station_radio(song_id: str, station_id: str = ""):
    headers = {"User-Agent": "Mozilla/5.0"}
    formatted = []
    
    try:
        # Step A: Agar station_id nahi hai, toh pehle JioSaavn se authentic radio station banwao
        if not station_id:
            st_url = f'https://www.jiosaavn.com/api.php?__call=webradio.createEntityStation&entity_id=["{song_id}"]&entity_type=queue&_format=json&_marker=0&api_version=4'
            st_res = requests.get(st_url, headers=headers).json()
            station_id = st_res.get("stationid")

        # Step B: Station se exact vibe wale continuous tracks fetch karo
        if station_id:
            song_url = f"https://www.jiosaavn.com/api.php?__call=webradio.getSong&stationid={station_id}&k=20&_format=json&_marker=0&api_version=4"
            song_res = requests.get(song_url, headers=headers).json()
            
            raw_items = song_res.values() if isinstance(song_res, dict) else song_res
            for item in raw_items:
                if isinstance(item, dict):
                    # Direct song ya nested song object
                    song_obj = item.get("song") if "song" in item and isinstance(item["song"], dict) else item
                    formatted_item = format_song_item(song_obj)
                    if formatted_item:
                        formatted.append(formatted_item)

        return {
            "status": "success", 
            "station_id": station_id, 
            "results": formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

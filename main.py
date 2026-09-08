from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="JioSaavn Light API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "JioSaavn API is live and running smoothly!"}

@app.get("/search")
def search_songs(query: str):
    try:
        # Better and updated JioSaavn search endpoint
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&n=10"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Handling different possible JSON structures from JioSaavn
        songs = []
        if isinstance(data, dict):
            songs = data.get("results", [])
            if not songs and "data" in data:
                songs = data.get("data", [])
        
        formatted_songs = []
        
        for song in songs:
            more_info = song.get("more_info", {})
            formatted_songs.append({
                "id": song.get("id"),
                "title": song.get("title") or song.get("song"),
                "artist": more_info.get("singers") or song.get("subtitle"),
                "album": more_info.get("album"),
                "duration": more_info.get("duration"),
                "image": (song.get("image") or "").replace("150x150", "500x500"),
                "stream_url": more_info.get("encrypted_media_url")
            })
            
        return {"status": "success", "results": formatted_songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

# 1. Search Songs
@app.get("/search")
def search_songs(query: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&n=10"
        response = requests.get(url)
        data = response.json()
        
        songs = data.get("results", [])
        formatted_songs = []
        
        for song in songs:
            # JioSaavn songs data clean formatting
            formatted_songs.endswith # wait, let's just append
            formatted_songs.append({
                "id": song.get("id"),
                "title": song.get("title"),
                "artist": song.get("more_info", {}).get("singers"),
                "album": song.get("more_info", {}).get("album"),
                "duration": song.get("more_info", {}).get("duration"),
                "image": song.get("image", "").replace("150x150", "500x500"),
                "stream_url": song.get("more_info", {}).get("encrypted_media_url")
            })
            
        return {"status": "success", "results": formatted_songs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

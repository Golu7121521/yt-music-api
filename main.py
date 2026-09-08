from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jio_client
import engine

app = FastAPI(title="Spotify-Architecture Music API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SeedPayload(BaseModel):
    id: str
    title: str
    artist: str
    year: int = 0
    language: str = "hindi"
    page: int = 1

@app.get("/")
def health():
    return {"status": "Spotify-style custom engine is active"}

@app.get("/search")
def search(query: str, page: int = 1):
    results = jio_client.fetch_search(query=query, page=page, count=20)
    return {"status": "success", "results": results}

@app.get("/home-feed")
def home_feed():
    try:
        data = jio_client.fetch_home()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lyrics")
def lyrics(song_id: str):
    text = jio_client.fetch_lyrics(song_id)
    return {"status": "success", "lyrics": text}

# Custom Vector Algorithm Endpoint
@app.post("/vibe-radio")
def vibe_radio(payload: SeedPayload):
    seed = payload.model_dump()
    recommended = engine.generate_vibe_queue(seed_song=seed, page=payload.page)
    return {"status": "success", "results": recommended}

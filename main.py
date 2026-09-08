from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Set
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

import engine

app = FastAPI(title="Spotify-Architecture Music Streamer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def decrypt_url(encrypted_url: str) -> str:
    if not encrypted_url:
        return ""
    try:
        secret_key = b"38346591"
        iv = b""
        k = des(secret_key, ECB, iv, pad=None, padmode=PAD_PKCS5)
        decrypted = k.decrypt(base64.b64decode(encrypted_url)).decode("utf-8")
        if decrypted.startswith("http://"):
            decrypted = decrypted.replace("http://", "https://", 1)
        if "_96.mp4" in decrypted:
            decrypted = decrypted.replace("_96.mp4", "_160.mp4")
        return decrypted
    except Exception:
        return ""

def format_track(item: dict) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    more = item.get("more_info", {})
    enc_url = more.get("encrypted_media_url")
    stream = decrypt_url(enc_url)
    if not stream:
        return None

    raw_year = item.get("year") or more.get("year") or 0
    try:
        year = int(raw_year)
    except (ValueError, TypeError):
        year = 0

    return {
        "id": str(item.get("id")),
        "title": item.get("title") or item.get("song") or "",
        "artist": more.get("singers") or item.get("primary_artists") or item.get("subtitle") or "Unknown",
        "album": more.get("album") or "",
        "year": year,
        "language": (item.get("language") or more.get("language") or "hindi").strip().lower(),
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "stream_url": stream,
        "tags": []
    }

def fetch_search_tracks(query: str, page: int = 1, count: int = 20) -> List[dict]:
    url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&p={page}&n={count}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers).json()
        raw_list = res.get("results", []) if isinstance(res, dict) else []
        formatted = []
        for s in raw_list:
            t = format_track(s)
            if t:
                formatted.append(t)
        return formatted
    except Exception:
        return []

class RecommendationRequest(BaseModel):
    seed_track: dict
    exclude_ids: Optional[List[str]] = []
    top_k: Optional[int] = 15

@app.get("/")
def root():
    return {"message": "Custom Content-Based Recommendation API is running"}

@app.get("/search")
def search(query: str, page: int = 1):
    tracks = fetch_search_tracks(query=query, page=page, count=20)
    return {"status": "success", "results": tracks}

@app.get("/home-feed")
def home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lyrics")
def lyrics(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return {"status": "success", "lyrics": data.get("lyrics", "Lyrics not available.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations")
def get_recommendations(req: RecommendationRequest):
    seed = req.seed_track
    if not seed or not seed.get("id"):
        raise HTTPException(status_code=400, detail="Invalid seed track")

    # 1. Claude ke engine se contextual queries generate karein
    queries = engine.generate_candidate_queries(seed)
    
    # 2. Candidate pool collect karein
    candidate_pool = []
    seen_ids: Set[str] = set(req.exclude_ids or [])
    seen_ids.add(str(seed.get("id")))

    for q in queries:
        batch = fetch_search_tracks(query=q, page=1, count=15)
        for cand in batch:
            if cand["id"] not in seen_ids:
                seen_ids.add(cand["id"])
                candidate_pool.append(cand)

    # 3. Engine ke rank_candidates dwara sanitize aur score karein
    ranked_tracks = engine.rank_candidates(
        seed_track=seed,
        candidates=candidate_pool,
        top_k=req.top_k,
        exclude_ids=set(req.exclude_ids or [])
    )

    return {"status": "success", "results": ranked_tracks}

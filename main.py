from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Set
import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

import engine

app = FastAPI(title="Spotify-Architecture Music Streamer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Decryption & Metadata Helpers
# -------------------------------------------------------------
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
        "image": (item.get("image") or "").replace("150x150", "500x500").replace("50x50", "500x500"),
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

# -------------------------------------------------------------
# Base Endpoints
# -------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Streaming API & Algorithmic Recommendation Engine is live"}

# 1. Standard Track Search
@app.get("/search")
def search(query: str, page: int = 1):
    tracks = fetch_search_tracks(query=query, page=page, count=20)
    return {"status": "success", "results": tracks}

# 2. Categorized Search (Songs, Albums, Artists for Search Screen Tabs)
@app.get("/search/all")
def search_all(query: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=autocomplete.get&query={query}&_format=json&_marker=0&api_version=4"
        res = requests.get(url, headers=headers).json()
        
        # Dedicated track search for robust audio results
        formatted_songs = fetch_search_tracks(query=query, page=1, count=15)

        albums = []
        for alb in res.get("albums", {}).get("data", []):
            albums.append({
                "id": str(alb.get("id")),
                "title": alb.get("title"),
                "artist": alb.get("music"),
                "image": (alb.get("image") or "").replace("50x50", "500x500").replace("150x150", "500x500"),
                "year": alb.get("year", "")
            })

        artists = []
        for art in res.get("artists", {}).get("data", []):
            artists.append({
                "id": str(art.get("id")),
                "name": art.get("name") or art.get("title"),
                "image": (art.get("image") or "").replace("50x50", "500x500").replace("150x150", "500x500"),
                "role": art.get("role", "Artist")
            })

        return {
            "status": "success",
            "results": {
                "songs": formatted_songs,
                "albums": albums,
                "artists": artists
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Home Feed
@app.get("/home-feed")
def home_feed():
    try:
        url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Lyrics
@app.get("/lyrics")
def lyrics(song_id: str):
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return {"status": "success", "lyrics": data.get("lyrics", "Lyrics aren't available for this song.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Album Details & Tracklist
@app.get("/album")
def get_album(album_id: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=content.getAlbumDetails&albumid={album_id}&_format=json&_marker=0&api_version=4"
        data = requests.get(url, headers=headers).json()
        
        songs_list = data.get("list", []) or data.get("songs", [])
        formatted_tracks = [format_track(s) for s in songs_list if format_track(s)]
        
        return {
            "status": "success",
            "album": {
                "id": str(data.get("id") or album_id),
                "title": data.get("title") or data.get("name"),
                "artist": data.get("primary_artists") or data.get("artist"),
                "year": data.get("year"),
                "image": (data.get("image") or "").replace("150x150", "500x500"),
                "track_count": len(formatted_tracks),
                "tracks": formatted_tracks
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 6. Artist Details, Top Songs & Albums
@app.get("/artist")
def get_artist(artist_id: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.jiosaavn.com/api.php?__call=artist.getArtistPageDetails&artistId={artist_id}&_format=json&_marker=0&api_version=4"
        data = requests.get(url, headers=headers).json()
        
        top_songs = data.get("topSongs", []) or data.get("songs", [])
        formatted_songs = [format_track(s) for s in top_songs if format_track(s)]
        
        top_albums = []
        for alb in data.get("topAlbums", []):
            top_albums.append({
                "id": str(alb.get("id")),
                "title": alb.get("title") or alb.get("name"),
                "year": alb.get("year", ""),
                "image": (alb.get("image") or "").replace("150x150", "500x500")
            })

        return {
            "status": "success",
            "artist": {
                "id": str(data.get("artistId") or artist_id),
                "name": data.get("name"),
                "image": (data.get("image") or "").replace("150x150", "500x500"),
                "follower_count": data.get("follower_count", "0"),
                "top_songs": formatted_songs,
                "top_albums": top_albums
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 7. Algorithmic Recommendations (Vibe Lock Engine)
@app.post("/recommendations")
def get_recommendations(req: RecommendationRequest):
    seed = req.seed_track
    if not seed or not seed.get("id"):
        raise HTTPException(status_code=400, detail="Invalid seed track")

    # Generate contextual candidate queries via engine.py
    queries = engine.generate_candidate_queries(seed)
    
    candidate_pool = []
    seen_ids: Set[str] = set(req.exclude_ids or [])
    seen_ids.add(str(seed.get("id")))

    for q in queries:
        batch = fetch_search_tracks(query=q, page=1, count=15)
        for cand in batch:
            if cand["id"] not in seen_ids:
                seen_ids.add(cand["id"])
                candidate_pool.append(cand)

    # Rank and filter through engine algorithm
    ranked_tracks = engine.rank_candidates(
        seed_track=seed,
        candidates=candidate_pool,
        top_k=req.top_k,
        exclude_ids=set(req.exclude_ids or [])
    )

    return {"status": "success", "results": ranked_tracks}

"""
main.py

FastAPI application exposing REST endpoints for the Flutter music streaming client.
Decoupled through the CatalogProvider abstraction (providers.py).

Run locally:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import engine
from providers import CatalogProvider, get_catalog_provider
from schemas import RecommendationRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mymusic.api")

app = FastAPI(
    title="MyMusic Streaming API",
    description="Backend API powering the MyMusic Flutter streaming app.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------

def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (str, int, float)):
        return str(value)
    return default


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return default


def _upgrade_to_https(url: str) -> str:
    if not url:
        return url
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def format_song(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "id": _safe_str(raw.get("id")),
        "title": _safe_str(raw.get("title"), "Unknown Title"),
        "artist": _safe_str(raw.get("artist"), "Unknown Artist"),
        "album": _safe_str(raw.get("album")),
        "year": _safe_int(raw.get("year")),
        "language": _safe_str(raw.get("language")),
        "image": _upgrade_to_https(_safe_str(raw.get("image"))),
        "stream_url": _upgrade_to_https(_safe_str(raw.get("stream_url"))),
        "duration": _safe_int(raw.get("duration")),
        "artist_id": _safe_str(raw.get("artist_id")),
        "album_id": _safe_str(raw.get("album_id")),
    }


def format_album(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    out = {
        "id": _safe_str(raw.get("id")),
        "title": _safe_str(raw.get("title"), "Unknown Album"),
        "artist": _safe_str(raw.get("artist"), "Unknown Artist"),
        "image": _upgrade_to_https(_safe_str(raw.get("image"))),
        "year": _safe_int(raw.get("year")),
        "description": _safe_str(raw.get("description")),
    }
    if "tracks" in raw:
        out["tracks"] = [format_song(t) for t in raw.get("tracks") or []]
        out["songCount"] = len(out["tracks"])
    return out


def format_artist(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    out = {
        "id": _safe_str(raw.get("id")),
        "name": _safe_str(raw.get("name"), "Unknown Artist"),
        "image": _upgrade_to_https(_safe_str(raw.get("image"))),
        "role": _safe_str(raw.get("role")),
        "followers": _safe_int(raw.get("followers"), 0),
    }
    if "top_songs" in raw:
        out["top_songs"] = [format_song(s) for s in raw.get("top_songs") or []]
    if "albums" in raw:
        out["albums"] = [format_album(a) for a in raw.get("albums") or []]
    return out


def format_playlist(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    out = {
        "id": _safe_str(raw.get("id")),
        "title": _safe_str(raw.get("title"), "Featured Playlist"),
        "image": _upgrade_to_https(_safe_str(raw.get("image"))),
        "description": _safe_str(raw.get("description")),
    }
    if "tracks" in raw:
        out["tracks"] = [format_song(t) for t in raw.get("tracks") or []]
        out["songCount"] = len(out["tracks"])
    return out


# ---------------------------------------------------------------------------
# Meta / Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["meta"])
async def root() -> Dict[str, str]:
    return {"status": "ok", "service": "MyMusic Streaming API"}


@app.get("/health", tags=["meta"])
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Search Endpoints
# ---------------------------------------------------------------------------

@app.get("/search", tags=["search"])
async def search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> List[Dict[str, Any]]:
    try:
        results = await provider.search_songs(query=query, page=page, page_size=20)
        return [format_song(r) for r in results]
    except Exception:
        logger.exception("search failed for query=%s page=%s", query, page)
        raise HTTPException(status_code=502, detail="Unable to fetch search results.")


@app.get("/search/all", tags=["search"])
async def search_all(
    query: str = Query(..., min_length=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, List[Dict[str, Any]]]:
    try:
        results = await provider.search_all(query=query)
        return {
            "songs": [format_song(s) for s in results.get("songs", [])],
            "albums": [format_album(a) for a in results.get("albums", [])],
            "artists": [format_artist(a) for a in results.get("artists", [])],
        }
    except Exception:
        logger.exception("search_all failed for query=%s", query)
        raise HTTPException(status_code=502, detail="Unable to fetch search results.")


# ---------------------------------------------------------------------------
# Home Feed
# ---------------------------------------------------------------------------

@app.get("/home-feed", tags=["home"])
async def home_feed(
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        feed = await provider.get_home_feed()
        return {
            "new_trending": [format_song(s) for s in feed.get("new_trending", [])],
            "top_playlists": [format_playlist(p) if "tracks" in p else p for p in feed.get("top_playlists", [])],
            "new_albums": [format_album(a) for a in feed.get("new_albums", [])],
            "charts": [format_song(s) for s in feed.get("charts", [])],
            "popular_artists": [format_artist(art) for art in feed.get("popular_artists", [])],
        }
    except Exception:
        logger.exception("home_feed failed")
        raise HTTPException(status_code=502, detail="Unable to load home feed.")


# ---------------------------------------------------------------------------
# Catalog Details
# ---------------------------------------------------------------------------

@app.get("/album", tags=["catalog"])
async def get_album(
    album_id: str = Query(..., min_length=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        album = await provider.get_album(album_id)
    except Exception:
        logger.exception("get_album failed for album_id=%s", album_id)
        raise HTTPException(status_code=502, detail="Unable to load album.")
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found.")
    return format_album(album)


@app.get("/artist", tags=["catalog"])
async def get_artist(
    artist_id: str = Query(..., min_length=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        artist = await provider.get_artist(artist_id)
    except Exception:
        logger.exception("get_artist failed for artist_id=%s", artist_id)
        raise HTTPException(status_code=502, detail="Unable to load artist.")
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found.")
    return format_artist(artist)


@app.get("/playlist", tags=["catalog"])
async def get_playlist(
    playlist_id: str = Query(..., min_length=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        playlist = await provider.get_playlist(playlist_id)
    except Exception:
        logger.exception("get_playlist failed for playlist_id=%s", playlist_id)
        raise HTTPException(status_code=502, detail="Unable to load playlist.")
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    return format_playlist(playlist)


@app.get("/lyrics", tags=["catalog"])
async def get_lyrics(
    song_id: str = Query(..., min_length=1),
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        lyrics = await provider.get_lyrics(song_id)
    except Exception:
        logger.exception("get_lyrics failed for song_id=%s", song_id)
        raise HTTPException(status_code=502, detail="Unable to load lyrics.")
    if not lyrics:
        return {"song_id": song_id, "available": False, "lyrics": None}
    return {"song_id": song_id, "available": True, "lyrics": lyrics, "synced": False}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@app.post("/recommendations", tags=["recommendations"])
async def recommendations(
    payload: RecommendationRequest,
    provider: CatalogProvider = Depends(get_catalog_provider),
) -> Dict[str, Any]:
    try:
        seed_dict = payload.seed_track.model_dump(by_alias=False)
        seed_dict["stream_url"] = seed_dict.get("stream_url") or payload.seed_track.stream_url

        queries = engine.generate_candidate_queries(seed_dict)
        candidate_pool = await provider.get_candidate_pool(queries)
        candidate_pool = [format_song(c) for c in candidate_pool]

        ranked = engine.rank_candidates(
            seed_track=seed_dict,
            candidates=candidate_pool,
            exclude_ids=payload.exclude_ids,
            top_k=payload.top_k,
        )
        return {"seed_id": seed_dict.get("id"), "count": len(ranked), "results": ranked}
    except HTTPException:
        raise
    except Exception:
        logger.exception("recommendations failed")
        raise HTTPException(status_code=502, detail="Unable to generate recommendations.")


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )

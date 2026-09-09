"""
providers.py

Defines the CatalogProvider abstraction and provides:
1. RealCatalogProvider: Backed by live high-bitrate streaming endpoints
   with server-side 3DES decryption for ready-to-play HTTPS streams.
2. MockCatalogProvider: Fallback in-memory provider.
"""

from __future__ import annotations

import base64
import requests
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pyDes import des, ECB, PAD_PKCS5

from catalog_data import ALBUMS, ARTISTS, LYRICS_DB, SONGS

# ---------------------------------------------------------------------------
# Decryption & Extraction Helpers
# ---------------------------------------------------------------------------

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


def format_saavn_track(item: dict) -> Optional[Dict[str, Any]]:
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
        year = None

    raw_dur = more.get("duration") or item.get("duration") or 0
    try:
        duration = int(raw_dur)
    except (ValueError, TypeError):
        duration = 0

    image_url = (item.get("image") or "").replace("50x50", "500x500").replace("150x150", "500x500")

    return {
        "id": str(item.get("id")),
        "title": item.get("title") or item.get("song") or "Unknown Title",
        "artist": more.get("singers") or item.get("primary_artists") or item.get("subtitle") or "Unknown Artist",
        "album": more.get("album") or "",
        "year": year,
        "language": (item.get("language") or more.get("language") or "hindi").strip().lower(),
        "image": image_url,
        "stream_url": stream,
        "duration": duration,
        "album_id": str(more.get("album_id") or ""),
        "artist_id": str(more.get("primary_artists_id") or ""),
    }


# ---------------------------------------------------------------------------
# Abstract Base Provider
# ---------------------------------------------------------------------------

class CatalogProvider(ABC):
    @abstractmethod
    async def search_songs(self, query: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def search_all(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        ...

    @abstractmethod
    async def get_home_feed(self) -> Dict[str, List[Dict[str, Any]]]:
        ...

    @abstractmethod
    async def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_lyrics(self, song_id: str) -> Optional[str]:
        ...

    @abstractmethod
    async def get_candidate_pool(self, queries: List[str]) -> List[Dict[str, Any]]:
        ...


# ---------------------------------------------------------------------------
# Production Provider (Live Streaming & Decryption)
# ---------------------------------------------------------------------------

class RealCatalogProvider(CatalogProvider):
    def __init__(self) -> None:
        self._headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async def search_songs(self, query: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&p={page}&n={page_size}"
        try:
            res = requests.get(url, headers=self._headers, timeout=10).json()
            raw_list = res.get("results", []) if isinstance(res, dict) else []
            formatted = []
            for s in raw_list:
                track = format_saavn_track(s)
                if track:
                    formatted.append(track)
            return formatted
        except Exception:
            return []

    async def search_all(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        songs = await self.search_songs(query, page=1, page_size=15)
        albums: List[Dict[str, Any]] = []
        artists: List[Dict[str, Any]] = []

        try:
            url = f"https://www.jiosaavn.com/api.php?__call=autocomplete.get&query={query}&_format=json&_marker=0&api_version=4"
            res = requests.get(url, headers=self._headers, timeout=10).json()

            for alb in res.get("albums", {}).get("data", []):
                albums.append({
                    "id": str(alb.get("id")),
                    "title": alb.get("title") or "Unknown Album",
                    "artist": alb.get("music") or "Unknown Artist",
                    "image": (alb.get("image") or "").replace("50x50", "500x500").replace("150x150", "500x500"),
                    "year": int(alb.get("year")) if str(alb.get("year", "")).isdigit() else None,
                })

            for art in res.get("artists", {}).get("data", []):
                artists.append({
                    "id": str(art.get("id")),
                    "name": art.get("name") or art.get("title") or "Unknown Artist",
                    "image": (art.get("image") or "").replace("50x50", "500x500").replace("150x150", "500x500"),
                    "role": art.get("role", "Artist"),
                    "followers": 0,
                })
        except Exception:
            pass

        return {"songs": songs, "albums": albums, "artists": artists}

    async def get_home_feed(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
            res = requests.get(url, headers=self._headers, timeout=10).json()

            trending_raw = res.get("new_trending", [])
            new_trending = []
            if isinstance(trending_raw, list):
                for item in trending_raw:
                    t = format_saavn_track(item)
                    if t:
                        new_trending.append(t)

            charts_raw = res.get("charts", [])
            charts = []
            if isinstance(charts_raw, list):
                for item in charts_raw:
                    t = format_saavn_track(item)
                    if t:
                        charts.append(t)

            top_playlists = []
            for pl in res.get("top_playlists", []):
                top_playlists.append({
                    "id": str(pl.get("id")),
                    "title": pl.get("title") or pl.get("listname") or "Featured Playlist",
                    "image": (pl.get("image") or "").replace("150x150", "500x500"),
                    "songCount": int(pl.get("count", 20)) if str(pl.get("count", "")).isdigit() else 20,
                })

            new_albums = []
            for alb in res.get("new_albums", []):
                new_albums.append({
                    "id": str(alb.get("id")),
                    "title": alb.get("title") or alb.get("name") or "New Album",
                    "artist": alb.get("subtitle") or alb.get("artist") or "Various Artists",
                    "image": (alb.get("image") or "").replace("150x150", "500x500"),
                    "year": int(alb.get("year")) if str(alb.get("year", "")).isdigit() else None,
                })

            # If live endpoint returns sparse data, fallback to search seed
            if not new_trending:
                new_trending = await self.search_songs("trending bollywood", page=1, page_size=10)
            if not charts:
                charts = await self.search_songs("top hindi hits", page=1, page_size=10)

            return {
                "new_trending": new_trending,
                "top_playlists": top_playlists,
                "new_albums": new_albums,
                "charts": charts,
            }
        except Exception:
            return {"new_trending": [], "top_playlists": [], "new_albums": [], "charts": []}

    async def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"https://www.jiosaavn.com/api.php?__call=content.getAlbumDetails&albumid={album_id}&_format=json&_marker=0&api_version=4"
            data = requests.get(url, headers=self._headers, timeout=10).json()
            if not data or not data.get("id"):
                return None

            songs_list = data.get("list", []) or data.get("songs", [])
            tracks = [format_saavn_track(s) for s in songs_list if format_saavn_track(s)]

            return {
                "id": str(data.get("id")),
                "title": data.get("title") or data.get("name") or "Unknown Album",
                "artist": data.get("primary_artists") or data.get("artist") or "Unknown Artist",
                "image": (data.get("image") or "").replace("150x150", "500x500"),
                "year": int(data.get("year")) if str(data.get("year", "")).isdigit() else None,
                "description": data.get("header_desc") or "",
                "tracks": tracks,
                "songCount": len(tracks),
            }
        except Exception:
            return None

    async def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"https://www.jiosaavn.com/api.php?__call=artist.getArtistPageDetails&artistId={artist_id}&_format=json&_marker=0&api_version=4"
            data = requests.get(url, headers=self._headers, timeout=10).json()
            if not data or not data.get("artistId"):
                return None

            top_songs = [format_saavn_track(s) for s in (data.get("topSongs", []) or data.get("songs", [])) if format_saavn_track(s)]
            top_albums = [{
                "id": str(alb.get("id")),
                "title": alb.get("title") or alb.get("name") or "Album",
                "artist": data.get("name") or "Artist",
                "year": int(alb.get("year")) if str(alb.get("year", "")).isdigit() else None,
                "image": (alb.get("image") or "").replace("150x150", "500x500"),
            } for alb in data.get("topAlbums", [])]

            return {
                "id": str(data.get("artistId")),
                "name": data.get("name") or "Unknown Artist",
                "image": (data.get("image") or "").replace("150x150", "500x500"),
                "role": "Lead Artist",
                "followers": int(data.get("follower_count", 0)) if str(data.get("follower_count", "")).isdigit() else 0,
                "top_songs": top_songs,
                "albums": top_albums,
            }
        except Exception:
            return None

    async def get_lyrics(self, song_id: str) -> Optional[str]:
        try:
            url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
            data = requests.get(url, headers=self._headers, timeout=10).json()
            return data.get("lyrics")
        except Exception:
            return None

    async def get_candidate_pool(self, queries: List[str]) -> List[Dict[str, Any]]:
        pool: Dict[str, Dict[str, Any]] = {}
        for q in queries:
            results = await self.search_songs(q, page=1, page_size=15)
            for r in results:
                pool[r["id"]] = r
        return list(pool.values())


# ---------------------------------------------------------------------------
# In-Memory Mock Provider (Retained as Fallback)
# ---------------------------------------------------------------------------

class MockCatalogProvider(CatalogProvider):
    def __init__(self) -> None:
        self._songs = SONGS
        self._albums = ALBUMS
        self._artists = ARTISTS
        self._lyrics = LYRICS_DB

    async def search_songs(self, query: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        matches = [s for s in self._songs if not q or q in s["title"].lower() or q in s["artist"].lower()]
        start = max(0, (page - 1) * page_size)
        return matches[start:start + page_size]

    async def search_all(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        q = (query or "").strip().lower()
        songs = [s for s in self._songs if not q or q in s["title"].lower()][:20]
        albums = [a for a in self._albums if not q or q in a["title"].lower()][:20]
        artists = [a for a in self._artists if not q or q in a["name"].lower()][:20]
        return {"songs": songs, "albums": albums, "artists": artists}

    async def get_home_feed(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "new_trending": sorted(self._songs, key=lambda s: -s["year"])[:8],
            "top_playlists": [{"id": "pl_1", "title": "Late Night Drive", "image": "https://picsum.photos/seed/p1/600/600", "songCount": 18}],
            "new_albums": sorted(self._albums, key=lambda a: -a["year"])[:6],
            "charts": list(reversed(self._songs))[:10],
        }

    async def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        alb = next((a for a in self._albums if a["id"] == album_id), None)
        if not alb:
            return None
        tracks = [s for s in self._songs if s.get("album_id") == album_id]
        return {**alb, "tracks": tracks, "songCount": len(tracks)}

    async def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        art = next((a for a in self._artists if a["id"] == artist_id), None)
        if not art:
            return None
        top_songs = [s for s in self._songs if s.get("artist_id") == artist_id]
        albums = [a for a in self._albums if a.get("artist_id") == artist_id]
        return {**art, "top_songs": top_songs, "albums": albums}

    async def get_lyrics(self, song_id: str) -> Optional[str]:
        return self._lyrics.get(song_id)

    async def get_candidate_pool(self, queries: List[str]) -> List[Dict[str, Any]]:
        pool = {s["id"]: s for s in self._songs}
        return list(pool.values())


# ---------------------------------------------------------------------------
# Factory Hook (Switching directly to RealCatalogProvider)
# ---------------------------------------------------------------------------

def get_catalog_provider() -> CatalogProvider:
    return RealCatalogProvider()

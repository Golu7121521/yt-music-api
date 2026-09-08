import requests
import base64
from pyDes import des, ECB, PAD_PKCS5

SECRET_KEY = b"38346591"

def decrypt_url(encrypted_url: str) -> str:
    if not encrypted_url:
        return ""
    try:
        iv = b""
        k = des(SECRET_KEY, ECB, iv, pad=None, padmode=PAD_PKCS5)
        decrypted = k.decrypt(base64.b64decode(encrypted_url)).decode('utf-8')
        if decrypted.startswith("http://"):
            decrypted = decrypted.replace("http://", "https://", 1)
        if "_96.mp4" in decrypted:
            decrypted = decrypted.replace("_96.mp4", "_160.mp4")
        return decrypted
    except Exception:
        return ""

def format_track(item: dict) -> dict:
    if not isinstance(item, dict):
        return None
    more = item.get("more_info", {})
    enc_url = more.get("encrypted_media_url")
    stream = decrypt_url(enc_url)
    if not stream:
        return None

    # Year normalization
    raw_year = item.get("year") or more.get("year") or "0"
    try:
        clean_year = int(raw_year)
    except ValueError:
        clean_year = 0

    return {
        "id": str(item.get("id")),
        "title": item.get("title") or item.get("song") or "",
        "artist": more.get("singers") or item.get("primary_artists") or item.get("subtitle") or "Unknown",
        "album": more.get("album") or "",
        "year": clean_year,
        "language": (item.get("language") or more.get("language") or "hindi").lower(),
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "stream_url": stream
    }

def fetch_search(query: str, page: int = 1, count: int = 20) -> list:
    url = f"https://www.jiosaavn.com/api.php?__call=search.getResults&q={query}&_format=json&_marker=0&api_version=4&p={page}&n={count}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers).json()
        raw_list = res.get("results", []) if isinstance(res, dict) else []
        return [t for t in [format_track(s) for s in raw_list] if t]
    except Exception:
        return []

def fetch_home():
    url = "https://www.jiosaavn.com/api.php?__call=webapi.getLaunchData&api_version=4&_format=json&_marker=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    return requests.get(url, headers=headers).json()

def fetch_lyrics(song_id: str):
    url = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&lyrics_id={song_id}&_format=json&_marker=0&api_version=4"
    headers = {"User-Agent": "Mozilla/5.0"}
    return requests.get(url, headers=headers).json().get("lyrics", "Lyrics not available.")

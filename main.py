from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import yt_dlp

app = FastAPI(title="YT Music Custom API")

# Add CORS Middleware to allow requests from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

ytmusic = YTMusic()

@app.get("/")
def home():
    return {"message": "Welcome to Custom YT Music API! Server is running."}

# 1. Search & Get Stream URL (Gaana play karne ke liye)
@app.get("/play")
def play_song(query: str):
    try:
        search_results = ytmusic.search(query, filter="songs")
        if not search_results:
            raise HTTPException(status_code=404, detail="Song not found")
            
        top_song = search_results[0]
        video_id = top_song['videoId']
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            info_dict = ydl.extract_info(video_url, download=False)
            stream_url = info_dict.get('url', None)

        return {
            "status": "success",
            "title": top_song.get('title'),
            "artist": top_song['artists'][0]['name'] if top_song.get('artists') else "Unknown",
            "video_id": video_id,
            "thumbnail": top_song.get('thumbnails', [{}])[-1].get('url', ''),
            "stream_url": stream_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Charts Endpoint (Trending Now ke liye)
@app.get("/charts")
def get_charts(country: str = "IN"):
    try:
        charts_data = ytmusic.get_charts(country=country)
        return {
            "status": "success",
            "trending_videos": charts_data.get("videos", {}).get("items", []),
            "top_songs": charts_data.get("tracks", {}).get("items", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Home Recommendations Endpoint (Home Tab ke liye)
@app.get("/home")
def get_home():
    try:
        home_feed = ytmusic.get_home(limit=5)
        return {
            "status": "success",
            "feed": home_feed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

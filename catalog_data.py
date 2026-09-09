"""
catalog_data.py

Static, self-contained mock catalog used by MockCatalogProvider so the API
runs standalone with zero external dependencies. All artwork and stream URLs
point to freely-licensed placeholder/sample media so the project is runnable
out of the box.

Replace MockCatalogProvider in providers.py with a real implementation that
talks to your internal/authorized CDN to go to production; the route layer
in main.py never needs to change.
"""

from typing import Any, Dict, List

# A small set of freely-usable sample MP3s (public domain / CC0 test assets)
# used purely so the client has something real to stream during development.
_SAMPLE_STREAMS = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
]

_ARTWORK = [
    "https://picsum.photos/seed/album1/600/600",
    "https://picsum.photos/seed/album2/600/600",
    "https://picsum.photos/seed/album3/600/600",
    "https://picsum.photos/seed/album4/600/600",
    "https://picsum.photos/seed/album5/600/600",
    "https://picsum.photos/seed/album6/600/600",
    "https://picsum.photos/seed/album7/600/600",
    "https://picsum.photos/seed/album8/600/600",
]

ARTISTS: List[Dict[str, Any]] = [
    {"id": "art_001", "name": "Nova Ridge", "image": "https://picsum.photos/seed/artist1/600/600", "role": "Singer", "followers": 154_200},
    {"id": "art_002", "name": "Kavya Sen", "image": "https://picsum.photos/seed/artist2/600/600", "role": "Singer-Songwriter", "followers": 92_800},
    {"id": "art_003", "name": "The Midnight Frequency", "image": "https://picsum.photos/seed/artist3/600/600", "role": "Band", "followers": 310_500},
    {"id": "art_004", "name": "Arjun Rao", "image": "https://picsum.photos/seed/artist4/600/600", "role": "Playback Singer", "followers": 68_900},
    {"id": "art_005", "name": "Lila Moreno", "image": "https://picsum.photos/seed/artist5/600/600", "role": "Singer", "followers": 210_000},
    {"id": "art_006", "name": "Echo Valley", "image": "https://picsum.photos/seed/artist6/600/600", "role": "Band", "followers": 45_300},
]

ALBUMS: List[Dict[str, Any]] = [
    {"id": "alb_001", "title": "Afterglow", "artist": "Nova Ridge", "artist_id": "art_001", "image": _ARTWORK[0], "year": 2022, "description": "A synth-driven exploration of late-night city life."},
    {"id": "alb_002", "title": "Paper Moons", "artist": "Kavya Sen", "artist_id": "art_002", "image": _ARTWORK[1], "year": 2019, "description": "Intimate acoustic ballads about memory and distance."},
    {"id": "alb_003", "title": "Static & Stars", "artist": "The Midnight Frequency", "artist_id": "art_003", "image": _ARTWORK[2], "year": 2023, "description": "A concept album about signals lost in space."},
    {"id": "alb_004", "title": "Ghar Wapsi", "artist": "Arjun Rao", "artist_id": "art_004", "image": _ARTWORK[3], "year": 1998, "description": "Classic 90s melodies celebrating homecoming."},
    {"id": "alb_005", "title": "Sundown Radio", "artist": "Lila Moreno", "artist_id": "art_005", "image": _ARTWORK[4], "year": 2021, "description": "Warm retro-pop with a modern production edge."},
    {"id": "alb_006", "title": "Low Tide", "artist": "Echo Valley", "artist_id": "art_006", "image": _ARTWORK[5], "year": 2020, "description": "A moody indie-rock record recorded live to tape."},
]

# 24 tracks distributed across the albums above.
SONGS: List[Dict[str, Any]] = [
    {"id": "song_001", "title": "Afterglow", "artist": "Nova Ridge", "artist_id": "art_001", "album": "Afterglow", "album_id": "alb_001", "year": 2022, "language": "english", "image": _ARTWORK[0], "stream_url": _SAMPLE_STREAMS[0], "duration": 214},
    {"id": "song_002", "title": "City Lights Fade", "artist": "Nova Ridge", "artist_id": "art_001", "album": "Afterglow", "album_id": "alb_001", "year": 2022, "language": "english", "image": _ARTWORK[0], "stream_url": _SAMPLE_STREAMS[1], "duration": 198},
    {"id": "song_003", "title": "Neon Rain", "artist": "Nova Ridge", "artist_id": "art_001", "album": "Afterglow", "album_id": "alb_001", "year": 2022, "language": "english", "image": _ARTWORK[0], "stream_url": _SAMPLE_STREAMS[2], "duration": 227},
    {"id": "song_004", "title": "Static Heartbeat", "artist": "Nova Ridge", "artist_id": "art_001", "album": "Afterglow", "album_id": "alb_001", "year": 2022, "language": "english", "image": _ARTWORK[0], "stream_url": _SAMPLE_STREAMS[3], "duration": 189},

    {"id": "song_005", "title": "Paper Moons", "artist": "Kavya Sen", "artist_id": "art_002", "album": "Paper Moons", "album_id": "alb_002", "year": 2019, "language": "hindi", "image": _ARTWORK[1], "stream_url": _SAMPLE_STREAMS[1], "duration": 241},
    {"id": "song_006", "title": "Dhoop Chhaon", "artist": "Kavya Sen", "artist_id": "art_002", "album": "Paper Moons", "album_id": "alb_002", "year": 2019, "language": "hindi", "image": _ARTWORK[1], "stream_url": _SAMPLE_STREAMS[2], "duration": 205},
    {"id": "song_007", "title": "Faded Letters", "artist": "Kavya Sen", "artist_id": "art_002", "album": "Paper Moons", "album_id": "alb_002", "year": 2019, "language": "hindi", "image": _ARTWORK[1], "stream_url": _SAMPLE_STREAMS[3], "duration": 178},
    {"id": "song_008", "title": "Quiet Rooms", "artist": "Kavya Sen", "artist_id": "art_002", "album": "Paper Moons", "album_id": "alb_002", "year": 2019, "language": "hindi", "image": _ARTWORK[1], "stream_url": _SAMPLE_STREAMS[4], "duration": 233},

    {"id": "song_009", "title": "Static & Stars", "artist": "The Midnight Frequency", "artist_id": "art_003", "album": "Static & Stars", "album_id": "alb_003", "year": 2023, "language": "english", "image": _ARTWORK[2], "stream_url": _SAMPLE_STREAMS[2], "duration": 256},
    {"id": "song_010", "title": "Transmission 7", "artist": "The Midnight Frequency", "artist_id": "art_003", "album": "Static & Stars", "album_id": "alb_003", "year": 2023, "language": "english", "image": _ARTWORK[2], "stream_url": _SAMPLE_STREAMS[3], "duration": 264},
    {"id": "song_011", "title": "Orbit Decay", "artist": "The Midnight Frequency", "artist_id": "art_003", "album": "Static & Stars", "album_id": "alb_003", "year": 2023, "language": "english", "image": _ARTWORK[2], "stream_url": _SAMPLE_STREAMS[4], "duration": 199},
    {"id": "song_012", "title": "Lost Signal", "artist": "The Midnight Frequency", "artist_id": "art_003", "album": "Static & Stars", "album_id": "alb_003", "year": 2023, "language": "english", "image": _ARTWORK[2], "stream_url": _SAMPLE_STREAMS[5], "duration": 221},

    {"id": "song_013", "title": "Ghar Wapsi", "artist": "Arjun Rao", "artist_id": "art_004", "album": "Ghar Wapsi", "album_id": "alb_004", "year": 1998, "language": "hindi", "image": _ARTWORK[3], "stream_url": _SAMPLE_STREAMS[3], "duration": 288},
    {"id": "song_014", "title": "Purani Yaadein", "artist": "Arjun Rao", "artist_id": "art_004", "album": "Ghar Wapsi", "album_id": "alb_004", "year": 1998, "language": "hindi", "image": _ARTWORK[3], "stream_url": _SAMPLE_STREAMS[4], "duration": 301},
    {"id": "song_015", "title": "Sham-e-Dilli", "artist": "Arjun Rao", "artist_id": "art_004", "album": "Ghar Wapsi", "album_id": "alb_004", "year": 1998, "language": "hindi", "image": _ARTWORK[3], "stream_url": _SAMPLE_STREAMS[5], "duration": 274},
    {"id": "song_016", "title": "Barsaat Ki Raat", "artist": "Arjun Rao", "artist_id": "art_004", "album": "Ghar Wapsi", "album_id": "alb_004", "year": 1997, "language": "hindi", "image": _ARTWORK[3], "stream_url": _SAMPLE_STREAMS[0], "duration": 250},

    {"id": "song_017", "title": "Sundown Radio", "artist": "Lila Moreno", "artist_id": "art_005", "album": "Sundown Radio", "album_id": "alb_005", "year": 2021, "language": "english", "image": _ARTWORK[4], "stream_url": _SAMPLE_STREAMS[4], "duration": 203},
    {"id": "song_018", "title": "Golden Hour", "artist": "Lila Moreno", "artist_id": "art_005", "album": "Sundown Radio", "album_id": "alb_005", "year": 2021, "language": "english", "image": _ARTWORK[4], "stream_url": _SAMPLE_STREAMS[5], "duration": 187},
    {"id": "song_019", "title": "Drive Slow", "artist": "Lila Moreno", "artist_id": "art_005", "album": "Sundown Radio", "album_id": "alb_005", "year": 2021, "language": "english", "image": _ARTWORK[4], "stream_url": _SAMPLE_STREAMS[0], "duration": 210},
    {"id": "song_020", "title": "Palm Static", "artist": "Lila Moreno", "artist_id": "art_005", "album": "Sundown Radio", "album_id": "alb_005", "year": 2020, "language": "english", "image": _ARTWORK[4], "stream_url": _SAMPLE_STREAMS[1], "duration": 195},

    {"id": "song_021", "title": "Low Tide", "artist": "Echo Valley", "artist_id": "art_006", "album": "Low Tide", "album_id": "alb_006", "year": 2020, "language": "english", "image": _ARTWORK[5], "stream_url": _SAMPLE_STREAMS[5], "duration": 244},
    {"id": "song_022", "title": "Salt Air", "artist": "Echo Valley", "artist_id": "art_006", "album": "Low Tide", "album_id": "alb_006", "year": 2020, "language": "english", "image": _ARTWORK[5], "stream_url": _SAMPLE_STREAMS[0], "duration": 219},
    {"id": "song_023", "title": "Harbor Lights", "artist": "Echo Valley", "artist_id": "art_006", "album": "Low Tide", "album_id": "alb_006", "year": 2020, "language": "english", "image": _ARTWORK[5], "stream_url": _SAMPLE_STREAMS[1], "duration": 233},
    {"id": "song_024", "title": "Undertow", "artist": "Echo Valley", "artist_id": "art_006", "album": "Low Tide", "album_id": "alb_006", "year": 2019, "language": "english", "image": _ARTWORK[5], "stream_url": _SAMPLE_STREAMS[2], "duration": 261},
]

LYRICS_DB: Dict[str, str] = {
    "song_001": (
        "City lights flicker, afterglow in the haze\n"
        "We're chasing shadows through the amber days\n"
        "Hold on to the static, hold on to the sound\n"
        "This is where the afterglow is found\n\n"
        "[Verse 2]\n"
        "Neon reflections on the wet concrete\n"
        "Every heartbeat matches every street\n"
        "Nothing lasts forever but tonight it feels like it might\n"
    ),
    "song_005": (
        "Paper moons hang low tonight\n"
        "Painted skies in fading light\n"
        "I wrote your name across the tide\n"
        "And watched it wash away outside\n\n"
        "[Chorus]\n"
        "Dhoop chhaon, dhoop chhaon\n"
        "Zindagi hai dhoop chhaon\n"
    ),
    "song_013": (
        "Ghar wapsi ka safar lamba tha\n"
        "Har mod pe ek yaadgar tha\n"
        "Ab jo dekha apna aangan\n"
        "Toh laga sab kuch waapas paaya\n"
    ),
}

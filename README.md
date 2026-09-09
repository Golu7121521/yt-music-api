# MyMusic Backend — FastAPI

Clean REST API powering the MyMusic Flutter client. Ships with a fully
self-contained mock catalog so it runs standalone with zero external
dependencies — swap in your real internal/authorized CDN provider later
without touching route code.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive OpenAPI docs.

## Architecture

```
backend/
  main.py          # FastAPI app: routes, CORS, defensive JSON formatting
  engine.py         # Standalone recommendation engine (no HTTP deps)
  providers.py      # CatalogProvider abstraction + MockCatalogProvider
  catalog_data.py   # Static sample catalog (songs/albums/artists/lyrics)
  schemas.py        # Pydantic request/response models
```

### Swapping in a real data source

Everything in `main.py` depends only on the `CatalogProvider` interface
defined in `providers.py`. To connect your real internal/authorized audio
CDN:

1. Implement a new class in `providers.py` that extends `CatalogProvider`
   and implements all abstract methods, calling your actual CDN/catalog API.
2. Update `get_catalog_provider()` to return an instance of your new class
   instead of `MockCatalogProvider()`.
3. No changes are needed in `main.py` — every route already works purely
   against the abstraction.

Each song object returned by your provider should look like:

```json
{
  "id": "song_001",
  "title": "Afterglow",
  "artist": "Nova Ridge",
  "album": "Afterglow",
  "year": 2022,
  "language": "english",
  "image": "https://.../artwork.jpg",
  "stream_url": "https://.../track.mp3",
  "duration": 214
}
```

`main.py`'s `format_song()` defensively sanitizes whatever your provider
returns (missing fields, wrong types, `http://` URLs upgraded to `https://`)
before it reaches the client, so a slightly messy upstream response won't
crash the API.

## Endpoints

| Method | Path              | Description                                   |
|--------|-------------------|------------------------------------------------|
| GET    | `/search`         | Paginated song search                          |
| GET    | `/search/all`     | Multi-category search (songs/albums/artists)   |
| GET    | `/home-feed`      | Home screen sections                           |
| GET    | `/album`          | Album details + tracklist                      |
| GET    | `/artist`         | Artist profile + top songs + albums            |
| GET    | `/lyrics`         | Song lyrics                                    |
| POST   | `/recommendations`| Content-based recommendations for a seed track |

## Recommendation engine

`engine.py` is fully decoupled from FastAPI and can be unit tested directly:

- `generate_candidate_queries(seed_track)` — produces search queries (same
  artist, artist + era, same album, language + era) to gather a candidate
  pool from any `CatalogProvider`.
- `rank_candidates(seed_track, candidates, exclude_ids, top_k)` — filters
  out contamination (devotional/kids/spoken-word content, unless the seed
  itself is in one of those categories) and extreme era mismatches
  (>40 years apart), then scores remaining candidates on:
  - Artist synergy (+0.40 for exact artist match)
  - Era proximity (+0.25 decaying boost within ±4 years)
  - Same album (+0.15)
  - Language match (+0.10)

Try it directly:

```python
import engine
from catalog_data import SONGS

seed = SONGS[0]
queries = engine.generate_candidate_queries(seed)
ranked = engine.rank_candidates(seed, SONGS, top_k=5)
```

## CORS

Wide open (`allow_origins=["*"]`) for development and mobile clients.
Tighten this in `main.py` before deploying a web build.

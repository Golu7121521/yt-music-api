"""
engine.py
Standalone content-based recommendation engine.

Responsible for:
  - Generating candidate search queries from a seed track
  - Normalizing features across candidates
  - Applying a temporal "era proximity" boost (Year +/- 4)
  - Applying an artist synergy boost
  - Filtering out contamination (devotional/spiritual/kids/extreme mismatches)
  - Producing a final ranked, scored list of candidate tracks

This module has zero FastAPI / HTTP dependencies so it can be unit tested
and reused independently of the web layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

ERA_WINDOW_YEARS = 4
ERA_BOOST = 0.25
ARTIST_SYNERGY_BOOST = 0.40
SAME_ALBUM_BOOST = 0.15
LANGUAGE_MATCH_BOOST = 0.10

# Keywords used to flag/penalize contamination categories. Matching is done
# on lowercased title/album/artist text. This is a coarse content-safety /
# relevance filter, not a moderation system.
CONTAMINATION_KEYWORDS = {
    "devotional": [
        "bhajan", "aarti", "mantra", "chalisa", "kirtan", "stotra",
        "devotional", "gospel", "hymn", "psalm", "shabad", "qawwali",
        "naat", "puja",
    ],
    "kids": [
        "nursery", "rhyme", "lullaby", "kids song", "children song",
        "cartoon theme", "poem for kids",
    ],
    "spoken_word": [
        "speech", "pravachan", "discourse", "audiobook", "interview",
        "podcast episode",
    ],
}

_ALL_CONTAMINATION_TERMS = [
    term for terms in CONTAMINATION_KEYWORDS.values() for term in terms
]


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class Track:
    """Normalized internal representation of a track used by the engine."""

    id: str
    title: str
    artist: str
    album: str = ""
    year: Optional[int] = None
    language: str = ""
    image: str = ""
    stream_url: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (str, int, float)):
            return str(value).strip()
        return ""

    @staticmethod
    def _safe_year(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(19|20)\d{2}", value)
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    return None
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Track":
        """Defensively build a Track from an arbitrary dict, tolerating
        missing keys, nulls, and wrong-typed values without raising."""
        if not isinstance(data, dict):
            data = {}
        return cls(
            id=cls._safe_str(data.get("id")) or cls._safe_str(data.get("track_id")),
            title=cls._safe_str(data.get("title")) or "Unknown Title",
            artist=cls._safe_str(data.get("artist")) or "Unknown Artist",
            album=cls._safe_str(data.get("album")),
            year=cls._safe_year(data.get("year")),
            language=cls._safe_str(data.get("language")).lower(),
            image=cls._safe_str(data.get("image") or data.get("artwork")),
            stream_url=cls._safe_str(data.get("stream_url") or data.get("streamUrl")),
            raw=data,
        )

    def to_public_dict(self, score: Optional[float] = None) -> Dict[str, Any]:
        out = {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "year": self.year,
            "language": self.language,
            "image": self.image,
            "stream_url": self.stream_url,
        }
        if score is not None:
            out["similarity_score"] = round(float(score), 4)
        return out

    def text_blob(self) -> str:
        return " ".join([self.title, self.album, self.artist]).lower()


# --------------------------------------------------------------------------
# Candidate query generation
# --------------------------------------------------------------------------

def generate_candidate_queries(seed_track: Dict[str, Any]) -> List[str]:
    """
    Given a seed track, produce a list of textual search queries that a
    CatalogProvider can use to fetch a pool of plausible candidate tracks.

    Strategy:
      - Same artist (primary signal)
      - Artist + era decade (captures "artist's other work from that period")
      - Same album (captures other tracks off the same record)
      - Same language + era decade (broad discovery net)
    """
    seed = Track.from_dict(seed_track)
    queries: List[str] = []

    if seed.artist and seed.artist != "Unknown Artist":
        queries.append(seed.artist)

    if seed.year:
        decade_start = (seed.year // 10) * 10
        if seed.artist and seed.artist != "Unknown Artist":
            queries.append(f"{seed.artist} {decade_start}s")
        if seed.language:
            queries.append(f"{seed.language} {decade_start}s hits")

    if seed.album:
        queries.append(seed.album)

    if seed.language and seed.artist != "Unknown Artist":
        queries.append(f"{seed.language} {seed.artist} similar")

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for q in queries:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(q.strip())

    if not deduped:
        # Fallback: at minimum, search on the title so we return *something*
        deduped.append(seed.title)

    return deduped


# --------------------------------------------------------------------------
# Contamination filtering
# --------------------------------------------------------------------------

def _is_contaminated(track: Track, seed: Track) -> bool:
    """
    Returns True if the candidate should be purged from results.

    A track is considered contaminated if:
      - Its text contains devotional/kids/spoken-word keywords AND the seed
        track itself is not from one of those categories (i.e. we don't want
        to inject a bhajan into a pop-song queue, but if the user is *already*
        listening to devotional music we should not purge similar content).
    """
    seed_blob = seed.text_blob()
    seed_is_flagged = any(term in seed_blob for term in _ALL_CONTAMINATION_TERMS)
    if seed_is_flagged:
        return False

    candidate_blob = track.text_blob()
    return any(term in candidate_blob for term in _ALL_CONTAMINATION_TERMS)


def _is_extreme_acoustic_mismatch(track: Track, seed: Track) -> bool:
    """
    Coarse era-mismatch guard: if both tracks have known years and they are
    more than 40 years apart, treat it as too dissonant a jump for a
    "similar vibe" queue (e.g. a 1965 track injected into a 2020 pop queue).
    """
    if track.year is None or seed.year is None:
        return False
    return abs(track.year - seed.year) > 40


# --------------------------------------------------------------------------
# Scoring / ranking
# --------------------------------------------------------------------------

def _score_candidate(track: Track, seed: Track) -> float:
    score = 0.5  # baseline relevance for having matched a candidate query

    # Artist synergy: same artist is a very strong signal
    if track.artist and seed.artist and track.artist.lower() == seed.artist.lower():
        score += ARTIST_SYNERGY_BOOST

    # Era proximity boost: within +/- ERA_WINDOW_YEARS gets a flat boost that
    # decays linearly the further out it is (up to the window edge).
    if track.year is not None and seed.year is not None:
        diff = abs(track.year - seed.year)
        if diff <= ERA_WINDOW_YEARS:
            decay = 1 - (diff / (ERA_WINDOW_YEARS + 1))
            score += ERA_BOOST * decay

    # Same-album boost
    if track.album and seed.album and track.album.lower() == seed.album.lower():
        score += SAME_ALBUM_BOOST

    # Language match boost
    if track.language and seed.language and track.language == seed.language:
        score += LANGUAGE_MATCH_BOOST

    return score


def rank_candidates(
    seed_track: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    exclude_ids: Optional[List[str]] = None,
    top_k: int = 15,
) -> List[Dict[str, Any]]:
    """
    Filters contamination/extreme mismatches out of `candidates`, scores the
    remainder against `seed_track`, and returns the top_k results sorted by
    descending similarity score.
    """
    seed = Track.from_dict(seed_track)
    exclude_ids = set(exclude_ids or [])
    exclude_ids.add(seed.id)

    seen_ids = set()
    scored: List[Dict[str, Any]] = []

    for raw in candidates:
        track = Track.from_dict(raw)

        if not track.id or track.id in exclude_ids or track.id in seen_ids:
            continue
        if not track.stream_url:
            # Never recommend a track the client can't actually play.
            continue
        if _is_contaminated(track, seed):
            continue
        if _is_extreme_acoustic_mismatch(track, seed):
            continue

        seen_ids.add(track.id)
        score = _score_candidate(track, seed)
        scored.append(track.to_public_dict(score=score))

    scored.sort(key=lambda t: t["similarity_score"], reverse=True)
    return scored[: max(0, top_k)]

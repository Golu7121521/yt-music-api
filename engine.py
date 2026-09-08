"""
engine.py

Standalone Content-Based Recommendation Engine for track metadata.
No external data-fetching, no network calls, no proprietary streaming code.
Consumes seed_track / candidate_tracks dicts supplied by an external data provider.

Track dict contract:
{
    "id": str,
    "title": str,
    "artist": str,          # e.g. "Kumar Sanu, Alka Yagnik"
    "album": str,
    "year": int,
    "language": str,
    "tags": list[str]       # optional
}
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Set, Tuple


# --------------------------------------------------------------------------
# Constants / lexicons
# --------------------------------------------------------------------------

CURRENT_YEAR_FALLBACK = 2026  # used only if a candidate year is missing/invalid

# Mood/sub-genre keyword lexicon. Token -> canonical mood tag.
# Matching is done against tokens extracted from title/album (and tags, if present).
MOOD_LEXICON: Dict[str, List[str]] = {
    "romantic": ["pyaar", "pyar", "ishq", "mohabbat", "dil", "love", "romance",
                 "romantic", "dilbar", "jaan", "yaar", "saathiya"],
    "sad": ["dard", "judaai", "tanhai", "sad", "gham", "bewafa", "yaad",
            "tears", "alone", "akela", "breakup", "viraha"],
    "dance": ["dance", "party", "beat", "dhamaka", "nachle", "masti",
              "club", "remix", "item"],
    "chill": ["chill", "lofi", "lo-fi", "sukoon", "shanti", "calm", "soft"],
    "unplugged": ["unplugged", "acoustic", "live", "session"],
    "devotional": ["bhajan", "aarti", "mantra", "bhakti", "devotional",
                   "chalisa", "stuti", "prarthana", "spiritual", "shiv",
                   "krishna", "ganesh", "durga", "hanuman"],
    "kids": ["nursery", "rhyme", "kids", "children", "cartoon", "poem",
             "balgeet", "chhota"],
    "patriotic": ["desh", "watan", "patriotic", "azaadi", "tiranga"],
    "wedding": ["shaadi", "vivah", "wedding", "sangeet", "mehendi", "baraat"],
}

# Categories treated as contamination unless explicitly present in the seed.
BLACKLIST_CATEGORIES = {"devotional", "kids"}

# Tokens that flag an "acoustic mismatch" risk (unplugged/acoustic seed vs
# high-energy candidate or vice versa) — handled separately in filtering.
ACOUSTIC_TOKENS = set(MOOD_LEXICON["unplugged"])
DANCE_TOKENS = set(MOOD_LEXICON["dance"])

_TOKEN_RE = re.compile(r"[a-zA-Z]+")


# --------------------------------------------------------------------------
# Helpers: tokenization & normalization
# --------------------------------------------------------------------------

def _tokenize(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _safe_year(track: Dict) -> Optional[int]:
    y = track.get("year")
    if isinstance(y, int) and 1900 <= y <= 2100:
        return y
    if isinstance(y, str) and y.isdigit():
        y_int = int(y)
        if 1900 <= y_int <= 2100:
            return y_int
    return None


def _decade_of(year: Optional[int]) -> Optional[int]:
    if year is None:
        return None
    return (year // 10) * 10


def _era_bucket(year: Optional[int]) -> str:
    """Coarse era cluster label, used as part of the temporal vector."""
    if year is None:
        return "unknown"
    if year < 1970:
        return "classic"
    if year < 1990:
        return "retro"
    if year < 2000:
        return "90s"
    if year < 2010:
        return "2000s"
    if year < 2020:
        return "2010s"
    return "modern"


def _split_artists(artist_field: Optional[str]) -> List[str]:
    """Split a comma/'&'/'feat.'-separated artist string into normalized names."""
    if not artist_field:
        return []
    # Normalize common separators to commas
    normalized = re.sub(r"\bfeat\.?\b|\bft\.?\b|&|/| and ", ",", artist_field, flags=re.IGNORECASE)
    parts = [p.strip().lower() for p in normalized.split(",")]
    return [p for p in parts if p]


def _extract_moods(track: Dict) -> Set[str]:
    """Derive mood/sub-genre tags from explicit tags plus title/album tokens."""
    moods: Set[str] = set()

    explicit_tags = track.get("tags") or []
    explicit_lower = {str(t).strip().lower() for t in explicit_tags}

    # Direct hits: explicit tag names that match a mood category name itself
    for category in MOOD_LEXICON:
        if category in explicit_lower:
            moods.add(category)

    tokens = set(_tokenize(track.get("title")) + _tokenize(track.get("album")))
    tokens |= explicit_lower  # tags can also contain keyword-style tokens

    for category, keywords in MOOD_LEXICON.items():
        if tokens.intersection(keywords):
            moods.add(category)

    return moods


# --------------------------------------------------------------------------
# Feature vector construction
# --------------------------------------------------------------------------

class TrackProfile:
    """Normalized feature representation of a track, built dynamically —
    nothing here is hardcoded to a specific artist/title/language."""

    __slots__ = ("track", "year", "decade", "era", "artists", "language", "moods")

    def __init__(self, track: Dict):
        self.track = track
        self.year = _safe_year(track)
        self.decade = _decade_of(self.year)
        self.era = _era_bucket(self.year)
        self.artists = _split_artists(track.get("artist"))
        self.language = (track.get("language") or "").strip().lower()
        self.moods = _extract_moods(track)

    # -- component similarity scores (each 0.0 - 1.0) ----------------------

    def temporal_similarity(self, other: "TrackProfile") -> float:
        if self.year is None or other.year is None:
            # fall back to era-bucket match only
            return 1.0 if self.era == other.era and self.era != "unknown" else 0.3
        diff = abs(self.year - other.year)
        if diff <= 4:
            return 1.0
        if diff <= 8:
            return 0.75
        if diff <= 15:
            return 0.45
        if diff <= 25:
            return 0.2
        # severe penalty for large temporal jumps (e.g. 1993 vs 2024)
        return max(0.0, 0.08 - 0.002 * (diff - 25))

    def artist_similarity(self, other: "TrackProfile") -> float:
        if not self.artists or not other.artists:
            return 0.0
        set_a, set_b = set(self.artists), set(other.artists)
        overlap = set_a.intersection(set_b)
        if not overlap:
            return 0.0
        union = set_a.union(set_b)
        jaccard = len(overlap) / len(union)
        # Boost strongly if the *primary* (first-listed) artist matches
        primary_bonus = 0.4 if self.artists[0] == other.artists[0] else 0.0
        return min(1.0, jaccard * 0.6 + primary_bonus)

    def language_lock(self, other: "TrackProfile") -> float:
        if not self.language or not other.language:
            return 0.5  # unknown language: neutral, not a hard fail
        return 1.0 if self.language == other.language else 0.0

    def mood_similarity(self, other: "TrackProfile") -> float:
        if not self.moods or not other.moods:
            return 0.5  # no mood signal either side: neutral
        overlap = self.moods.intersection(other.moods)
        union = self.moods.union(other.moods)
        return len(overlap) / len(union) if union else 0.5


# --------------------------------------------------------------------------
# Adaptive weighting
# --------------------------------------------------------------------------

def _adaptive_weights(seed_profile: TrackProfile) -> Dict[str, float]:
    """
    Base weights, then reshaped based on the seed track's own profile:
      - Older seed (pre-2005): Era Proximity dominates.
      - Seed has multiple / strong artist signal: Artist Synergy dominates.
    Weights always sum to 1.0.
    """
    weights = {
        "temporal": 0.30,
        "artist": 0.30,
        "language": 0.20,
        "mood": 0.20,
    }

    is_old_seed = seed_profile.year is not None and seed_profile.year < 2005
    is_artist_driven = len(seed_profile.artists) >= 1  # any identifiable primary artist
    multi_artist = len(seed_profile.artists) >= 2

    if is_old_seed:
        weights["temporal"] += 0.15
        weights["mood"] -= 0.05
        weights["artist"] -= 0.10

    if is_artist_driven:
        boost = 0.15 if multi_artist else 0.08
        weights["artist"] += boost
        weights["mood"] -= boost * 0.5
        weights["temporal"] -= boost * 0.5

    # Clamp negatives, then renormalize to sum to 1.0
    for k in weights:
        weights[k] = max(0.02, weights[k])
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


# --------------------------------------------------------------------------
# Similarity scoring (public API)
# --------------------------------------------------------------------------

def calculate_similarity(seed: Dict, candidate: Dict) -> float:
    """
    Returns a similarity score in [0.0, 1.0] between seed and candidate tracks.
    Weights adapt to the seed's profile (era-driven vs artist-driven), and
    large temporal jumps are penalized on top of the base temporal score.
    """
    seed_profile = TrackProfile(seed)
    cand_profile = TrackProfile(candidate)
    weights = _adaptive_weights(seed_profile)

    temporal = seed_profile.temporal_similarity(cand_profile)
    artist = seed_profile.artist_similarity(cand_profile)
    language = seed_profile.language_lock(cand_profile)
    mood = seed_profile.mood_similarity(cand_profile)

    score = (
        weights["temporal"] * temporal
        + weights["artist"] * artist
        + weights["language"] * language
        + weights["mood"] * mood
    )

    # Hard language mismatch (strict lock): steep additional penalty so
    # a sudden language swap can't be compensated for by other factors,
    # unless both languages are unknown (handled as neutral above).
    if seed_profile.language and cand_profile.language and seed_profile.language != cand_profile.language:
        score *= 0.15

    # Severe temporal-jump penalty stacks multiplicatively on top of the
    # weighted score for very large gaps (e.g. 1993 seed vs 2024 candidate).
    if seed_profile.year is not None and cand_profile.year is not None:
        gap = abs(seed_profile.year - cand_profile.year)
        if gap > 25:
            score *= 0.5
        if gap > 40:
            score *= 0.5

    return round(max(0.0, min(1.0, score)), 6)


# --------------------------------------------------------------------------
# Negative filtering (contamination blocker)
# --------------------------------------------------------------------------

def _is_contaminated(seed_moods: Set[str], candidate: Dict) -> bool:
    """
    Drops devotional / spiritual / kids tracks, and acoustic-vs-energetic
    mismatches, unless the seed itself explicitly carries that marker.
    """
    cand_moods = _extract_moods(candidate)

    # Devotional / kids hard blacklist
    contamination = cand_moods.intersection(BLACKLIST_CATEGORIES)
    if contamination and not seed_moods.intersection(BLACKLIST_CATEGORIES):
        return True

    # Acoustic/unplugged vs dance/high-energy mismatch
    cand_is_acoustic = "unplugged" in cand_moods
    cand_is_dance = "dance" in cand_moods
    seed_is_acoustic = "unplugged" in seed_moods
    seed_is_dance = "dance" in seed_moods

    if cand_is_acoustic and seed_is_dance and not seed_is_acoustic:
        return True
    if cand_is_dance and seed_is_acoustic and not seed_is_dance:
        return True

    return False


def filter_contamination(seed_track: Dict, candidates: List[Dict]) -> List[Dict]:
    """Public helper: strips blacklisted / mismatched candidates from a list."""
    seed_moods = _extract_moods(seed_track)
    return [c for c in candidates if not _is_contaminated(seed_moods, c)]


# --------------------------------------------------------------------------
# Query generator
# --------------------------------------------------------------------------

def generate_candidate_queries(seed_track: Dict) -> List[str]:
    """
    Produces 3-4 high-relevance search query strings derived dynamically
    from the seed track's era, primary artist(s), and mood — no hardcoded
    artist/title values.
    """
    profile = TrackProfile(seed_track)
    queries: List[str] = []

    era_label = profile.era if profile.era != "unknown" else ""
    decade_label = f"{profile.decade}s" if profile.decade else era_label
    lang = seed_track.get("language", "").strip().capitalize()
    primary_artist = profile.artists[0].title() if profile.artists else ""
    secondary_artist = profile.artists[1].title() if len(profile.artists) > 1 else ""

    top_mood = next(iter(profile.moods), None)
    mood_label = top_mood if top_mood else "hits"

    # Query 1: primary artist + decade + mood
    if primary_artist:
        parts = [primary_artist]
        if decade_label:
            parts.append(decade_label)
        parts.append(mood_label)
        queries.append(" ".join(parts))

    # Query 2: secondary/co-artist + decade + "best"
    if secondary_artist:
        parts = [secondary_artist]
        if decade_label:
            parts.append(decade_label)
        parts.append("best")
        queries.append(" ".join(parts))

    # Query 3: language + decade + genre descriptor
    if lang and decade_label:
        golden = "golden era" if profile.era in ("retro", "90s", "classic") else "hits"
        queries.append(f"{decade_label} {lang.lower()} {golden}")
    elif decade_label:
        queries.append(f"{decade_label} {mood_label} hits")

    # Query 4: mood + primary artist (fallback / diversification)
    if primary_artist and mood_label:
        queries.append(f"{mood_label} songs by {primary_artist}")
    elif lang:
        queries.append(f"best {lang.lower()} {mood_label} songs")

    # Deduplicate while preserving order, cap at 4
    seen = set()
    deduped = []
    for q in queries:
        q_norm = " ".join(q.split()).strip()
        if q_norm and q_norm.lower() not in seen:
            seen.add(q_norm.lower())
            deduped.append(q_norm)

    return deduped[:4] if deduped else [f"{seed_track.get('title', '')} similar songs"]


# --------------------------------------------------------------------------
# Rank & select
# --------------------------------------------------------------------------

def rank_candidates(
    seed_track: Dict,
    candidates: List[Dict],
    top_k: int = 15,
    exclude_ids: Optional[Set[str]] = None,
) -> List[Dict]:
    """
    Filters contamination, scores remaining candidates against the seed,
    and returns the top_k highest-scoring tracks (each annotated with a
    '_similarity_score' float), sorted descending by score.
    """
    exclude_ids = exclude_ids or set()

    # 1. Drop excluded ids and the seed itself
    seed_id = seed_track.get("id")
    pool = [
        c for c in candidates
        if c.get("id") not in exclude_ids and c.get("id") != seed_id
    ]

    # 2. Contamination filter
    pool = filter_contamination(seed_track, pool)

    # 3. Score
    scored: List[Tuple[float, Dict]] = []
    for candidate in pool:
        score = calculate_similarity(seed_track, candidate)
        enriched = dict(candidate)
        enriched["_similarity_score"] = score
        scored.append((score, enriched))

    # 4. Sort descending by score, stable tie-break by title for determinism
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("title", ""))))

    return [track for _, track in scored[:top_k]]


# --------------------------------------------------------------------------
# Manual smoke test (safe to remove / ignore in production import)
# --------------------------------------------------------------------------

if __name__ == "__main__":
    seed = {
        "id": "seed1",
        "title": "Tujhe Dekha To",
        "artist": "Kumar Sanu, Lata Mangeshkar",
        "album": "Dilwale Dulhania Le Jayenge",
        "year": 1995,
        "language": "hindi",
        "tags": ["romantic"],
    }

    candidates = [
        {"id": "c1", "title": "Pehla Nasha", "artist": "Udit Narayan, Sadhana Sargam",
         "album": "Jo Jeeta Wohi Sikandar", "year": 1992, "language": "hindi", "tags": ["romantic"]},
        {"id": "c2", "title": "Kal Ho Naa Ho", "artist": "Sonu Nigam",
         "album": "Kal Ho Naa Ho", "year": 2003, "language": "hindi", "tags": ["sad"]},
        {"id": "c3", "title": "Ganesh Aarti", "artist": "Anuradha Paudwal",
         "album": "Bhakti Sangeet", "year": 1998, "language": "hindi", "tags": ["devotional"]},
        {"id": "c4", "title": "Kaal Nagini", "artist": "Anonymous",
         "album": "Random", "year": 2024, "language": "hindi", "tags": ["dance"]},
        {"id": "c5", "title": "Chalte Chalte", "artist": "Kumar Sanu, Alka Yagnik",
         "album": "Pardes", "year": 1997, "language": "hindi", "tags": ["romantic"]},
    ]

    print("Queries:", generate_candidate_queries(seed))
    ranked = rank_candidates(seed, candidates, top_k=5)
    for t in ranked:
        print(f"{t['_similarity_score']:.3f}  {t['title']} ({t['year']})")

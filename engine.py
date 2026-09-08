from jio_client import fetch_search

BLACKLIST_WORDS = {
    "aarti", "bhajan", "chalisa", "mantra", "katha", "devotional", 
    "hanuman", "krishna", "ram", "shiv", "ganesh", "stuti", "amritwani"
}

def is_vibe_polluted(title: str) -> bool:
    low = title.lower()
    return any(word in low for word in BLACKLIST_WORDS)

def calculate_vibe_score(seed: dict, candidate: dict) -> float:
    score = 0.0
    
    # 1. Year / Era Closeness (Max 50 points)
    if seed.get("year") and candidate.get("year"):
        year_diff = abs(seed["year"] - candidate["year"])
        if year_diff == 0:
            score += 50
        elif year_diff <= 3:
            score += 40
        elif year_diff <= 7:
            score += 20
        else:
            score -= 30  # Penalty for huge decade gap
            
    # 2. Artist Overlap (Max 30 points)
    seed_artists = set(a.strip().lower() for a in seed.get("artist", "").split(","))
    cand_artists = set(a.strip().lower() for a in candidate.get("artist", "").split(","))
    if seed_artists & cand_artists:
        score += 30

    # 3. Language Match (Max 20 points)
    if seed.get("language") == candidate.get("language"):
        score += 20
        
    return score

def generate_vibe_queue(seed_song: dict, page: int = 1) -> list:
    """Generates continuous pure recommendations matching the seed's exact vibe."""
    candidates = []
    
    # Candidate Source 1: Query by era and primary singer
    primary_artist = seed_song.get("artist", "").split(",")[0].split("/")[0].strip()
    year = seed_song.get("year")
    
    if year and 1985 <= year <= 2005:
        era_str = "90s" if year < 2000 else "2000s"
        query = f"{primary_artist} {era_str} romantic hits"
    else:
        query = f"{primary_artist} top songs"

    batch = fetch_search(query=query, page=page, count=25)
    candidates.extend(batch)

    # Filtering & Scoring Pipeline
    valid_candidates = []
    seen_ids = {seed_song.get("id")}

    for cand in candidates:
        if cand["id"] in seen_ids or is_vibe_polluted(cand["title"]):
            continue
            
        # Strict era check for 90s/Golden Era seeds
        if year and 1990 <= year <= 1999:
            if cand["year"] and (cand["year"] < 1986 or cand["year"] > 2003):
                continue

        score = calculate_vibe_score(seed_song, cand)
        valid_candidates.append((score, cand))
        seen_ids.add(cand["id"])

    # Rank candidates by descending similarity score
    valid_candidates.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in valid_candidates]

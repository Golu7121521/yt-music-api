"""
schemas.py
Pydantic models for request validation and response documentation.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SeedTrack(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = ""
    year: Optional[int] = None
    language: Optional[str] = ""
    image: Optional[str] = ""
    stream_url: Optional[str] = Field(default="", alias="streamUrl")

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
    }


class RecommendationRequest(BaseModel):
    seed_track: SeedTrack
    exclude_ids: List[str] = Field(default_factory=list)
    top_k: int = 15

    model_config = {
        "populate_by_name": True,
    }


class SongOut(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = ""
    year: Optional[int] = None
    language: Optional[str] = ""
    image: Optional[str] = ""
    stream_url: Optional[str] = ""
    duration: Optional[int] = None
    similarity_score: Optional[float] = None

    model_config = {"extra": "allow"}

from dataclasses import dataclass
from typing import Optional


@dataclass
class PruneIntent:
    action: str
    artist_name: str
    album_name: str
    album_mbid: Optional[str] = None
    artist_mbid: Optional[str] = None
    rated_tracks: int = 0
    bad_tracks: int = 0
    total_tracks_seen: int = 0
    bad_ratio: float = 0.0
    reason: Optional[str] = None
    match_method: Optional[str] = None
    lidarr_album_id: Optional[int] = None
    lidarr_artist_id: Optional[int] = None
    has_files: Optional[bool] = None
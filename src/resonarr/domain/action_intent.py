# src/resonarr/domain/action_intent.py

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ActionIntent:
    action_type: str  # e.g. "ACQUIRE_ARTIST"
    artist_mbid: str

    artist_name: Optional[str] = None
    target_album_id: Optional[int] = None
    target_album_title: Optional[str] = None

    reason: str = ""
    score: Optional[int] = None

    metadata: dict = field(default_factory=dict)

    dry_run: bool = False
from pydantic import BaseModel


class DashboardCardModel(BaseModel):
    kind: str
    source: str
    status: str
    live: bool
    historical: bool
    artist_name: str | None = None
    artist_mbid: str | None = None
    album_title: str | None = None
    album_id: int | str | None = None
    score: float | None = None
    reason: str | None = None
    event_ts: int | None = None

    seed_count: int | None = None
    seen_count: int | None = None
    source_seeds: list[str] | None = None
    in_recommendation_backoff: bool | None = None
    is_promotable: bool | None = None

    lastfm_playcount: int | None = None
    partial_present: bool | None = None
    eligible_album_count: int | None = None
    fully_owned: bool | None = None
    in_cooldown: bool | None = None
    is_suppressed: bool | None = None

    suppressed_ts: int | None = None

    rated_tracks: int | None = None
    bad_tracks: int | None = None
    total_tracks_seen: int | None = None
    match_method: str | None = None
    matched: bool | None = None
    lidarr_has_files: bool | None = None


class ExtendSummaryModel(BaseModel):
    total_candidates: int
    starter_album_recommendation: int
    starter_album_approved: int
    starter_album_rejected: int
    starter_album_exhausted: int
    recommended: int
    new: int
    promotable_count: int
    review_queue_count: int


class DeepenSummaryModel(BaseModel):
    candidate_count: int
    review_queue_count: int
    partial_present_count: int
    suppressed_count: int
    cooldown_count: int
    recommendation_backoff_count: int


class PruneSummaryModel(BaseModel):
    live_candidate_count: int
    matched_count: int
    fallback_eligible_count: int
    strictly_unmatched_count: int
    history_count: int
    prune_recommendation_count: int
    prune_approved_count: int
    prune_executed_count: int
    prune_rejected_count: int
    reviewable_count: int


class DashboardHomeSummaryModel(BaseModel):
    extend: ExtendSummaryModel
    deepen: DeepenSummaryModel
    prune: PruneSummaryModel
    suppressed_artist_count: int


class DashboardSectionModel(BaseModel):
    status: str
    count: int
    items: list[DashboardCardModel]


class DashboardSectionsModel(BaseModel):
    extend_review_queue: DashboardSectionModel
    extend_promotable: DashboardSectionModel
    deepen_candidates: DashboardSectionModel
    deepen_review_queue: DashboardSectionModel
    suppressed_artists: DashboardSectionModel
    prune_review_queue: DashboardSectionModel


class DashboardHighlightsModel(BaseModel):
    recent_reviewable: list[DashboardCardModel]
    top_promotable: list[DashboardCardModel]
    top_deepen_candidates: list[DashboardCardModel]
    top_prune_candidates: list[DashboardCardModel]


class DashboardHomeResponseModel(BaseModel):
    status: str
    read_path: str
    snapshot_updated_ts: int | None = None
    snapshot_age_seconds: int | None = None
    home_summary: DashboardHomeSummaryModel
    sections: DashboardSectionsModel
    highlights: DashboardHighlightsModel

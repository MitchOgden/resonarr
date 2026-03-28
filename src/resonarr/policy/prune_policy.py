from resonarr.config.settings import (
    PRUNE_TRACK_BAD_MAX_RATING,
    PRUNE_MIN_TRACKS_RATED,
    PRUNE_ALBUM_BAD_RATIO,
    PRUNE_UNRATED_TRACK_STRATEGY,
    PRUNE_ALLOW_SMALL_ALBUM_FULL_REJECT,
)
from resonarr.domain.prune_intent import PruneIntent


class PrunePolicy:
    def score_album(self, album_signal):
        rated_tracks = album_signal["rated_tracks"]
        bad_tracks = album_signal["bad_tracks"]
        total_tracks_seen = album_signal["total_tracks_seen"]

        denominator = rated_tracks
        if PRUNE_UNRATED_TRACK_STRATEGY == "neutral":
            denominator = total_tracks_seen if total_tracks_seen > 0 else rated_tracks

        bad_ratio = 0.0
        if denominator > 0:
            bad_ratio = bad_tracks / denominator

        eligible = rated_tracks >= PRUNE_MIN_TRACKS_RATED

        should_prune = False
        reason = None

        if eligible:
            if bad_ratio >= PRUNE_ALBUM_BAD_RATIO:
                should_prune = True
                reason = (
                    f"bad ratio {bad_ratio:.2f} >= prune threshold {PRUNE_ALBUM_BAD_RATIO:.2f} "
                    f"with {rated_tracks} rated tracks"
                )
        else:
            if (
                PRUNE_ALLOW_SMALL_ALBUM_FULL_REJECT
                and total_tracks_seen > 0
                and total_tracks_seen <= PRUNE_MIN_TRACKS_RATED
                and rated_tracks >= 1
                and bad_tracks == rated_tracks
            ):
                should_prune = True
                reason = (
                    f"small album full reject: {bad_tracks}/{rated_tracks} rated tracks "
                    f"at or below {PRUNE_TRACK_BAD_MAX_RATING} on album with "
                    f"{total_tracks_seen} total tracks"
                )

        if not should_prune:
            return None

        return PruneIntent(
            action="RECOMMEND_PRUNE_ALBUM",
            artist_name=album_signal["artist_name"],
            album_name=album_signal["album_name"],
            album_mbid=album_signal.get("album_mbid"),
            artist_mbid=album_signal.get("artist_mbid"),
            rated_tracks=rated_tracks,
            bad_tracks=bad_tracks,
            total_tracks_seen=total_tracks_seen,
            bad_ratio=bad_ratio,
            reason=reason,
        )
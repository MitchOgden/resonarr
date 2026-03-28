from resonarr.config.settings import (
    PRUNE_MATCH_MODE,
    PRUNE_ALLOW_NAME_FALLBACK,
    PRUNE_MAX_CANDIDATES_PER_RUN,
)
from resonarr.execution.lidarr.client import LidarrClient
from resonarr.execution.lidarr.album_matching import (
    build_lidarr_album_indexes,
    match_album_to_lidarr,
)
from resonarr.policy.prune_policy import PrunePolicy
from resonarr.signals.plex.prune_extractor import PlexPruneExtractor


class PruneService:
    def __init__(self, extractor=None, policy=None, lidarr_client=None):
        self.extractor = extractor or PlexPruneExtractor()
        self.policy = policy or PrunePolicy()
        self.lidarr = lidarr_client or LidarrClient()

    def _fetch_lidarr_albums(self):
        resp = self.lidarr.get("/api/v1/album")
        resp.raise_for_status()
        return resp.json()

    def _index_lidarr_albums(self, albums):
        return build_lidarr_album_indexes(albums)

    def _match_album(self, prune_signal, by_mbid, by_name):
        return match_album_to_lidarr(
            prune_signal=prune_signal,
            lidarr_album_by_mbid=by_mbid,
            lidarr_album_by_name=by_name,
            client=self.lidarr,
            match_mode=PRUNE_MATCH_MODE,
            allow_name_fallback=PRUNE_ALLOW_NAME_FALLBACK,
        )

    def list_prune_candidates(self, limit=None):
        if limit is None:
            limit = PRUNE_MAX_CANDIDATES_PER_RUN

        album_signals = self.extractor.extract_album_signals()
        lidarr_albums = self._fetch_lidarr_albums()
        by_mbid, by_name = self._index_lidarr_albums(lidarr_albums)

        items = []

        for signal in album_signals:
            intent = self.policy.score_album(signal)
            if not intent:
                continue

            lidarr_album, match_method, diagnostics = self._match_album(
                signal,
                by_mbid,
                by_name,
            )

            item = {
                "artist_name": intent.artist_name,
                "artist_mbid": intent.artist_mbid,
                "album_name": intent.album_name,
                "album_mbid": intent.album_mbid,
                "rated_tracks": intent.rated_tracks,
                "bad_tracks": intent.bad_tracks,
                "total_tracks_seen": intent.total_tracks_seen,
                "bad_ratio": intent.bad_ratio,
                "reason": intent.reason,
                "match_method": match_method,
                "lidarr_album_id": None,
                "lidarr_artist_id": None,
                "lidarr_has_files": None,
                "matched": False,
                "action": intent.action,
                "has_album_mbid": diagnostics.get("has_album_mbid"),
                "mbid_match_found": diagnostics.get("mbid_match_found"),
                "name_match_found": diagnostics.get("name_match_found"),
                "name_match_available_but_disabled": diagnostics.get("name_match_available_but_disabled"),
                "name_match_type": diagnostics.get("name_match_type"),
                "name_candidate_count": diagnostics.get("name_candidate_count"),
                "verification_reason": diagnostics.get("verification_reason"),
                "verification_failures": diagnostics.get("verification_failures", []),
                "diagnostic_name_match_artist": diagnostics.get("diagnostic_name_match_artist"),
                "diagnostic_name_match_album": diagnostics.get("diagnostic_name_match_album"),
            }

            if lidarr_album:
                artist = lidarr_album.get("artist") or {}
                item["lidarr_album_id"] = lidarr_album.get("id")
                item["lidarr_artist_id"] = artist.get("id")
                item["lidarr_has_files"] = bool(lidarr_album.get("statistics", {}).get("trackFileCount", 0))
                item["matched"] = True

            items.append(item)

        items.sort(
            key=lambda x: (
                not x["matched"],
                -x["bad_ratio"],
                -x["rated_tracks"],
                x["artist_name"].lower(),
                x["album_name"].lower(),
            )
        )

        items = items[:limit]

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def get_prune_summary(self, limit=None):
        result = self.list_prune_candidates(limit=limit)
        items = result["items"]

        return {
            "status": "success",
            "candidate_count": len(items),
            "matched_count": sum(1 for item in items if item["matched"]),
            "unmatched_count": sum(1 for item in items if not item["matched"]),
            "items": items,
        }
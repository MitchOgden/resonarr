from resonarr.config.settings import (
    PRUNE_MATCH_MODE,
    PRUNE_ALLOW_NAME_FALLBACK,
    PRUNE_MAX_CANDIDATES_PER_RUN,
)
from resonarr.execution.lidarr.client import LidarrClient
from resonarr.policy.prune_policy import PrunePolicy
from resonarr.signals.plex.prune_extractor import PlexPruneExtractor


class PruneService:
    def __init__(self, extractor=None, policy=None, lidarr_client=None):
        self.extractor = extractor or PlexPruneExtractor()
        self.policy = policy or PrunePolicy()
        self.lidarr = lidarr_client or LidarrClient()

    def _normalize(self, value):
        return (
            (value or "")
            .lower()
            .replace("’", "'")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
        )

    def _fetch_lidarr_albums(self):
        resp = self.lidarr.get("/api/v1/album")
        resp.raise_for_status()
        return resp.json()

    def _index_lidarr_albums(self, albums):
        by_mbid = {}
        by_name = {}

        for album in albums:
            foreign_album_id = album.get("foreignAlbumId")
            if foreign_album_id:
                by_mbid[foreign_album_id] = album

            artist = album.get("artist") or {}
            artist_name = artist.get("artistName") or ""
            album_name = album.get("title") or ""

            key = (self._normalize(artist_name), self._normalize(album_name))
            by_name[key] = album

        return by_mbid, by_name

    def _match_album(self, prune_signal, by_mbid, by_name):
        album_mbid = prune_signal.get("album_mbid")
        artist_name = prune_signal.get("artist_name")
        album_name = prune_signal.get("album_name")

        if PRUNE_MATCH_MODE == "mbid" and album_mbid:
            album = by_mbid.get(album_mbid)
            if album:
                return album, "mbid"

        if PRUNE_ALLOW_NAME_FALLBACK:
            key = (self._normalize(artist_name), self._normalize(album_name))
            album = by_name.get(key)
            if album:
                return album, "name"

        return None, "unmatched"

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

            lidarr_album, match_method = self._match_album(signal, by_mbid, by_name)

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
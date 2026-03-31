import time

from resonarr.config.settings import PRUNE_TRACK_BAD_MAX_RATING
from resonarr.signals.plex.client import PlexClient


class PlexPruneExtractor:
    def __init__(self, plex_client=None):
        self.plex = plex_client or PlexClient()

    def _extract_mbids(self, item, tracks=None):
        import re

        album_mbids = []
        artist_mbid = None

        def add_candidate(value):
            if not value:
                return
            value = str(value).strip()
            if value and value not in album_mbids:
                album_mbids.append(value)

        def extract_candidates(raw_value):
            if not raw_value:
                return []

            raw_value = str(raw_value).strip()
            lowered = raw_value.lower()

            if "musicbrainz" not in lowered and "mbid" not in lowered:
                return []

            parts = re.split(r"[:/?#=&]", raw_value)
            candidates = []

            for part in parts:
                token = str(part).strip()
                if not token:
                    continue

                if re.fullmatch(r"[0-9a-fA-F-]{36}", token):
                    candidates.append(token)

            return candidates

        guid_strings = []

        for g in item.get("Guid") or []:
            guid = g.get("id")
            if guid:
                guid_strings.append(str(guid))

        direct_guid = item.get("guid")
        if direct_guid:
            guid_strings.append(str(direct_guid))

        for raw in guid_strings:
            for candidate in extract_candidates(raw):
                add_candidate(candidate)

        # Also harvest MBID-like identifiers from tracks, because Plex may expose
        # useful IDs there even when the album-level GUID chosen here is not the
        # one Lidarr uses directly.
        for track in tracks or []:
            for g in track.get("Guid") or []:
                guid = g.get("id")
                if not guid:
                    continue
                for candidate in extract_candidates(guid):
                    add_candidate(candidate)

        parent_guids = item.get("parentGuid") or []
        if isinstance(parent_guids, str):
            parent_guids = [parent_guids]

        for raw in parent_guids:
            for candidate in extract_candidates(raw):
                artist_mbid = candidate
                break
            if artist_mbid:
                break

        primary_album_mbid = album_mbids[0] if album_mbids else None
        return primary_album_mbid, artist_mbid, album_mbids

    def _track_is_bad(self, track):
        rating = track.get("userRating")
        if rating is None:
            return False
        return rating <= PRUNE_TRACK_BAD_MAX_RATING

    def _log_phase_elapsed(self, label, started_at):
        elapsed = time.perf_counter() - started_at
        print(f"[PERF][plex_prune] {label}: {elapsed:.2f}s")

    def extract_album_signals(self):
        total_started_at = time.perf_counter()

        phase_started_at = time.perf_counter()
        artists = self.plex.get_artists()
        self._log_phase_elapsed("fetch_artists", phase_started_at)

        results = []
        results_append = results.append

        total_tracks_considered = 0
        album_buckets_created = 0
        get_albums_calls = 0
        get_album_tracks_calls = 0

        get_albums = self.plex.get_albums
        get_album_tracks = self.plex.get_album_tracks
        extract_mbids = self._extract_mbids
        bad_max_rating = PRUNE_TRACK_BAD_MAX_RATING

        phase_started_at = time.perf_counter()
        for artist in artists:
            artist_get = artist.get
            artist_name = artist_get("title")
            artist_rating_key = artist_get("ratingKey")

            if not artist_rating_key or not artist_name:
                continue

            get_albums_calls += 1
            albums = get_albums(artist_rating_key)

            for album in albums:
                album_get = album.get
                album_name = album_get("title")
                album_rating_key = album_get("ratingKey")

                if not album_name or not album_rating_key:
                    continue

                get_album_tracks_calls += 1
                tracks = get_album_tracks(album_rating_key)
                album_mbid, artist_mbid, album_mbids = extract_mbids(album, tracks=tracks)

                rated_tracks = 0
                bad_tracks = 0
                total_tracks_seen = len(tracks)

                for track in tracks:
                    rating = track.get("userRating")
                    if rating is None:
                        continue

                    rated_tracks += 1
                    if rating <= bad_max_rating:
                        bad_tracks += 1

                total_tracks_considered += total_tracks_seen
                album_buckets_created += 1
                results_append({
                    "artist_name": artist_name,
                    "album_name": album_name,
                    "album_rating_key": album_rating_key,
                    "album_mbid": album_mbid,
                    "album_mbids": album_mbids,
                    "artist_mbid": artist_mbid,
                    "rated_tracks": rated_tracks,
                    "bad_tracks": bad_tracks,
                    "total_tracks_seen": total_tracks_seen,
                })
        self._log_phase_elapsed("track_album_iteration", phase_started_at)

        phase_started_at = time.perf_counter()
        self._log_phase_elapsed("aggregation_grouping", phase_started_at)

        phase_started_at = time.perf_counter()
        print(
            f"[PERF][plex_prune] counts: source_tracks={total_tracks_considered} "
            f"album_buckets={album_buckets_created} returned_album_signals={len(results)} "
            f"get_albums_calls={get_albums_calls} get_album_tracks_calls={get_album_tracks_calls}"
        )
        self._log_phase_elapsed("final_shape_return", phase_started_at)

        if hasattr(self.plex, "flush_caches"):
            self.plex.flush_caches()

        self._log_phase_elapsed("total_extract_album_signals", total_started_at)

        return results

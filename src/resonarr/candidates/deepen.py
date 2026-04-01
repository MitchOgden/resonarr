import time

from resonarr.signals.lastfm.client import LastfmClient
from resonarr.execution.lidarr.client import LidarrClient
from resonarr.state.memory_store import MemoryStore
from resonarr.config.settings import (
    DEEPEN_LASTFM_PERIOD,
    DEEPEN_MAX_CANDIDATES,
    DEEPEN_CANDIDATE_SCAN_LIMIT,
    DEEPEN_MIN_LASTFM_PLAYS,
    ARTIST_COOLDOWN_HOURS,
    RECOMMENDATION_BACKOFF_HOURS,
)


class DeepenCandidateSource:
    def __init__(self):
        self.lastfm = LastfmClient()
        self.lidarr = LidarrClient()
        self.memory = MemoryStore()
        self._perf = {}

    def _reset_perf(self):
        self._perf = {
            "get_lidarr_artists_calls": 0,
            "get_albums_calls": 0,
            "get_tracks_calls": 0,
            "classify_artist_calls": 0,
            "lastfm_top_artists_seen": 0,
            "playcount_filtered_count": 0,
            "missing_in_lidarr_count": 0,
            "candidates_built_count": 0,
            "artists_with_partial_present": 0,
            "artists_fully_owned": 0,
            "artists_with_eligible_albums": 0,
            "albums_fetched_total": 0,
            "albums_total_raw": 0,
            "albums_kept_after_filters": 0,
            "album_stats_fast_path_count": 0,
            "album_stats_fully_owned_fast_path_count": 0,
            "album_stats_zero_file_fast_path_count": 0,
            "album_track_fallback_count": 0,
            "albums_missing_or_invalid_stats_count": 0,
            "fully_owned_album_skips": 0,
            "partial_album_hits": 0,
            "eligible_album_hits": 0,
            "tracks_examined_total": 0,
            "lidarr_artist_fetch_seconds": 0.0,
            "lastfm_fetch_seconds": 0.0,
            "classify_artist_seconds": 0.0,
            "sort_seconds": 0.0,
            "candidate_loop_seconds": 0.0,
        }

    def _inc_perf(self, key, amount=1):
        self._perf[key] = self._perf.get(key, 0) + amount

    def _add_perf_seconds(self, key, elapsed):
        self._perf[key] = self._perf.get(key, 0.0) + elapsed

    def _log_phase_elapsed(self, label, started_at):
        elapsed = time.perf_counter() - started_at
        print(f"[PERF][deepen] {label}: {elapsed:.2f}s")

    def _print_perf_summary(self, returned_candidates):
        print(
            f"[PERF][deepen] counts: "
            f"get_lidarr_artists_calls={self._perf['get_lidarr_artists_calls']} "
            f"get_albums_calls={self._perf['get_albums_calls']} "
            f"get_tracks_calls={self._perf['get_tracks_calls']} "
            f"classify_artist_calls={self._perf['classify_artist_calls']} "
            f"lastfm_top_artists_seen={self._perf['lastfm_top_artists_seen']} "
            f"playcount_filtered_count={self._perf['playcount_filtered_count']} "
            f"missing_in_lidarr_count={self._perf['missing_in_lidarr_count']} "
            f"candidates_built_count={self._perf['candidates_built_count']} "
            f"artists_with_partial_present={self._perf['artists_with_partial_present']} "
            f"artists_fully_owned={self._perf['artists_fully_owned']} "
            f"artists_with_eligible_albums={self._perf['artists_with_eligible_albums']} "
            f"albums_fetched_total={self._perf['albums_fetched_total']} "
            f"albums_total_raw={self._perf['albums_total_raw']} "
            f"albums_kept_after_filters={self._perf['albums_kept_after_filters']} "
            f"album_stats_fast_path_count={self._perf['album_stats_fast_path_count']} "
            f"album_stats_fully_owned_fast_path_count={self._perf['album_stats_fully_owned_fast_path_count']} "
            f"album_stats_zero_file_fast_path_count={self._perf['album_stats_zero_file_fast_path_count']} "
            f"album_track_fallback_count={self._perf['album_track_fallback_count']} "
            f"albums_missing_or_invalid_stats_count={self._perf['albums_missing_or_invalid_stats_count']} "
            f"fully_owned_album_skips={self._perf['fully_owned_album_skips']} "
            f"partial_album_hits={self._perf['partial_album_hits']} "
            f"eligible_album_hits={self._perf['eligible_album_hits']} "
            f"tracks_examined_total={self._perf['tracks_examined_total']} "
            f"returned_candidates={returned_candidates}"
        )
        print(
            f"[PERF][deepen] seconds: "
            f"lidarr_artist_fetch_seconds={self._perf['lidarr_artist_fetch_seconds']:.2f}s "
            f"lastfm_fetch_seconds={self._perf['lastfm_fetch_seconds']:.2f}s "
            f"classify_artist_seconds={self._perf['classify_artist_seconds']:.2f}s "
            f"candidate_loop_seconds={self._perf['candidate_loop_seconds']:.2f}s "
            f"sort_seconds={self._perf['sort_seconds']:.2f}s"
        )

    def _normalize(self, name):
        return (name or "").lower().strip()

    def _get_lidarr_artists(self):
        self._inc_perf("get_lidarr_artists_calls")

        started_at = time.perf_counter()
        resp = self.lidarr.get("/api/v1/artist")
        artists = resp.json()
        self._add_perf_seconds("lidarr_artist_fetch_seconds", time.perf_counter() - started_at)

        by_name = {}
        for artist in artists:
            artist_name = artist.get("artistName")
            if artist_name:
                by_name[self._normalize(artist_name)] = artist

        return artists, by_name

    def _get_albums(self, artist_id):
        self._inc_perf("get_albums_calls")
        resp = self.lidarr.get(f"/api/v1/album?artistId={artist_id}")
        albums = resp.json()
        self._inc_perf("albums_fetched_total", len(albums))
        return albums

    def _get_tracks(self, album_id):
        self._inc_perf("get_tracks_calls")
        resp = self.lidarr.get(f"/api/v1/track?albumId={album_id}")
        tracks = resp.json()
        self._inc_perf("tracks_examined_total", len(tracks))
        return tracks
    
    def _get_cooldown_state_from_artist_state(self, artist_state):
        last_action_ts = artist_state.get("last_action_ts")

        if not last_action_ts:
            return {
                "in_cooldown": False,
                "cooldown_remaining_seconds": 0,
            }

        cooldown_seconds = ARTIST_COOLDOWN_HOURS * 3600
        elapsed = time.time() - last_action_ts

        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return {
                "in_cooldown": True,
                "cooldown_remaining_seconds": remaining,
            }

        return {
            "in_cooldown": False,
            "cooldown_remaining_seconds": 0,
        }

    def _get_recommendation_backoff_state_from_artist_state(self, artist_state):
        last_recommendation_ts = artist_state.get("last_recommendation_ts")

        if not last_recommendation_ts:
            return {
                "in_recommendation_backoff": False,
            }

        backoff_seconds = RECOMMENDATION_BACKOFF_HOURS * 3600
        elapsed = time.time() - last_recommendation_ts

        return {
            "in_recommendation_backoff": elapsed < backoff_seconds,
        }

    def _classify_album_ownership_from_album_stats(self, album):
        return {
            "can_skip_track_fetch": False,
            "fully_owned": False,
            "partial_present": False,
            "track_count": None,
            "track_file_count": None,
            "fast_path_reason": None,
        }

    def _album_counts_as_partial_present(self, total_tracks, has_file_count):
        if total_tracks <= 0:
            return False

        if has_file_count >= total_tracks:
            return False

        return has_file_count >= 2

    def _classify_artist(self, lidarr_artist):
        self._inc_perf("classify_artist_calls")
        started_at = time.perf_counter()

        artist_id = lidarr_artist.get("id")
        albums = self._get_albums(artist_id)

        partial_present = False
        eligible_album_count = 0
        fully_owned_album_count = 0
        total_album_count = 0

        self._inc_perf("albums_total_raw", len(albums))

        for album in albums:
            if album.get("albumType") != "Album":
                continue

            title = (album.get("title") or "").lower()
            secondary_types = [t.lower() for t in (album.get("secondaryTypes") or [])]

            if "playlist:" in title:
                continue
            if "compilation" in secondary_types:
                continue
            if "collection" in title or "box" in title:
                continue

            total_album_count += 1
            self._inc_perf("albums_kept_after_filters")

            self._inc_perf("album_track_fallback_count")

            tracks = self._get_tracks(album.get("id"))
            total_tracks = len(tracks)
            has_file_count = sum(1 for t in tracks if t.get("hasFile"))

            if total_tracks > 0 and has_file_count == total_tracks:
                fully_owned_album_count += 1
                self._inc_perf("fully_owned_album_skips")
                continue

            if self._album_counts_as_partial_present(total_tracks, has_file_count):
                partial_present = True
                self._inc_perf("partial_album_hits")

            if not album.get("monitored", False):
                eligible_album_count += 1
                self._inc_perf("eligible_album_hits")

        fully_owned = (
            total_album_count > 0 and
            fully_owned_album_count == total_album_count and
            not partial_present
        )

        if partial_present:
            self._inc_perf("artists_with_partial_present")
        if fully_owned:
            self._inc_perf("artists_fully_owned")
        if eligible_album_count > 0:
            self._inc_perf("artists_with_eligible_albums")

        self._add_perf_seconds("classify_artist_seconds", time.perf_counter() - started_at)

        return {
            "partial_present": partial_present,
            "eligible_album_count": eligible_album_count,
            "fully_owned": fully_owned,
            "total_album_count": total_album_count,
            "fully_owned_album_count": fully_owned_album_count,
        }

    def get_candidates(self):
        total_started_at = time.perf_counter()
        self._reset_perf()

        phase_started_at = time.perf_counter()
        _, lidarr_by_name = self._get_lidarr_artists()
        self._log_phase_elapsed("fetch_lidarr_artists", phase_started_at)

        phase_started_at = time.perf_counter()
        data = self.lastfm.get_top_artists(period=DEEPEN_LASTFM_PERIOD)
        top_artists = data.get("topartists", {}).get("artist", [])
        self._add_perf_seconds("lastfm_fetch_seconds", time.perf_counter() - phase_started_at)
        self._log_phase_elapsed("fetch_lastfm_top_artists", phase_started_at)

        candidates = []

        phase_started_at = time.perf_counter()
        for idx, artist in enumerate(top_artists, start=1):
            self._inc_perf("lastfm_top_artists_seen")

            name = artist.get("name")
            playcount = int(artist.get("playcount", 0))

            if playcount < DEEPEN_MIN_LASTFM_PLAYS:
                self._inc_perf("playcount_filtered_count")
                continue

            lidarr_artist = lidarr_by_name.get(self._normalize(name))
            if not lidarr_artist:
                self._inc_perf("missing_in_lidarr_count")
                continue

            mbid = lidarr_artist.get("foreignArtistId")
            classification = self._classify_artist(lidarr_artist)

            artist_state = self.memory.get_artist_state(mbid)
            cooldown = self._get_cooldown_state_from_artist_state(artist_state)
            recommendation_backoff = self._get_recommendation_backoff_state_from_artist_state(artist_state)

            is_suppressed = artist_state.get("suppressed", False)
            suppression_reason = artist_state.get("suppression_reason")

            candidates.append({
                "rank": idx,
                "artist_name": lidarr_artist.get("artistName"),
                "mbid": mbid,
                "lastfm_playcount": playcount,
                "lidarr_artist_id": lidarr_artist.get("id"),
                "partial_present": classification["partial_present"],
                "eligible_album_count": classification["eligible_album_count"],
                "fully_owned": classification["fully_owned"],
                "total_album_count": classification["total_album_count"],
                "fully_owned_album_count": classification["fully_owned_album_count"],
                "in_cooldown": cooldown["in_cooldown"],
                "cooldown_remaining_seconds": cooldown["cooldown_remaining_seconds"],
                "in_recommendation_backoff": recommendation_backoff["in_recommendation_backoff"],
                "is_suppressed": is_suppressed,
                "suppression_reason": suppression_reason,
            })
            self._inc_perf("candidates_built_count")
        self._add_perf_seconds("candidate_loop_seconds", time.perf_counter() - phase_started_at)
        self._log_phase_elapsed("candidate_scan_loop", phase_started_at)

        phase_started_at = time.perf_counter()
        candidates.sort(
            key=lambda x: (
                not x["partial_present"],
                x["is_suppressed"],
                x["in_cooldown"],
                x["in_recommendation_backoff"],
                x["fully_owned"],
                -x["eligible_album_count"],
                -x["lastfm_playcount"],
                x["rank"],
            )
        )
        self._add_perf_seconds("sort_seconds", time.perf_counter() - phase_started_at)
        self._log_phase_elapsed("sort_candidates", phase_started_at)

        returned = candidates[:DEEPEN_CANDIDATE_SCAN_LIMIT]
        self._print_perf_summary(len(returned))
        self._log_phase_elapsed("total_get_candidates", total_started_at)

        return returned

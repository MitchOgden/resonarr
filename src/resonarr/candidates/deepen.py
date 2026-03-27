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
)


class DeepenCandidateSource:
    def __init__(self):
        self.lastfm = LastfmClient()
        self.lidarr = LidarrClient()
        self.memory = MemoryStore()

    def _normalize(self, name):
        return (name or "").lower().strip()

    def _get_lidarr_artists(self):
        resp = self.lidarr.get("/api/v1/artist")
        artists = resp.json()

        by_name = {}
        for artist in artists:
            artist_name = artist.get("artistName")
            if artist_name:
                by_name[self._normalize(artist_name)] = artist

        return artists, by_name

    def _get_albums(self, artist_id):
        resp = self.lidarr.get(f"/api/v1/album?artistId={artist_id}")
        return resp.json()

    def _get_tracks(self, album_id):
        resp = self.lidarr.get(f"/api/v1/track?albumId={album_id}")
        return resp.json()
    
    def _get_cooldown_state(self, mbid):
        artist_state = self.memory.get_artist_state(mbid)
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

    def _classify_artist(self, lidarr_artist):
        artist_id = lidarr_artist.get("id")
        albums = self._get_albums(artist_id)

        partial_present = False
        eligible_album_count = 0
        fully_owned_album_count = 0
        total_album_count = 0

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

            tracks = self._get_tracks(album.get("id"))
            total_tracks = len(tracks)
            has_file_count = sum(1 for t in tracks if t.get("hasFile"))

            if total_tracks > 0 and has_file_count == total_tracks:
                fully_owned_album_count += 1
                continue

            if has_file_count > 0:
                partial_present = True

            if not album.get("monitored", False):
                eligible_album_count += 1

        fully_owned = (
            total_album_count > 0 and
            fully_owned_album_count == total_album_count and
            not partial_present
        )

        return {
            "partial_present": partial_present,
            "eligible_album_count": eligible_album_count,
            "fully_owned": fully_owned,
            "total_album_count": total_album_count,
            "fully_owned_album_count": fully_owned_album_count,
        }

    def get_candidates(self):
        _, lidarr_by_name = self._get_lidarr_artists()

        data = self.lastfm.get_top_artists(period=DEEPEN_LASTFM_PERIOD)
        top_artists = data.get("topartists", {}).get("artist", [])

        candidates = []

        for idx, artist in enumerate(top_artists, start=1):
            name = artist.get("name")
            playcount = int(artist.get("playcount", 0))

            if playcount < DEEPEN_MIN_LASTFM_PLAYS:
                continue

            lidarr_artist = lidarr_by_name.get(self._normalize(name))
            if not lidarr_artist:
                continue

            mbid = lidarr_artist.get("foreignArtistId")
            classification = self._classify_artist(lidarr_artist)
            cooldown = self._get_cooldown_state(mbid)

            artist_state = self.memory.get_artist_state(mbid)
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
                "is_suppressed": is_suppressed,
                "suppression_reason": suppression_reason,
            })

        candidates.sort(
            key=lambda x: (
                not x["partial_present"],
                x["is_suppressed"],
                x["in_cooldown"],
                x["fully_owned"],
                -x["eligible_album_count"],
                -x["lastfm_playcount"],
                x["rank"],
            )
        )

        return candidates[:DEEPEN_CANDIDATE_SCAN_LIMIT]
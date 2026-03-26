from resonarr.signals.lastfm.client import LastfmClient
from resonarr.execution.lidarr.client import LidarrClient
from resonarr.config.settings import (
    DEEPEN_LASTFM_PERIOD,
    DEEPEN_MAX_CANDIDATES,
    DEEPEN_MIN_LASTFM_PLAYS,
)


class DeepenCandidateSource:
    def __init__(self):
        self.lastfm = LastfmClient()
        self.lidarr = LidarrClient()

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

            candidates.append({
                "rank": idx,
                "artist_name": lidarr_artist.get("artistName"),
                "mbid": lidarr_artist.get("foreignArtistId"),
                "lastfm_playcount": playcount,
                "lidarr_artist_id": lidarr_artist.get("id"),
            })

        candidates.sort(
            key=lambda x: (-x["lastfm_playcount"], x["rank"])
        )

        return candidates[:DEEPEN_MAX_CANDIDATES]
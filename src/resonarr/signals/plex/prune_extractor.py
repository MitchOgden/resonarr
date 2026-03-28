from resonarr.config.settings import PRUNE_TRACK_BAD_MAX_RATING
from resonarr.signals.plex.client import PlexClient


class PlexPruneExtractor:
    def __init__(self, plex_client=None):
        self.plex = plex_client or PlexClient()

    def _extract_mbids(self, item):
        album_mbid = None
        artist_mbid = None

        guids = item.get("Guid") or []

        for g in guids:
            guid = g.get("id")
            if not guid:
                continue

            if guid.startswith("mbid://"):
                value = guid.split("mbid://", 1)[1]
                if not album_mbid:
                    album_mbid = value
                continue

            if "musicbrainz" in guid:
                try:
                    value = guid.split("://", 1)[1].split("?", 1)[0]
                    if not album_mbid:
                        album_mbid = value
                except Exception:
                    pass

        parent_guids = item.get("parentGuid") or []
        if isinstance(parent_guids, str):
            parent_guids = [parent_guids]

        for guid in parent_guids:
            if not guid:
                continue

            if guid.startswith("mbid://"):
                artist_mbid = guid.split("mbid://", 1)[1]
                break

            if "musicbrainz" in guid:
                try:
                    artist_mbid = guid.split("://", 1)[1].split("?", 1)[0]
                    break
                except Exception:
                    pass

        return album_mbid, artist_mbid

    def _track_is_bad(self, track):
        rating = track.get("userRating")
        if rating is None:
            return False
        return rating <= PRUNE_TRACK_BAD_MAX_RATING

    def extract_album_signals(self):
        artists = self.plex.get_artists()
        results = []

        for artist in artists:
            artist_name = artist.get("title")
            artist_rating_key = artist.get("ratingKey")

            if not artist_rating_key or not artist_name:
                continue

            albums = self.plex.get_albums(artist_rating_key)

            for album in albums:
                album_name = album.get("title")
                album_rating_key = album.get("ratingKey")

                if not album_name or not album_rating_key:
                    continue

                tracks = self.plex.get_album_tracks(album_rating_key)
                album_mbid, artist_mbid = self._extract_mbids(album)

                rated_tracks = 0
                bad_tracks = 0
                total_tracks_seen = 0

                for track in tracks:
                    total_tracks_seen += 1
                    rating = track.get("userRating")

                    if rating is not None:
                        rated_tracks += 1
                        if self._track_is_bad(track):
                            bad_tracks += 1

                results.append({
                    "artist_name": artist_name,
                    "album_name": album_name,
                    "album_rating_key": album_rating_key,
                    "album_mbid": album_mbid,
                    "artist_mbid": artist_mbid,
                    "rated_tracks": rated_tracks,
                    "bad_tracks": bad_tracks,
                    "total_tracks_seen": total_tracks_seen,
                })

        return results
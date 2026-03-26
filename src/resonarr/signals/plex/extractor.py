from resonarr.signals.models import ArtistSignals

class PlexSignalExtractor:
    def __init__(self, plex_client):
        self.plex = plex_client

    def _normalize(self, name):
        return name.lower().strip()

    def _normalize_title(self, name):
        return (
            name.lower()
            .replace("’", "'")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
        )

    def _match_artist(self, artists, artist_name):
        target = self._normalize(artist_name)

        for artist in artists:
            plex_name = self._normalize(artist.get("title", ""))

            if target == plex_name or target in plex_name:
                return artist

        return None

    def _extract_mbid(self, album):
        guids = album.get("Guid") or []

        for g in guids:
            guid = g.get("id")

            if not guid:
                continue

            # --- CASE 1: mbid://<uuid> ---
            if guid.startswith("mbid://"):
                return guid.split("mbid://")[1]

            # --- CASE 2: musicbrainz agent format ---
            if "musicbrainz" in guid:
                try:
                    return guid.split("://")[1].split("?")[0]
                except Exception:
                    continue

        return None

    def extract_artist_signals(self, artist_name):
        artists = self.plex.get_artists()
        match = self._match_artist(artists, artist_name)

        albums = self.plex.get_albums(match.get("ratingKey"))

        owned_album_mbids = set()

        for album in albums:
            title = album.get("title")
            guids = album.get("Guid")

            mbid = self._extract_mbid(album)

            if mbid:
                owned_album_mbids.add(mbid)

        if not match:
            print(f"[DEBUG] Plex: artist not found: {artist_name}")
            return None

        rating = match.get("userRating")
        play_count = match.get("viewCount")

        print("[DEBUG] Plex signals:")
        print(f"  artist={match.get('title')}")
        print(f"  rating={rating}")
        print(f"  play_count={play_count}")

        return ArtistSignals(
            rating=rating,
            play_count=play_count,
            normalized_play_ratio=None,
            last_played=None,
            owned_albums=owned_album_mbids,
            source="plex_real"
        )
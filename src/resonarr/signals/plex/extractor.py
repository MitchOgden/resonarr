from resonarr.signals.models import ArtistSignals

class PlexSignalExtractor:
    def __init__(self, plex_client):
        self.plex = plex_client

    def _normalize(self, name):
        return name.lower().strip()

    def _match_artist(self, artists, artist_name):
        target = self._normalize(artist_name)

        for artist in artists:
            plex_name = self._normalize(artist.get("title", ""))

            if target == plex_name or target in plex_name:
                return artist

        return None

    def extract_artist_signals(self, artist_name):
        artists = self.plex.get_artists()
        match = self._match_artist(artists, artist_name)

        if not match:
            print(f"[DEBUG] Plex: artist not found: {artist_name}")
            return None

        rating = match.get("userRating")
        play_count = match.get("viewCount")

        print("[DEBUG] Plex artist raw:")
        print(f"  name={match.get('title')}")
        print(f"  rating={rating}")
        print(f"  play_count={play_count}")

        return ArtistSignals(
            rating=rating,
            play_count=play_count,
            normalized_play_ratio=None,  # not available yet
            last_played=None,            # not available yet
            source="plex_real"
        )
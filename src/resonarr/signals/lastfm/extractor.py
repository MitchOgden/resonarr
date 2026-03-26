from resonarr.signals.models import ArtistSignals


class LastfmSignalExtractor:
    def __init__(self, client):
        self.client = client

    def _normalize(self, name):
        return name.lower().strip()

    def extract_artist_signals(self, artist_name):
        data = self.client.get_top_artists()

        artists = data.get("topartists", {}).get("artist", [])

        target = self._normalize(artist_name)

        total_plays = 0
        match_plays = 0

        for artist in artists:
            name = self._normalize(artist.get("name", ""))
            playcount = int(artist.get("playcount", 0))

            total_plays += playcount

            if name == target:
                match_plays = playcount

        if total_plays == 0:
            return None

        ratio = match_plays / total_plays if match_plays else 0

        print("[DEBUG] Last.fm signals:")
        print(f"  artist={artist_name}")
        print(f"  play_count={match_plays}")
        print(f"  ratio={round(ratio, 3)}")

        return ArtistSignals(
            rating=None,
            play_count=match_plays,
            normalized_play_ratio=ratio,
            last_played=None,
            source="lastfm"
        )
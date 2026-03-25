class PlexSignalExtractor:
    def __init__(self, plex_client):
        self.plex = plex_client

    def extract_artist_signals(self, artist_name):
        artists = self.plex.get_artists()

        match = None

        def normalize(name):
            return name.lower().strip()


        target = normalize(artist_name)

        for a in artists:
            plex_name = normalize(a.get("title", ""))

            if target == plex_name or target in plex_name:
                match = a
                break

        if not match:
            print(f"[DEBUG] Plex: artist not found: {artist_name}")
            return None

        rating = match.get("userRating")
        play_count = match.get("viewCount")

        print("[DEBUG] Plex artist raw:")
        print(f"  name={match.get('title')}")
        print(f"  rating={rating}")
        print(f"  play_count={play_count}")

        # DO NOT influence system yet
        return {
            "rating": rating,
            "play_count": play_count,
            "source": "plex_real"
        }
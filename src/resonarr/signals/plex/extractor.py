class PlexSignalExtractor:
    def __init__(self, plex_client):
        self.plex = plex_client

    def extract_artist_signals(self, artist_name):
        # MVP: stub (safe)
        # Replace with real logic next step

        return {
            "affinity": None,
            "suppressed": False,
            "source": "plex_stub"
        }
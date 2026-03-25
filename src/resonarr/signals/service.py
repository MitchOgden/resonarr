from resonarr.signals.plex.client import PlexClient
from resonarr.signals.plex.extractor import PlexSignalExtractor


class SignalService:
    def __init__(self):
        self.plex = PlexClient()
        self.extractor = PlexSignalExtractor(self.plex)

    def get_artist_signals(self, artist_name):
        return self.extractor.extract_artist_signals(artist_name)
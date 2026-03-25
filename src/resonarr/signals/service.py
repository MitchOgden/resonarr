from resonarr.signals.plex.client import PlexClient
from resonarr.signals.plex.extractor import PlexSignalExtractor
from resonarr.signals.interpreter import SignalInterpreter


class SignalService:
    def __init__(self):
        self.plex = PlexClient()
        self.extractor = PlexSignalExtractor(self.plex)
        self.interpreter = SignalInterpreter()

    def apply_artist_signals(self, mbid, artist_name, memory):
        signals = self.extractor.extract_artist_signals(artist_name)

        if signals:
            self.interpreter.apply_artist_signals(mbid, signals, memory)

        return signals
from resonarr.signals.plex.client import PlexClient
from resonarr.signals.plex.extractor import PlexSignalExtractor
from resonarr.signals.lastfm.client import LastfmClient
from resonarr.signals.lastfm.extractor import LastfmSignalExtractor
from resonarr.signals.interpreter import SignalInterpreter


class SignalService:
    def __init__(self):
        self.lastfm = LastfmSignalExtractor(LastfmClient())
        self.extractor = PlexSignalExtractor(PlexClient())
        self.interpreter = SignalInterpreter()

    def apply_artist_signals(self, mbid, artist_name, memory):
        plex_signals = self.extractor.extract_artist_signals(artist_name)
        lastfm_signals = self.lastfm.extract_artist_signals(artist_name)

        signals = plex_signals or lastfm_signals

        if signals:
            print(f"[DEBUG] Normalized signals ({signals.source}): {signals.to_dict()}")
            self.interpreter.apply_artist_signals(mbid, signals, memory)

        return signals
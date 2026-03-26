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
        affinity = 1.0
        confidence = 0.0

        # --- PLEX ---
        if plex_signals and plex_signals.play_count:
            if plex_signals.play_count >= 50:
                affinity *= 2.5
            elif plex_signals.play_count >= 20:
                affinity *= 2.0
            elif plex_signals.play_count >= 5:
                affinity *= 1.5

            confidence += 0.6

        # --- LAST.FM ---
        if lastfm_signals and lastfm_signals.normalized_play_ratio:
            ratio = lastfm_signals.normalized_play_ratio

            if ratio >= 0.25:
                affinity *= 2.0
            elif ratio >= 0.10:
                affinity *= 1.5
            elif ratio > 0:
                affinity *= 1.2

            confidence += 0.4

        return {
            "affinity": affinity,
            "confidence": confidence,
            "sources": ["plex", "lastfm"]
        }
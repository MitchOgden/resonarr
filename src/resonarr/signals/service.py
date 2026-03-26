from resonarr.signals.plex.client import PlexClient
from resonarr.signals.plex.extractor import PlexSignalExtractor
from resonarr.signals.lastfm.client import LastfmClient
from resonarr.signals.lastfm.extractor import LastfmSignalExtractor
from resonarr.signals.models import ArtistSignals


class SignalService:
    def __init__(self):
        self.lastfm = LastfmSignalExtractor(LastfmClient())
        self.extractor = PlexSignalExtractor(PlexClient())

    def apply_artist_signals(self, mbid, artist_name, memory):
        plex_signals = self.extractor.extract_artist_signals(artist_name)
        lastfm_signals = self.lastfm.extract_artist_signals(artist_name)

        affinity = 1.0
        confidence = 0.0
        sources = []

        # --- PLEX ---
        if plex_signals and plex_signals.play_count:
            if plex_signals.play_count >= 50:
                affinity *= 2.5
            elif plex_signals.play_count >= 20:
                affinity *= 2.0
            elif plex_signals.play_count >= 5:
                affinity *= 1.5

            confidence += 0.6
            sources.append("plex")

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
            sources.append("lastfm")

        if sources:
            memory.boost_artist_affinity(
                mbid,
                multiplier=affinity,
                reason=f"signal_merge({','.join(sources)})"
            )

        owned_albums = plex_signals.owned_albums if plex_signals else set()

        print(
            f"[DEBUG] Merged signals: affinity={affinity} "
            f"confidence={confidence} sources={sources}"
        )

        return ArtistSignals(
            rating=plex_signals.rating if plex_signals else None,
            play_count=plex_signals.play_count if plex_signals else None,
            normalized_play_ratio=lastfm_signals.normalized_play_ratio if lastfm_signals else None,
            last_played=None,
            owned_albums=owned_albums,
            source="merged"
        )
from resonarr.signals.plex.client import PlexClient
from resonarr.signals.plex.extractor import PlexSignalExtractor
from resonarr.signals.lastfm.client import LastfmClient
from resonarr.signals.lastfm.extractor import LastfmSignalExtractor
from resonarr.signals.models import ArtistSignals
from resonarr.config.settings import (
    SIGNAL_PLEX_WEIGHT,
    SIGNAL_LASTFM_WEIGHT,
    SIGNAL_PLEX_PLAYS_HIGH,
    SIGNAL_PLEX_PLAYS_MEDIUM,
    SIGNAL_PLEX_PLAYS_LOW,
    SIGNAL_PLEX_MULTIPLIER_HIGH,
    SIGNAL_PLEX_MULTIPLIER_MEDIUM,
    SIGNAL_PLEX_MULTIPLIER_LOW,
    SIGNAL_LASTFM_RATIO_HIGH,
    SIGNAL_LASTFM_RATIO_MEDIUM,
    SIGNAL_LASTFM_RATIO_LOW,
    SIGNAL_LASTFM_MULTIPLIER_HIGH,
    SIGNAL_LASTFM_MULTIPLIER_MEDIUM,
    SIGNAL_LASTFM_MULTIPLIER_LOW,
)


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
            pc = plex_signals.play_count

            if pc >= SIGNAL_PLEX_PLAYS_HIGH:
                affinity *= SIGNAL_PLEX_MULTIPLIER_HIGH
            elif pc >= SIGNAL_PLEX_PLAYS_MEDIUM:
                affinity *= SIGNAL_PLEX_MULTIPLIER_MEDIUM
            elif pc >= SIGNAL_PLEX_PLAYS_LOW:
                affinity *= SIGNAL_PLEX_MULTIPLIER_LOW

            confidence += SIGNAL_PLEX_WEIGHT
            sources.append("plex")

        # --- LAST.FM ---
        if lastfm_signals and lastfm_signals.normalized_play_ratio is not None:
            ratio = lastfm_signals.normalized_play_ratio

            if ratio >= SIGNAL_LASTFM_RATIO_HIGH:
                affinity *= SIGNAL_LASTFM_MULTIPLIER_HIGH
            elif ratio >= SIGNAL_LASTFM_RATIO_MEDIUM:
                affinity *= SIGNAL_LASTFM_MULTIPLIER_MEDIUM
            elif ratio > SIGNAL_LASTFM_RATIO_LOW:
                affinity *= SIGNAL_LASTFM_MULTIPLIER_LOW

            confidence += SIGNAL_LASTFM_WEIGHT
            sources.append("lastfm")

        if sources:
            memory.boost_artist_affinity(
                mbid,
                multiplier=affinity,
                reason=f"signal_merge({','.join(sources)})"
            )

        owned_albums = plex_signals.owned_albums if plex_signals else set()

        print(
            f"[DEBUG] Merged signals: affinity={affinity:.2f} "
            f"confidence={confidence:.2f} sources={sources}"
        )

        return ArtistSignals(
            rating=plex_signals.rating if plex_signals else None,
            play_count=plex_signals.play_count if plex_signals else None,
            normalized_play_ratio=lastfm_signals.normalized_play_ratio if lastfm_signals else None,
            last_played=None,
            owned_albums=owned_albums,
            source="merged"
        )
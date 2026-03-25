class SignalInterpreter:
    def apply_artist_signals(self, mbid, signals, memory):
        if not signals:
            return

        print(f"[DEBUG] Signals: {signals}")

        # --- PLAY COUNT → AFFINITY ---
        play_count = signals.get("play_count")

        if play_count is not None:
            if play_count >= 50:
                multiplier = 2.5
                reason = "plex_high_playcount"
            elif play_count >= 20:
                multiplier = 2.0
                reason = "plex_medium_playcount"
            elif play_count >= 5:
                multiplier = 1.5
                reason = "plex_low_playcount"
            else:
                multiplier = None

            if multiplier:
                print(f"[DEBUG] Applying affinity from play_count={play_count} → {multiplier}")
                memory.boost_artist_affinity(
                    mbid,
                    multiplier=multiplier,
                    reason=reason
                )
class AlbumSelector:
    
    def _normalize_title(self, name):
        return (
            name.lower()
            .replace("’", "'")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
        )
    
    def select_best_album(self, albums, affinity, owned_albums=None):
        deepening = affinity > 1.0

        candidates = []

        owned_mbids = owned_albums or set()

        for a in albums:
            if a.get("albumType") != "Album":
                continue

            title = a.get("title")
            monitored = a.get("monitored", False)
            track_file_count = a.get("statistics", {}).get("trackFileCount", 0)
            lidarr_mbid = a.get("foreignAlbumId")

            # --- SKIP: owned in Plex (release-level MBID match) ---
            lidarr_releases = a.get("releases") or []
            track_file_count = a.get("statistics", {}).get("trackFileCount", 0)
            total_track_count = a.get("statistics", {}).get("trackCount", 0)

            is_owned_in_plex = False

            for release in lidarr_releases:
                release_mbid = release.get("foreignReleaseId")
                if release_mbid and release_mbid in owned_mbids:
                    is_owned_in_plex = True
                    break


            # --- OWNERSHIP CLASSIFICATION ---
            if is_owned_in_plex:
                if total_track_count > 0 and track_file_count >= total_track_count:
                    print(f"[DEBUG] Skipping fully owned album: {title}")
                    continue
                else:
                    print(f"[DEBUG] Partial album detected: {title} ({track_file_count}/{total_track_count})")
                    partial = True
            else:
                partial = False


            # --- SKIP: owned in Lidarr (files exist) ---
            track_file_count = a.get("statistics", {}).get("trackFileCount", 0)

            if track_file_count > 0:
                print(f"[DEBUG] Skipping owned album in Lidarr: {title} (trackFileCount={track_file_count})")
                continue


            # --- SKIP: already monitored ---
            if a.get("monitored"):
                print(f"[DEBUG] Skipping monitored album: {title}")
                continue

            candidates.append(a)

        if not candidates:
            print("[WARN] All albums already owned — allowing re-selection fallback")

            candidates = [
                a for a in albums
                if a.get("albumType") == "Album"
            ]

        if not candidates:
            raise Exception("No valid albums found")

        scored = []

        for album in candidates:
            score = 0
            reasons = []

            release_date = album.get("releaseDate")
            if release_date:
                year = int(release_date[:4])
                current_year = 2025
                age = current_year - year

                if deepening:
                    if age <= 2:
                        score += 0
                        reasons.append("very_recent_penalty(0)")
                    elif age <= 6:
                        score += 5
                        reasons.append("core_catalog_peak(+5)")
                    elif age <= 15:
                        score += 3
                        reasons.append("strong_catalog(+3)")
                    else:
                        score += 1
                        reasons.append("deep_catalog(+1)")
                else:
                    if year >= 2015:
                        score += 3
                        reasons.append("recent_release(+3)")
                    elif year >= 2005:
                        score += 2
                        reasons.append("modern_release(+2)")
                    elif year >= 1990:
                        score += 1
                        reasons.append("older_release(+1)")
                    else:
                        score -= 1
                        reasons.append("very_old_release(-1)")
            if partial:
                score += 3
                reasons.append("partial_album_boost(+3)")
                
            adjusted_score = score * affinity
            reasons.append(f"affinity_multiplier({affinity})")

            scored.append({
                "album": album,
                "score": adjusted_score,
                "base_score": score,
                "reasons": reasons
            })

        def sort_key(x):
            score = x["score"]
            release_date = x["album"].get("releaseDate") or "2025"
            year = int(release_date[:4])
            age = 2025 - year
            distance = abs(7 - age)
            return (score, -distance)

        scored.sort(key=sort_key, reverse=True)

        print("\n[DEBUG] Album scoring:")
        for s in scored[:5]:
            print(
                f"- {s['album']['title']} | score={s['score']} "
                f"(base={s['base_score']}) | affinity={affinity} | "
                f"{', '.join(s['reasons'])}"
            )

        best_entry = scored[0]
        return best_entry["album"], best_entry["score"]
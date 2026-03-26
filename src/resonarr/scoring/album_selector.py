class AlbumSelector:
    
    def _normalize_title(self, name):
        return (
            name.lower()
            .replace("’", "'")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
        )
    
    def select_best_album(self, albums, affinity, owned_albums=None, album_tracks=None):
        deepening = affinity > 1.0

        candidates = []

        owned_mbids = owned_albums or set()

        album_tracks = album_tracks or {}

        for a in albums:
            if a.get("albumType") != "Album":
                continue

            title = a.get("title")

            normalized_title = (title or "").lower()
            secondary_types = [t.lower() for t in (a.get("secondaryTypes") or [])]

            if "playlist:" in normalized_title:
                continue

            if "compilation" in secondary_types:
                continue

            if "collection" in normalized_title or "box" in normalized_title:
                continue

            monitored = a.get("monitored", False)

            # --- SKIP: owned in Plex (MBID match) ---
            lidarr_releases = a.get("releases") or []

            is_plex_owned = False

            for release in lidarr_releases:
                release_mbid = release.get("foreignReleaseId")

                if release_mbid and release_mbid in owned_mbids:
                    is_plex_owned = True
                    break

            # --- OWNERSHIP / PARTIAL CHECK: track-level truth ---
            tracks = album_tracks.get(a.get("id"), [])
            total_tracks = len(tracks)
            has_file_count = sum(1 for t in tracks if t.get("hasFile"))

            if total_tracks > 0:
                if has_file_count == total_tracks:
                    print(f"[DEBUG] Skipping fully owned album: {title}")
                    continue

                elif has_file_count > 0:
                    print(f"[DEBUG] Partial album detected: {title} ({has_file_count}/{total_tracks})")
                    partial = True

                else:
                    partial = False
            else:
                partial = False

            # --- IMPORTANT: Plex-owned but NOT complete ---
            if is_plex_owned and has_file_count < total_tracks:
                print(f"[DEBUG] Plex-owned but incomplete: {title}")
                partial = True

            # --- SKIP: already monitored ---
            if monitored:
                print(f"[DEBUG] Skipping monitored album: {title}")
                continue

            a["_partial"] = partial
            candidates.append(a)

        if not candidates:
            print("[INFO] No eligible albums remain after ownership filtering")
            return None, None

        scored = []

        for album in candidates:
            score = 0
            reasons = []

            if album.get("_partial"):
                score += 3
                reasons.append("partial_album_boost(+3)")

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
                f"- {s['album']['title']} | score={s['score']:.2f} "
                f"(base={s['base_score']}) | affinity={affinity} | "
                f"{', '.join(s['reasons'])}"
            )

        best_entry = scored[0]
        return best_entry["album"], best_entry["score"]
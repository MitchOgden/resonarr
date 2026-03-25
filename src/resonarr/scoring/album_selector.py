class AlbumSelector:
    def select_best_album(self, albums, affinity):
        deepening = affinity > 1.0

        candidates = [
            a for a in albums
            if a.get("albumType") == "Album"
            and "set" not in (a.get("title") or "").lower()
            and "collection" not in (a.get("title") or "").lower()
        ]

        if not candidates:
            print("[WARN] No 'Album' types found, falling back to official releases")
            candidates = [
                a for a in albums
                if a.get("releaseStatus") == "official"
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
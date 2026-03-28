from resonarr.state.memory_store import MemoryStore


class ExtendQueryService:
    STATUS_ORDER = [
        "starter_album_candidate",
        "starter_album_recommendation",
        "starter_album_approved",
        "starter_album_rejected",
        "staged_artist",
        "starter_album_exhausted",
        "promotable",
        "new",
        "recommended",
    ]

    def __init__(self, memory=None):
        self.memory = memory or MemoryStore()

    def _candidate_view(self, candidate):
        return {
            "artist_name": candidate.get("artist_name"),
            "status": candidate.get("status"),
            "resolved_artist_name": candidate.get("resolved_artist_name"),
            "resolved_artist_mbid": candidate.get("resolved_artist_mbid"),
            "starter_album_id": candidate.get("starter_album_id"),
            "starter_album_title": candidate.get("starter_album_title"),
            "starter_album_score": candidate.get("starter_album_score"),
            "starter_album_reason": candidate.get("starter_album_reason"),
            "seed_count": candidate.get("seed_count"),
            "seen_count": candidate.get("seen_count"),
            "best_match_score": candidate.get("best_match_score"),
            "source_seeds": candidate.get("source_seeds", []),
        }

    def _resolve_artist_name_from_candidates(self, artist_key):
        for candidate in self.memory.list_extend_candidates():
            if candidate.get("resolved_artist_mbid") == artist_key:
                return (
                    candidate.get("resolved_artist_name")
                    or candidate.get("artist_name")
                )

        return None

    def get_extend_status_summary(self):
        candidates = self.memory.list_extend_candidates()

        counts = {status: 0 for status in self.STATUS_ORDER}
        counts["unknown"] = 0

        for candidate in candidates:
            status = candidate.get("status", "unknown")
            if status in counts:
                counts[status] += 1
            else:
                counts["unknown"] += 1

        return {
            "status": "success",
            "total_candidates": len(candidates),
            "counts": counts,
        }

    def list_candidates_by_status(self, statuses):
        wanted = set(statuses)
        candidates = [
            self._candidate_view(candidate)
            for candidate in self.memory.list_extend_candidates()
            if candidate.get("status") in wanted
        ]

        status_rank = {status: idx for idx, status in enumerate(self.STATUS_ORDER)}

        candidates.sort(
            key=lambda c: (
                status_rank.get(c.get("status"), 999),
                -(c.get("starter_album_score") or 0),
                -(c.get("best_match_score") or 0),
                c.get("artist_name", "").lower(),
            )
        )

        return {
            "status": "success",
            "count": len(candidates),
            "items": candidates,
        }

    def list_suppressed_artists(self):
        items = []

        for key, artist_state in self.memory.state["artists"].items():
            if not artist_state.get("suppressed"):
                continue

            items.append({
                "artist_key": key,
                "artist_name": self._resolve_artist_name_from_candidates(key),
                "suppressed": artist_state.get("suppressed", False),
                "suppression_reason": artist_state.get("suppression_reason"),
                "suppressed_ts": artist_state.get("suppressed_ts"),
            })

        items.sort(key=lambda x: x.get("artist_key", "").lower())

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }
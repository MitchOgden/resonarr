import time

from resonarr.signals.lastfm.client import LastfmClient
from resonarr.execution.lidarr.client import LidarrClient
from resonarr.state.memory_store import MemoryStore
from resonarr.config.settings import (
    EXTEND_LASTFM_PERIOD,
    EXTEND_MIN_SEED_PLAYS,
    EXTEND_MAX_SEEDS,
    EXTEND_SIMILAR_PER_SEED,
    EXTEND_MAX_RECOMMENDATIONS,
    EXTEND_RECOMMENDATION_BACKOFF_HOURS,
    EXTEND_PROMOTION_MIN_SEEN_COUNT,
    EXTEND_PROMOTION_MIN_SEED_COUNT,
    EXTEND_PROMOTION_MIN_MATCH_SCORE,
)


class ExtendCandidateSource:
    def __init__(self):
        self.lastfm = LastfmClient()
        self.lidarr = LidarrClient()
        self.memory = MemoryStore()

    def _normalize(self, name):
        return (name or "").lower().strip()

    def _get_lidarr_artists(self):
        resp = self.lidarr.get("/api/v1/artist")
        artists = resp.json()

        by_name = {}
        for artist in artists:
            artist_name = artist.get("artistName")
            if artist_name:
                by_name[self._normalize(artist_name)] = artist

        return artists, by_name

    def _get_extend_backoff_state(self, artist_name):
        artist_state = self.memory.get_artist_state(f"extend:{self._normalize(artist_name)}")
        last_recommendation_ts = artist_state.get("last_recommendation_ts")

        if not last_recommendation_ts:
            return {
                "in_recommendation_backoff": False,
            }

        backoff_seconds = EXTEND_RECOMMENDATION_BACKOFF_HOURS * 3600
        elapsed = time.time() - last_recommendation_ts

        return {
            "in_recommendation_backoff": elapsed < backoff_seconds,
        }

    def _get_seed_artists(self):
        data = self.lastfm.get_top_artists(period=EXTEND_LASTFM_PERIOD)
        top_artists = data.get("topartists", {}).get("artist", [])

        seeds = []

        for idx, artist in enumerate(top_artists, start=1):
            name = artist.get("name")
            playcount = int(artist.get("playcount", 0))

            if playcount < EXTEND_MIN_SEED_PLAYS:
                continue

            seeds.append({
                "rank": idx,
                "artist_name": name,
                "playcount": playcount,
            })

        seeds.sort(key=lambda x: (-x["playcount"], x["rank"]))
        return seeds[:EXTEND_MAX_SEEDS]

    def get_candidates(self):
        _, lidarr_by_name = self._get_lidarr_artists()
        seeds = self._get_seed_artists()

        candidates_by_name = {}

        for seed in seeds:
            seed_name = seed["artist_name"]
            similar_data = self.lastfm.get_similar_artists(
                seed_name,
                limit=EXTEND_SIMILAR_PER_SEED
            )

            similar_artists = similar_data.get("similarartists", {}).get("artist", [])

            for idx, similar in enumerate(similar_artists, start=1):
                candidate_name = similar.get("name")
                if not candidate_name:
                    continue

                normalized = self._normalize(candidate_name)

                # skip artists already in Lidarr
                if normalized in lidarr_by_name:
                    continue

                backoff = self._get_extend_backoff_state(candidate_name)

                existing = candidates_by_name.get(normalized)
                match_score = float(similar.get("match", 0.0))

                if existing:
                    existing["seed_count"] += 1
                    existing["best_match_score"] = max(existing["best_match_score"], match_score)
                    existing["source_seeds"].append(seed_name)
                    existing["seed_playcount"] = max(existing["seed_playcount"], seed["playcount"])
                    existing["seed_rank"] = min(existing["seed_rank"], seed["rank"])
                    continue

                candidates_by_name[normalized] = {
                    "artist_name": candidate_name,
                    "best_match_score": match_score,
                    "seed_count": 1,
                    "source_seeds": [seed_name],
                    "seed_playcount": seed["playcount"],
                    "seed_rank": seed["rank"],
                    "in_recommendation_backoff": backoff["in_recommendation_backoff"],
                }

        candidates = []

        for candidate in candidates_by_name.values():
            persisted = self.memory.upsert_extend_candidate(
                artist_name=candidate["artist_name"],
                best_match_score=candidate["best_match_score"],
                seed_count=candidate["seed_count"],
                source_seeds=candidate["source_seeds"],
                seed_playcount=candidate["seed_playcount"],
                seed_rank=candidate["seed_rank"],
            )

            candidate["status"] = persisted.get("status", "new")
            candidate["first_seen_ts"] = persisted.get("first_seen_ts")
            candidate["last_seen_ts"] = persisted.get("last_seen_ts")
            candidate["seen_count"] = persisted.get("seen_count", 1)
            candidate["recommendation_count"] = persisted.get("recommendation_count", 0)

            promotable = (
                candidate["seen_count"] >= EXTEND_PROMOTION_MIN_SEEN_COUNT and
                (
                    candidate["seed_count"] >= EXTEND_PROMOTION_MIN_SEED_COUNT or
                    candidate["best_match_score"] >= EXTEND_PROMOTION_MIN_MATCH_SCORE
                )
            )

            candidate["is_promotable"] = promotable

            if promotable and candidate["status"] != "promotable":
                self.memory.mark_extend_candidate_promotable(candidate["artist_name"])
                candidate["status"] = "promotable"

            candidates.append(candidate)

        status_rank = {
            "promotable": 0,
            "new": 1,
            "recommended": 2,
        }

        candidates.sort(
            key=lambda x: (
                x["in_recommendation_backoff"],
                status_rank.get(x.get("status", "new"), 3),
                -x["seed_count"],
                -x["best_match_score"],
                -x["seed_playcount"],
                x["seed_rank"],
                x["artist_name"].lower(),
            )
        )

        return candidates[:EXTEND_MAX_RECOMMENDATIONS]
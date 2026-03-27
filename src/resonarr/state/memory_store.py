import json
import os
import time

STATE_FILE = "resonarr_state.json"


class MemoryStore:
    def __init__(self):
        self.state = self._load()

    def _load(self):
        if not os.path.exists(STATE_FILE):
            return {
                "artists": {},
                "extend_candidates": {}
            }

        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        state.setdefault("artists", {})
        state.setdefault("extend_candidates", {})

        return state

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def get_artist_last_action(self, mbid):
        return self.state["artists"].get(mbid)

    def set_artist_action(self, mbid):
        artist = self.state["artists"].get(mbid, {})

        artist["last_action_ts"] = int(time.time())

        self.state["artists"][mbid] = artist
        self._save()
        
    def set_artist_recommendation(self, mbid):
        artist = self.state["artists"].get(mbid, {})

        artist["last_recommendation_ts"] = int(time.time())

        self.state["artists"][mbid] = artist
        self._save()

    def suppress_artist(self, mbid, reason="manual"):
        artist = self.state["artists"].get(mbid, {})

        artist["suppressed"] = True
        artist["suppression_reason"] = reason
        artist["suppressed_ts"] = int(time.time())

        self.state["artists"][mbid] = artist
        self._save()


    def is_artist_suppressed(self, mbid):
        artist = self.state["artists"].get(mbid)

        if not artist:
            return False

        return artist.get("suppressed", False)
    
    def boost_artist_affinity(self, mbid, multiplier=1.5, reason="manual"):
        artist = self.state["artists"].get(mbid, {})

        artist["affinity"] = multiplier
        artist["affinity_reason"] = reason
        artist["affinity_ts"] = int(time.time())

        self.state["artists"][mbid] = artist
        self._save()


    def get_artist_affinity(self, mbid):
        artist = self.state["artists"].get(mbid)

        if not artist:
            return 1.0

        return artist.get("affinity", 1.0)
    
    def unsuppress_artist(self, mbid):
        artist = self.state["artists"].get(mbid)

        if not artist:
            return

        artist["suppressed"] = False
        artist["suppression_reason"] = None

        self.state["artists"][mbid] = artist
        self._save()

    def get_artist_state(self, mbid):
        return self.state["artists"].get(mbid, {})
    
    def get_extend_candidate(self, artist_name):
        key = artist_name.lower().strip()
        return self.state["extend_candidates"].get(key, {})

    def upsert_extend_candidate(
        self,
        artist_name,
        best_match_score,
        seed_count,
        source_seeds,
        seed_playcount,
        seed_rank,
    ):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})

        if not candidate:
            candidate = {
                "artist_name": artist_name,
                "first_seen_ts": now,
                "status": "new",
                "seen_count": 0,
                "recommendation_count": 0,
            }

        existing_seeds = set(candidate.get("source_seeds", []))
        merged_seeds = sorted(existing_seeds.union(set(source_seeds)))

        candidate["artist_name"] = artist_name
        candidate["best_match_score"] = max(candidate.get("best_match_score", 0.0), best_match_score)
        candidate["seed_count"] = max(candidate.get("seed_count", 0), seed_count)
        candidate["source_seeds"] = merged_seeds
        candidate["seed_playcount"] = max(candidate.get("seed_playcount", 0), seed_playcount)
        candidate["seed_rank"] = min(candidate.get("seed_rank", seed_rank), seed_rank)
        candidate["last_seen_ts"] = now
        candidate["seen_count"] = candidate.get("seen_count", 0) + 1
        candidate.setdefault("recommendation_count", 0)

        self.state["extend_candidates"][key] = candidate
        self._save()

        return candidate

    def mark_extend_candidate_recommended(self, artist_name):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})
        if not candidate:
            candidate = {
                "artist_name": artist_name,
                "first_seen_ts": now,
            }

        candidate["status"] = "recommended"
        candidate["last_recommended_ts"] = now
        candidate["recommendation_count"] = candidate.get("recommendation_count", 0) + 1

        self.state["extend_candidates"][key] = candidate
        self._save()

    def mark_extend_candidate_promotable(self, artist_name):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})
        if not candidate:
            return

        candidate["status"] = "promotable"
        candidate["promotable_ts"] = now

        self.state["extend_candidates"][key] = candidate
        self._save()

    def mark_extend_candidate_starter_album_candidate(
        self,
        artist_name,
        artist_mbid,
        resolved_artist_name,
        album_id,
        album_title,
        reason,
        score,
    ):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})
        if not candidate:
            candidate = {
                "artist_name": artist_name,
                "first_seen_ts": now,
            }

        candidate["status"] = "starter_album_candidate"
        candidate["starter_album_candidate_ts"] = now
        candidate["starter_album_candidate_count"] = candidate.get("starter_album_candidate_count", 0) + 1
        candidate["resolved_artist_mbid"] = artist_mbid
        candidate["resolved_artist_name"] = resolved_artist_name
        candidate["starter_album_id"] = album_id
        candidate["starter_album_title"] = album_title
        candidate["starter_album_reason"] = reason
        candidate["starter_album_score"] = score

        self.state["extend_candidates"][key] = candidate
        self._save()

    def list_extend_candidates(self):
        return list(self.state["extend_candidates"].values())
    
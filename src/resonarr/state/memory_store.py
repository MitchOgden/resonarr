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
                "extend_candidates": {},
                "prune_candidates": {}
            }

        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        state.setdefault("artists", {})
        state.setdefault("extend_candidates", {})
        state.setdefault("prune_candidates", {})

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

    def mark_extend_candidate_staged_artist(
        self,
        artist_name,
        artist_mbid,
        resolved_artist_name,
    ):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})
        if not candidate:
            candidate = {
                "artist_name": artist_name,
                "first_seen_ts": now,
            }

        candidate["status"] = "staged_artist"
        candidate["staged_artist_ts"] = now
        candidate["staged_artist_count"] = candidate.get("staged_artist_count", 0) + 1
        candidate["resolved_artist_mbid"] = artist_mbid
        candidate["resolved_artist_name"] = resolved_artist_name

        self.state["extend_candidates"][key] = candidate
        self._save()

    def mark_extend_candidate_starter_album_exhausted(
        self,
        artist_name,
        artist_mbid,
        resolved_artist_name,
        reason,
    ):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key, {})
        if not candidate:
            candidate = {
                "artist_name": artist_name,
                "first_seen_ts": now,
            }

        candidate["status"] = "starter_album_exhausted"
        candidate["starter_album_exhausted_ts"] = now
        candidate["starter_album_exhausted_count"] = candidate.get("starter_album_exhausted_count", 0) + 1
        candidate["resolved_artist_mbid"] = artist_mbid
        candidate["resolved_artist_name"] = resolved_artist_name
        candidate["starter_album_exhausted_reason"] = reason

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

    def mark_extend_candidate_starter_album_recommendation(
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

        candidate["status"] = "starter_album_recommendation"
        candidate["starter_album_recommendation_ts"] = now
        candidate["starter_album_recommendation_count"] = candidate.get("starter_album_recommendation_count", 0) + 1
        candidate["resolved_artist_mbid"] = artist_mbid
        candidate["resolved_artist_name"] = resolved_artist_name
        candidate["starter_album_id"] = album_id
        candidate["starter_album_title"] = album_title
        candidate["starter_album_reason"] = reason
        candidate["starter_album_score"] = score

        self.state["extend_candidates"][key] = candidate
        self._save()

    def clear_extend_recommendation_backoff(self, artist_name):
        key = f"extend:{artist_name.lower().strip()}"

        artist = self.state["artists"].get(key)
        if not artist:
            return False

        if "last_recommendation_ts" in artist:
            del artist["last_recommendation_ts"]

        self.state["artists"][key] = artist
        self._save()
        return True
    
    def mark_extend_candidate_approved(self, artist_name, note="manual_approve"):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key)
        if not candidate:
            return

        candidate["status"] = "starter_album_approved"
        candidate["starter_album_approved_ts"] = now
        candidate["starter_album_approved_note"] = note

        self.state["extend_candidates"][key] = candidate
        self._save()

    def mark_extend_candidate_rejected(self, artist_name, note="manual_reject"):
        key = artist_name.lower().strip()
        now = int(time.time())

        candidate = self.state["extend_candidates"].get(key)
        if not candidate:
            return

        candidate["status"] = "starter_album_rejected"
        candidate["starter_album_rejected_ts"] = now
        candidate["starter_album_rejected_note"] = note

        self.state["extend_candidates"][key] = candidate
        self._save()

    def list_extend_candidates_by_status(self, statuses):
        wanted = set(statuses)
        return [
            candidate
            for candidate in self.state["extend_candidates"].values()
            if candidate.get("status") in wanted
        ]

    def find_extend_candidate_by_artist_name(self, artist_name):
        key = artist_name.lower().strip()
        return self.state["extend_candidates"].get(key)    

    def list_extend_candidates(self):
        return list(self.state["extend_candidates"].values())
    
    def _prune_candidate_key(self, artist_name, album_name, album_mbid=None, lidarr_album_id=None):
        if album_mbid:
            return f"mbid:{str(album_mbid).lower().strip()}"

        if lidarr_album_id is not None:
            return f"lidarr:{lidarr_album_id}"

        artist_key = (artist_name or "").lower().strip()
        album_key = (album_name or "").lower().strip()
        return f"name:{artist_key}::{album_key}"

    def upsert_prune_candidate(self, item):
        key = self._prune_candidate_key(
            artist_name=item.get("artist_name"),
            album_name=item.get("album_name"),
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=item.get("lidarr_album_id"),
        )
        now = int(time.time())

        candidate = self.state["prune_candidates"].get(key, {})
        existing_status = candidate.get("status")

        candidate["key"] = key
        candidate["artist_name"] = item.get("artist_name")
        candidate["artist_mbid"] = item.get("artist_mbid")
        candidate["album_name"] = item.get("album_name")
        candidate["album_mbid"] = item.get("album_mbid")
        candidate["lidarr_album_id"] = item.get("lidarr_album_id")
        candidate["lidarr_artist_id"] = item.get("lidarr_artist_id")
        candidate["lidarr_has_files"] = item.get("lidarr_has_files")
        candidate["bad_ratio"] = item.get("bad_ratio")
        candidate["rated_tracks"] = item.get("rated_tracks")
        candidate["bad_tracks"] = item.get("bad_tracks")
        candidate["total_tracks_seen"] = item.get("total_tracks_seen")
        candidate["reason"] = item.get("reason")
        candidate["match_method"] = item.get("match_method")
        candidate["matched"] = item.get("matched", False)
        candidate["action"] = item.get("action")
        candidate["last_seen_ts"] = now
        candidate.setdefault("first_seen_ts", now)

        if existing_status in {"prune_rejected", "prune_executed"}:
            candidate["status"] = existing_status
        else:
            candidate["status"] = "prune_recommendation"

        self.state["prune_candidates"][key] = candidate
        self._save()
        return candidate

    def get_prune_candidate(self, artist_name, album_name, album_mbid=None, lidarr_album_id=None):
        key = self._prune_candidate_key(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=album_mbid,
            lidarr_album_id=lidarr_album_id,
        )
        return self.state["prune_candidates"].get(key, {})

    def list_prune_candidates(self):
        return list(self.state["prune_candidates"].values())

    def list_prune_candidates_by_status(self, statuses):
        wanted = set(statuses)
        return [
            candidate
            for candidate in self.state["prune_candidates"].values()
            if candidate.get("status") in wanted
        ]

    def mark_prune_candidate_approved(self, artist_name, album_name, album_mbid=None, lidarr_album_id=None, note="manual_approve"):
        key = self._prune_candidate_key(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=album_mbid,
            lidarr_album_id=lidarr_album_id,
        )
        now = int(time.time())

        candidate = self.state["prune_candidates"].get(key)
        if not candidate:
            return

        candidate["status"] = "prune_approved"
        candidate["prune_approved_ts"] = now
        candidate["prune_approved_note"] = note

        self.state["prune_candidates"][key] = candidate
        self._save()

    def mark_prune_candidate_executed(self, artist_name, album_name, album_mbid=None, lidarr_album_id=None, note="executed"):
        key = self._prune_candidate_key(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=album_mbid,
            lidarr_album_id=lidarr_album_id,
        )
        now = int(time.time())

        candidate = self.state["prune_candidates"].get(key)
        if not candidate:
            return

        candidate["status"] = "prune_executed"
        candidate["prune_executed_ts"] = now
        candidate["prune_executed_note"] = note

        self.state["prune_candidates"][key] = candidate
        self._save()

    def mark_prune_candidate_rejected(self, artist_name, album_name, album_mbid=None, lidarr_album_id=None, note="manual_reject"):
        key = self._prune_candidate_key(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=album_mbid,
            lidarr_album_id=lidarr_album_id,
        )
        now = int(time.time())

        candidate = self.state["prune_candidates"].get(key)
        if not candidate:
            return

        candidate["status"] = "prune_rejected"
        candidate["prune_rejected_ts"] = now
        candidate["prune_rejected_note"] = note

        self.state["prune_candidates"][key] = candidate
        self._save()
    
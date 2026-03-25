# src/resonarr/execution/lidarr/adapter.py

import time
from .client import LidarrClient
from resonarr.state.memory_store import MemoryStore
from resonarr.domain.action_intent import ActionIntent
from resonarr.config.settings import (
    ROOT_FOLDER,
    QUALITY_PROFILE_NAME,
    METADATA_PROFILE_NAME,
    ACQUIRE_SCORE_THRESHOLD,
    RECOMMEND_SCORE_THRESHOLD,
    ARTIST_COOLDOWN_HOURS
)

class LidarrAdapter:
    def __init__(self):
        self.client = LidarrClient()
        self.memory = MemoryStore()

    def acquire_artist_best_release(self, mbid):
        print(f"[INFO] Processing artist MBID: {mbid}")

        artist = self._get_artist_by_mbid(mbid)

        if artist:
            print("[INFO] Artist already exists")
        else:
            print("[INFO] Adding artist...")
            self._add_artist(mbid)

        artist = self._wait_for_artist(mbid)

        if not artist:
            return {"status": "failed", "reason": "artist hydration timeout"}

        albums = self._get_albums(artist["id"])

        if not albums:
            return {"status": "failed", "reason": "no albums found"}

        intent = self._decide_acquire_artist(mbid, artist, albums)

        print(f"[INFO] Intent decided:")
        print(f"  Action: {intent.action_type}")
        print(f"  Artist: {intent.artist_name}")
        print(f"  Album: {intent.target_album_title}")
        print(f"  Reason: {intent.reason}")
        print(f"  Score: {intent.score}")
        print(f"  Thresholds: acquire={ACQUIRE_SCORE_THRESHOLD}, recommend={RECOMMEND_SCORE_THRESHOLD}")

        self._execute_action_intent(intent, artist, albums)

        return {
            "status": "success",
            "action": intent.action_type,
            "artist": intent.artist_name,
            "selected_album": intent.target_album_title,
            "reason": intent.reason,
            "album_count": intent.metadata.get("album_count")
        }

    # ------------------------
    # Profiles
    # ------------------------

    def _get_quality_profiles(self):
        resp = self.client.get("/api/v1/qualityprofile")
        print(f"[DEBUG] Quality profiles status: {resp.status_code}")
        data = resp.json()
        print(f"[DEBUG] Quality profiles returned: {len(data)}")
        return data


    def _get_metadata_profiles(self):
        resp = self.client.get("/api/v1/metadataprofile")
        print(f"[DEBUG] Metadata profiles status: {resp.status_code}")
        data = resp.json()
        print(f"[DEBUG] Metadata profiles returned: {len(data)}")
        return data


    def _resolve_quality_profile_id(self, name="Lossless"):
        profiles = self._get_quality_profiles()

        for profile in profiles:
            if profile.get("name", "").lower() == name.lower():
                print(f"[DEBUG] Resolved quality profile '{name}' -> ID {profile['id']}")
                return profile["id"]

        raise Exception(f"Quality profile '{name}' not found")


    def _resolve_metadata_profile_id(self, name="Standard"):
        profiles = self._get_metadata_profiles()

        for profile in profiles:
            if profile.get("name", "").lower() == name.lower():
                print(f"[DEBUG] Resolved metadata profile '{name}' -> ID {profile['id']}")
                return profile["id"]

        raise Exception(f"Metadata profile '{name}' not found")

    # ------------------------
    # Artist
    # ------------------------

    def _lookup_artist(self, mbid):
        resp = self.client.get(f"/api/v1/artist/lookup?term=mbid:{mbid}")
        
        print(f"[DEBUG] Lookup status: {resp.status_code}")
        
        data = resp.json()
        
        if not data:
            print("[ERROR] Lookup returned no results")
            return None
        
        return data[0]

    def _get_artist_by_mbid(self, mbid):
        resp = self.client.get("/api/v1/artist")
        artists = resp.json()

        print(f"[DEBUG] Total artists: {len(artists)}")

        for artist in artists:
            if artist.get("foreignArtistId") == mbid:
                print("[DEBUG] Found artist match")
                return artist

        print("[DEBUG] Artist NOT found")
        return None

    def _add_artist(self, mbid):
        lookup = self._lookup_artist(mbid)

        if not lookup:
            raise Exception("Artist lookup failed")

        quality_profile_id = self._resolve_quality_profile_id(QUALITY_PROFILE_NAME)
        metadata_profile_id = self._resolve_metadata_profile_id(METADATA_PROFILE_NAME)

        payload = {
            "artistName": lookup["artistName"],
            "foreignArtistId": lookup["foreignArtistId"],
            "qualityProfileId": quality_profile_id,
            "metadataProfileId": metadata_profile_id,
            "rootFolderPath": ROOT_FOLDER,
            "monitored": False,
            "addOptions": {
                "searchForMissingAlbums": False
            }
        }

        resp = self.client.post("/api/v1/artist", json=payload)

        print(f"[DEBUG] Add artist status: {resp.status_code}")
        print(f"[DEBUG] Add artist response: {resp.text}")

    def _wait_for_artist(self, mbid, retries=10, delay=2):
        for i in range(retries):
            artist = self._get_artist_by_mbid(mbid)
            if artist:
                albums = self._get_albums(artist["id"])
                if albums:
                    return artist
            print(f"[WAIT] Attempt {i+1}...")
            time.sleep(delay)
        return None

    # ------------------------
    # Albums
    # ------------------------

    def _get_albums(self, artist_id):
        resp = self.client.get(f"/api/v1/album?artistId={artist_id}")
        
        print(f"[DEBUG] Album API status: {resp.status_code}")
        
        data = resp.json()
        print(f"[DEBUG] Albums returned: {len(data)}")
        
        return data

    def _select_best_album(self, albums):
        
        affinity = self.memory.get_artist_affinity(self.current_mbid)

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

            # --- Release date scoring ---
            release_date = album.get("releaseDate")

            if release_date:
                year = int(release_date[:4])
                current_year = 2025  # safe static for MVP

                age = current_year - year

                if deepening:
                    # Strong preference for "true core era"
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
                    # original behavior
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

        # highest score → closest to "ideal core age" wins ✔
        def sort_key(x):
            score = x["score"]

            release_date = x["album"].get("releaseDate") or "2025"
            year = int(release_date[:4])
            age = 2025 - year

            distance = abs(7 - age)

            return (score, -distance)


        scored.sort(key=sort_key, reverse=True)

        # Debug output
        print("\n[DEBUG] Album scoring:")
        for s in scored[:5]:
            print(f"- {s['album']['title']} | score={s['score']} (base={s['base_score']}) | affinity={affinity} | {', '.join(s['reasons'])}")

        best_entry = scored[0]
        best = best_entry["album"]
        best_score = best_entry["score"]

        return best, best_score

    # ------------------------
    # Decision
    # ------------------------    

    def _decide_acquire_artist(self, mbid, artist, albums):

        artist_state = self.memory.get_artist_state(mbid)

        if artist_state and artist_state.get("suppressed"):
            reason = artist_state.get("suppression_reason", "unknown")

            print("[INFO] Artist is suppressed — skipping")

            return ActionIntent(
                action_type="NO_ACTION",
                artist_mbid=mbid,
                artist_name=artist["artistName"],
                target_album_title="(suppressed)",
                reason=f"artist_suppressed ({reason})",
                metadata={
                    "album_count": len(albums)
                }
            )

        last = self.memory.get_artist_last_action(mbid)

        if last and last.get("last_action_ts"):
            elapsed = time.time() - last["last_action_ts"]
            cooldown_seconds = ARTIST_COOLDOWN_HOURS * 3600

            if elapsed < cooldown_seconds:
                print("[INFO] Artist in cooldown — skipping")

                return ActionIntent(
                    action_type="NO_ACTION",
                    artist_mbid=mbid,
                    artist_name=artist["artistName"],
                    target_album_title="(cooldown)",
                    reason=f"in_cooldown ({int(elapsed)}s elapsed)",
                    metadata={
                        "cooldown_hours": ARTIST_COOLDOWN_HOURS,
                        "album_count": len(albums)
                    }
                )

        self.current_mbid = mbid
        best, score = self._select_best_album(albums)

        if score >= ACQUIRE_SCORE_THRESHOLD:
            action_type = "ACQUIRE_ARTIST"
            reason = f"score {score} >= acquire threshold {ACQUIRE_SCORE_THRESHOLD}"
        elif score >= RECOMMEND_SCORE_THRESHOLD:
            action_type = "RECOMMEND_ONLY"
            reason = f"score {score} below acquire threshold {ACQUIRE_SCORE_THRESHOLD}"
        else:
            action_type = "NO_ACTION"
            reason = f"score {score} below recommend threshold {RECOMMEND_SCORE_THRESHOLD}"

        return ActionIntent(
            action_type=action_type,
            artist_mbid=mbid,
            artist_name=artist["artistName"],
            target_album_id=best["id"],
            target_album_title=best["title"],
            reason=reason,
            score=score,
            metadata={
                "album_count": len(albums)
            }
        )
    
    def _execute_action_intent(self, intent: ActionIntent, artist, albums):
        print(f"\n[INFO] Executing intent: {intent.action_type}")

        if intent.dry_run:
            print("[INFO] Dry run — no changes applied")
            return

        if intent.action_type == "NO_ACTION":
            print("[INFO] No action taken")
            return

        if intent.action_type == "RECOMMEND_ONLY":
            print("[INFO] Recommendation only — not executing")
            self.memory.set_artist_action(intent.artist_mbid)
            return

        if intent.action_type == "ACQUIRE_ARTIST":
            best_album = next(
                a for a in albums if a["id"] == intent.target_album_id
            )

            self._apply_monitoring(artist, best_album, albums)

            self.memory.set_artist_action(intent.artist_mbid)

    # ------------------------
    # Monitoring
    # ------------------------

    def _apply_monitoring(self, artist, best_album, all_albums):
        print("\n[DEBUG] ===== BEFORE MONITORING =====")
        for album in all_albums[:10]:
            print(f"- {album['title']} | monitored={album.get('monitored')}")

        print(f"\n[DEBUG] Target album: {best_album['title']} (ID: {best_album['id']})")

        print("\n[INFO] Applying monitoring (per-album)...")

        for album in all_albums:
            desired = album["id"] == best_album["id"]

            if album.get("monitored") == desired:
                continue  # skip if already correct

            album["monitored"] = desired

            resp = self.client.put(f"/api/v1/album/{album['id']}", json=album)

            print(f"[DEBUG] Update {album['title']} → {desired} | status={resp.status_code}")

            if resp.status_code != 202 and resp.status_code != 200:
                print(f"[ERROR] Failed updating {album['title']}: {resp.text[:200]}")

        # Re-fetch to verify
        updated = self._get_albums(artist["id"])

        print("\n[DEBUG] ===== AFTER MONITORING =====")
        for album in updated[:10]:
            print(f"- {album['title']} | monitored={album.get('monitored')}")

        monitored = [a for a in updated if a.get("monitored")]

        print(f"\n[DEBUG] Total monitored albums: {len(monitored)}")

        for m in monitored:
            print(f"[DEBUG] MONITORED: {m['title']}")

        if len(monitored) != 1:
            print("[ERROR] Monitoring mismatch — expected exactly 1 monitored album")
        else:
            print("[SUCCESS] Monitoring correctly applied")
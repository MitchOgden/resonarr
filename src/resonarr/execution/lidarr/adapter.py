# src/resonarr/execution/lidarr/adapter.py

import time
from .client import LidarrClient


class LidarrAdapter:
    def __init__(self):
        self.client = LidarrClient()

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

        best_album = self._select_best_album(albums)

        print(f"[INFO] Selected album: {best_album['title']}")

        self._apply_monitoring(artist, best_album, albums)

        return {
            "status": "success",
            "artist": artist["artistName"],
            "selected_album": best_album["title"],
            "album_count": len(albums)
        }

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

        payload = {
            "artistName": lookup["artistName"],
            "foreignArtistId": lookup["foreignArtistId"],
            "qualityProfileId": 1,
            "metadataProfileId": 1,
            "rootFolderPath": "/volume1/music/library",  # FIX THIS
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
        # Step 1 — Prefer real albums
        valid = [
            a for a in albums
            if a.get("albumType") == "Album"
        ]

        # Step 2 — Fallback if somehow empty
        if not valid:
            print("[WARN] No 'Album' types found, falling back to official releases")

            valid = [
                a for a in albums
                if a.get("releaseStatus") == "official"
            ]

        if not valid:
            raise Exception("No valid albums found")

        # Step 3 — pick first (temporary)
        return valid[0]

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
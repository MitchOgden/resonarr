import json
import os
import time

STATE_FILE = "resonarr_state.json"


class MemoryStore:
    def __init__(self):
        self.state = self._load()

    def _load(self):
        if not os.path.exists(STATE_FILE):
            return {"artists": {}}

        with open(STATE_FILE, "r") as f:
            return json.load(f)

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
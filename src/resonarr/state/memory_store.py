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
        self.state["artists"][mbid] = {
            "last_action_ts": int(time.time())
        }
        self._save()
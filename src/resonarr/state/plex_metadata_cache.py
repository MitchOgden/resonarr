import atexit
import json
import os


PLEX_METADATA_CACHE_FILE = "resonarr_plex_metadata_cache.json"


class PlexMetadataCache:
    def __init__(self, path=PLEX_METADATA_CACHE_FILE):
        self.path = path
        self.state = self._load()
        self._dirty = False
        atexit.register(self.flush)

    def _load(self):
        if not os.path.exists(self.path):
            return {
                "albums": {}
            }

        with open(self.path, "r", encoding="utf-8") as handle:
            state = json.load(handle)

        state.setdefault("albums", {})
        return state

    def _minimal_album_payload(self, album):
        payload = {
            "ratingKey": album.get("ratingKey"),
            "title": album.get("title"),
        }

        if album.get("guid") is not None:
            payload["guid"] = album.get("guid")

        if album.get("Guid") is not None:
            payload["Guid"] = album.get("Guid")

        if album.get("parentGuid") is not None:
            payload["parentGuid"] = album.get("parentGuid")

        return payload

    def get_album_metadata(self, rating_key):
        if rating_key is None:
            return None

        return self.state["albums"].get(str(rating_key))

    def put_album_metadata(self, album):
        rating_key = album.get("ratingKey")
        if rating_key is None:
            return

        key = str(rating_key)
        payload = self._minimal_album_payload(album)
        existing = self.state["albums"].get(key)

        if existing == payload:
            return

        self.state["albums"][key] = payload
        self._dirty = True

    def flush(self):
        if not self._dirty:
            return

        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)

        self._dirty = False

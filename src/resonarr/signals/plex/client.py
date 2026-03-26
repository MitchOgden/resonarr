import requests
from resonarr.config.settings import PLEX_BASE_URL, PLEX_TOKEN


class PlexClient:
    def __init__(self):
        self.base_url = PLEX_BASE_URL
        self.token = PLEX_TOKEN

    def _get(self, path):
        url = f"{self.base_url}{path}"
        params = {"X-Plex-Token": self.token}

        headers = {
            "Accept": "application/json"
        }

        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()

        return r.json()

    def search(self, query):
        return self._get(f"/hubs/search?query={query}")
    
    def get_music_library_section_id(self):
        data = self._get("/library/sections")

        for section in data.get("MediaContainer", {}).get("Directory", []):
            if section.get("type") == "artist":
                return section.get("key")

        return None


    def get_artists(self):
        section_id = self.get_music_library_section_id()

        if not section_id:
            return []

        data = self._get(f"/library/sections/{section_id}/all")

        return data.get("MediaContainer", {}).get("Metadata", [])
    
    def get_albums(self, artist_rating_key):
        """
        Fetch albums with FULL metadata (including GUIDs)
        """
        data = self._get(f"/library/metadata/{artist_rating_key}/children")

        albums = data.get("MediaContainer", {}).get("Metadata", [])

        full_albums = []

        for album in albums:
            rating_key = album.get("ratingKey")

            if not rating_key:
                continue

            full = self._get(f"/library/metadata/{rating_key}")

            meta = full.get("MediaContainer", {}).get("Metadata", [])

            if meta:
                full_albums.append(meta[0])
            else:
                full_albums.append(album)  # fallback

        return full_albums
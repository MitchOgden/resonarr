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
import requests
from resonarr.config.settings import PLEX_BASE_URL, PLEX_TOKEN


class PlexClient:
    def __init__(self):
        self.base_url = PLEX_BASE_URL
        self.token = PLEX_TOKEN

    def _get(self, path):
        url = f"{self.base_url}{path}"
        params = {"X-Plex-Token": self.token}

        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()

    def search(self, query):
        return self._get(f"/hubs/search?query={query}")
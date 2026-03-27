# src/resonarr/execution/lidarr/client.py

import os
import requests


class LidarrClient:
    def __init__(self):
        self.base_url = os.getenv("LIDARR_URL")
        self.api_key = os.getenv("LIDARR_API_KEY")

        if not self.base_url or not self.api_key:
            raise ValueError("LIDARR_URL and LIDARR_API_KEY must be set")

        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        })

    def get(self, path, params=None):
        url = f"{self.base_url}{path}"
        return self.session.get(url, params=params)

    def post(self, path, json=None, params=None):
        url = f"{self.base_url}{path}"
        return self.session.post(url, json=json, params=params)

    def put(self, path, json=None, params=None):
        url = f"{self.base_url}{path}"
        return self.session.put(url, json=json, params=params)
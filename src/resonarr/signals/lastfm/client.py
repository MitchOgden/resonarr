import requests
from resonarr.config.settings import LASTFM_API_KEY, LASTFM_USERNAME


class LastfmClient:
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"

    def _get(self, params):
        params.update({
            "api_key": LASTFM_API_KEY,
            "format": "json"
        })

        r = requests.get(self.BASE_URL, params=params)

        if r.status_code != 200:
            raise Exception(f"Last.fm API error: {r.status_code}")

        return r.json()

    def get_top_artists(self, period="1month"):
        return self._get({
            "method": "user.getTopArtists",
            "user": LASTFM_USERNAME,
            "period": period,
            "limit": 100
        })

    def get_top_albums(self, artist_name, period="1month"):
        return self._get({
            "method": "user.getTopAlbums",
            "user": LASTFM_USERNAME,
            "period": period,
            "limit": 200
        })
    
    def get_similar_artists(self, artist_name, limit=10):
        return self._get({
            "method": "artist.getSimilar",
            "artist": artist_name,
            "limit": limit
        })
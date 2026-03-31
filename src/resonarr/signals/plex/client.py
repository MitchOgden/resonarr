import requests
from resonarr.config.settings import PLEX_BASE_URL, PLEX_TOKEN
from resonarr.utils.api_resilience import request_with_retry


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

        response = request_with_retry(
            source="plex",
            operation=path,
            request_func=requests.get,
            url=url,
            params=params,
            headers=headers,
            context={"path": path},
        )
        return response.json()

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

    def _album_needs_full_metadata(self, album):
        guid_entries = album.get("Guid") or []
        direct_guid = album.get("guid")

        guid_values = []

        for entry in guid_entries:
            if isinstance(entry, dict):
                value = entry.get("id")
                if value:
                    guid_values.append(str(value))
            elif entry:
                guid_values.append(str(entry))

        if direct_guid:
            guid_values.append(str(direct_guid))

        for value in guid_values:
            lowered = value.lower()
            if "musicbrainz" in lowered or "mbid" in lowered:
                return False

        return True

    def get_albums(self, artist_rating_key):
        """
        Fetch album list from the artist children endpoint and only expand
        individual albums when the child payload does not already expose GUID
        metadata needed by downstream MBID extraction.
        """
        data = self._get(f"/library/metadata/{artist_rating_key}/children")
        albums = data.get("MediaContainer", {}).get("Metadata", [])

        resolved_albums = []

        for album in albums:
            rating_key = album.get("ratingKey")

            if not rating_key:
                continue

            if not self._album_needs_full_metadata(album):
                resolved_albums.append(album)
                continue

            full = self._get(f"/library/metadata/{rating_key}")
            meta = full.get("MediaContainer", {}).get("Metadata", [])

            if meta:
                resolved_albums.append(meta[0])
            else:
                resolved_albums.append(album)

        return resolved_albums
    
    def get_album_tracks(self, album_rating_key):
        data = self._get(f"/library/metadata/{album_rating_key}/children")
        return data.get("MediaContainer", {}).get("Metadata", [])
    
    def scan_music_library_files(self):
        section_id = self.get_music_library_section_id()
        if not section_id:
            return {
                "status": "failed",
                "reason": "music library section not found",
            }

        url = f"{self.base_url}/library/sections/{section_id}/refresh"
        params = {"X-Plex-Token": self.token}
        headers = {"Accept": "application/json"}

        r = requests.get(url, params=params, headers=headers)
        if r.status_code not in (200, 202):
            return {
                "status": "failed",
                "reason": f"plex scan failed ({r.status_code})",
                "response_text": r.text[:300],
            }

        return {
            "status": "success",
            "section_id": section_id,
            "status_code": r.status_code,
        }

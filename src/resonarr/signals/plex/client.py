import time

import requests
from resonarr.config.settings import PLEX_BASE_URL, PLEX_TOKEN
from resonarr.state.plex_metadata_cache import PlexMetadataCache
from resonarr.utils.api_resilience import request_with_retry


class PlexClient:
    def __init__(self, metadata_cache=None):
        self.base_url = PLEX_BASE_URL
        self.token = PLEX_TOKEN
        self.metadata_cache = metadata_cache or PlexMetadataCache()

    def _log_phase_elapsed(self, label, started_at):
        elapsed = time.perf_counter() - started_at
        print(f"[PERF][plex_client] {label}: {elapsed:.2f}s")

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

    def _merge_cached_album_metadata(self, album, cached_album):
        merged = dict(album)

        if cached_album.get("guid") is not None:
            merged["guid"] = cached_album.get("guid")

        if cached_album.get("Guid") is not None:
            merged["Guid"] = cached_album.get("Guid")

        if cached_album.get("parentGuid") is not None:
            merged["parentGuid"] = cached_album.get("parentGuid")

        return merged

    def flush_caches(self):
        self.metadata_cache.flush()

    def get_albums(self, artist_rating_key):
        """
        Fetch album list from the artist children endpoint.

        Resolution order:
        1) use child payload directly when it already contains usable MBID data
        2) use persisted cached album metadata when available
        3) fetch full album metadata from Plex and persist the stable GUID fields
        """
        total_started_at = time.perf_counter()

        phase_started_at = time.perf_counter()
        data = self._get(f"/library/metadata/{artist_rating_key}/children")
        self._log_phase_elapsed("get_albums.children_fetch", phase_started_at)

        albums = data.get("MediaContainer", {}).get("Metadata", [])
        resolved_albums = []

        child_payload_fast_path_count = 0
        metadata_cache_hit_count = 0
        fallback_full_metadata_count = 0
        missing_rating_key_count = 0

        phase_started_at = time.perf_counter()
        for album in albums:
            rating_key = album.get("ratingKey")

            if not rating_key:
                missing_rating_key_count += 1
                continue

            if not self._album_needs_full_metadata(album):
                child_payload_fast_path_count += 1
                resolved_albums.append(album)
                continue

            cached_album = self.metadata_cache.get_album_metadata(rating_key)
            if cached_album and not self._album_needs_full_metadata(cached_album):
                metadata_cache_hit_count += 1
                resolved_albums.append(self._merge_cached_album_metadata(album, cached_album))
                continue

            fallback_full_metadata_count += 1
            full = self._get(f"/library/metadata/{rating_key}")
            meta = full.get("MediaContainer", {}).get("Metadata", [])

            if meta:
                resolved_album = meta[0]
                self.metadata_cache.put_album_metadata(resolved_album)
                resolved_albums.append(resolved_album)
            else:
                resolved_albums.append(album)
        self._log_phase_elapsed("get_albums.resolve_loop", phase_started_at)

        print(
            f"[PERF][plex_client] get_albums.counts: "
            f"artist_rating_key={artist_rating_key} "
            f"albums={len(albums)} "
            f"child_payload_fast_path_count={child_payload_fast_path_count} "
            f"metadata_cache_hit_count={metadata_cache_hit_count} "
            f"fallback_full_metadata_count={fallback_full_metadata_count} "
            f"missing_rating_key_count={missing_rating_key_count}"
        )
        self._log_phase_elapsed("get_albums.total", total_started_at)

        return resolved_albums
    
    def get_artist_tracks(self, artist_rating_key):
        data = self._get(f"/library/metadata/{artist_rating_key}/allLeaves")
        return data.get("MediaContainer", {}).get("Metadata", [])

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

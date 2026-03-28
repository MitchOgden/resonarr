from typing import Dict, List, Optional, Tuple


def normalize_name(value) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = value.lower().strip()

    replacements = {
        "’": "'",
        "‘": "'",
        "‐": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "…": "...",
    }

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    cleaned = []
    for ch in value:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")

    value = "".join(cleaned)
    value = " ".join(value.split())
    return value


def build_lidarr_album_indexes(
    albums: List[dict],
) -> Tuple[Dict[str, dict], Dict[Tuple[str, str], List[dict]]]:
    by_mbid: Dict[str, dict] = {}
    by_name: Dict[Tuple[str, str], List[dict]] = {}

    for album in albums:
        foreign_album_id = album.get("foreignAlbumId")
        title = normalize_name(album.get("title", ""))

        artist = album.get("artist") or {}
        artist_name = normalize_name(artist.get("artistName", ""))

        if foreign_album_id:
            by_mbid[str(foreign_album_id).lower()] = album

        if artist_name and title:
            key = (artist_name, title)
            by_name.setdefault(key, []).append(album)

    return by_mbid, by_name


def fetch_lidarr_album(client, album_id: int) -> dict:
    resp = client.get(f"/api/v1/album/{album_id}")
    resp.raise_for_status()
    return resp.json()


def lidarr_album_track_count_candidates(album_obj: dict) -> List[int]:
    counts: List[int] = []

    statistics = album_obj.get("statistics") or {}
    stats_track_file_count = statistics.get("trackFileCount")
    if isinstance(stats_track_file_count, int) and stats_track_file_count >= 0:
        counts.append(stats_track_file_count)

    direct_track_file_count = album_obj.get("trackFileCount")
    if isinstance(direct_track_file_count, int) and direct_track_file_count >= 0:
        counts.append(direct_track_file_count)

    tracks = album_obj.get("tracks") or []
    if tracks:
        file_backed_tracks = 0

        for track in tracks:
            has_file = track.get("hasFile")
            track_file_id = track.get("trackFileId")

            if has_file is True:
                file_backed_tracks += 1
                continue

            if isinstance(track_file_id, int) and track_file_id > 0:
                file_backed_tracks += 1

        counts.append(file_backed_tracks)

    return sorted(set(counts))


def lidarr_album_has_registered_files(album_obj: dict) -> bool:
    statistics = album_obj.get("statistics") or {}
    stats_track_file_count = statistics.get("trackFileCount")
    if isinstance(stats_track_file_count, int) and stats_track_file_count > 0:
        return True

    direct_track_file_count = album_obj.get("trackFileCount")
    if isinstance(direct_track_file_count, int) and direct_track_file_count > 0:
        return True

    for track in album_obj.get("tracks") or []:
        track_file_id = track.get("trackFileId")
        has_file = track.get("hasFile")
        if has_file is True:
            return True
        if isinstance(track_file_id, int) and track_file_id > 0:
            return True

    return False


def verify_lidarr_album_candidate(prune_signal: dict, candidate: dict, client) -> Tuple[bool, str, dict]:
    album_id = candidate.get("id")
    if not isinstance(album_id, int):
        return False, "missing-album-id", candidate

    fresh = fetch_lidarr_album(client, album_id)

    plex_track_count = prune_signal.get("total_tracks_seen") or 0
    lidarr_track_counts = lidarr_album_track_count_candidates(fresh)
    if plex_track_count not in lidarr_track_counts:
        return (
            False,
            f"file-track-count-mismatch plex={plex_track_count} lidarr_file_counts={lidarr_track_counts}",
            fresh,
        )

    if not lidarr_album_has_registered_files(fresh):
        return False, "no-registered-files", fresh

    return True, "verified", fresh


def choose_best_name_fallback_candidate(
    prune_signal: dict,
    candidates: List[dict],
    client,
) -> Tuple[Optional[dict], str, dict]:
    diagnostics = {
        "name_match_found": False,
        "name_match_available_but_disabled": False,
        "name_match_type": None,
        "diagnostic_name_match_artist": None,
        "diagnostic_name_match_album": None,
        "name_candidate_count": len(candidates),
        "verification_reason": None,
        "verification_failures": [],
    }

    if not candidates:
        diagnostics["verification_reason"] = "no-name-candidates"
        return None, "no-name-candidates", diagnostics

    verified_matches: List[dict] = []

    for candidate in candidates:
        ok, reason, fresh = verify_lidarr_album_candidate(prune_signal, candidate, client)

        candidate_artist = (candidate.get("artist") or {}).get("artistName")
        candidate_album = candidate.get("title")

        diagnostics["verification_failures"].append({
            "album_id": candidate.get("id"),
            "artist_name": candidate_artist,
            "album_name": candidate_album,
            "reason": reason,
        })

        if ok:
            verified_matches.append(fresh)

    if len(verified_matches) == 1:
        match = verified_matches[0]
        artist = match.get("artist") or {}
        diagnostics["name_match_found"] = True
        diagnostics["name_match_type"] = "verified-exact"
        diagnostics["diagnostic_name_match_artist"] = artist.get("artistName")
        diagnostics["diagnostic_name_match_album"] = match.get("title")
        diagnostics["verification_reason"] = "verified"
        return match, "name+verified", diagnostics

    if len(verified_matches) > 1:
        diagnostics["verification_reason"] = "ambiguous-verified-candidates"
        return None, "ambiguous-verified-candidates", diagnostics

    if len(diagnostics["verification_failures"]) == 1:
        diagnostics["verification_reason"] = diagnostics["verification_failures"][0]["reason"]
    else:
        failure_reasons = sorted({
            item["reason"] for item in diagnostics["verification_failures"] if item.get("reason")
        })
        diagnostics["verification_reason"] = (
            "multiple-failures: " + "; ".join(failure_reasons)
            if failure_reasons else
            "no-verified-candidates"
        )

    return None, "no-verified-candidates", diagnostics


def match_album_to_lidarr(
    prune_signal: dict,
    lidarr_album_by_mbid: Dict[str, dict],
    lidarr_album_by_name: Dict[Tuple[str, str], List[dict]],
    client,
    match_mode: str = "mbid",
    allow_name_fallback: bool = False,
) -> Tuple[Optional[dict], str, dict]:
    artist_name = prune_signal.get("artist_name") or ""
    album_name = prune_signal.get("album_name") or ""
    album_mbid = prune_signal.get("album_mbid")

    diagnostics = {
        "has_album_mbid": bool(album_mbid),
        "mbid_match_found": False,
        "name_match_found": False,
        "name_match_available_but_disabled": False,
        "name_match_type": None,
        "diagnostic_name_match_artist": None,
        "diagnostic_name_match_album": None,
        "name_candidate_count": 0,
        "verification_reason": None,
    }

    if match_mode == "mbid":
        if album_mbid:
            match = lidarr_album_by_mbid.get(str(album_mbid).lower())
            if match:
                ok, reason, fresh = verify_lidarr_album_candidate(prune_signal, match, client)
                diagnostics["mbid_match_found"] = True
                diagnostics["verification_reason"] = reason
                if ok:
                    return fresh, "mbid+verified", diagnostics

        key = (normalize_name(artist_name), normalize_name(album_name))
        candidates = lidarr_album_by_name.get(key, [])

        match, method, name_diag = choose_best_name_fallback_candidate(
            prune_signal,
            candidates,
            client,
        )

        diagnostics.update(name_diag)

        if match:
            if allow_name_fallback:
                return match, method, diagnostics

            diagnostics["name_match_available_but_disabled"] = True
            return None, "unmatched", diagnostics

        return None, method, diagnostics

    key = (normalize_name(artist_name), normalize_name(album_name))
    candidates = lidarr_album_by_name.get(key, [])

    match, method, name_diag = choose_best_name_fallback_candidate(
        prune_signal,
        candidates,
        client,
    )
    diagnostics.update(name_diag)

    return (match, method, diagnostics) if match else (None, method, diagnostics)
def normalize_text(value):
    normalized = (
        (value or "")
        .lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("‐", "-")
        .replace("‒", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("…", "...")
        .replace("-", " ")
        .replace("_", " ")
        .replace(":", " ")
        .replace("/", " ")
        .strip()
    )
    return " ".join(normalized.split())


def build_lidarr_album_indexes(albums):
    by_mbid = {}
    by_exact_name = {}
    name_rows = []

    for album in albums:
        foreign_album_id = album.get("foreignAlbumId")
        if foreign_album_id:
            by_mbid[foreign_album_id] = album

        artist = album.get("artist") or {}
        artist_name = artist.get("artistName") or ""
        album_name = album.get("title") or ""

        normalized_artist = normalize_text(artist_name)
        normalized_album = normalize_text(album_name)

        by_exact_name[(normalized_artist, normalized_album)] = album
        name_rows.append({
            "artist_name": artist_name,
            "album_name": album_name,
            "normalized_artist": normalized_artist,
            "normalized_album": normalized_album,
            "album": album,
        })

    return by_mbid, by_exact_name, name_rows


def match_lidarr_album(artist_name, album_name, album_mbid, by_mbid, by_exact_name, name_rows):
    diagnostics = {
        "has_album_mbid": bool(album_mbid),
        "mbid_match_found": False,
        "name_match_found": False,
        "name_match_available_but_disabled": False,
        "diagnostic_name_match_artist": None,
        "diagnostic_name_match_album": None,
        "name_match_type": None,
    }

    if album_mbid:
        album = by_mbid.get(album_mbid)
        if album:
            diagnostics["mbid_match_found"] = True
            return album, "mbid", diagnostics

    normalized_artist = normalize_text(artist_name)
    normalized_album = normalize_text(album_name)

    exact = by_exact_name.get((normalized_artist, normalized_album))
    if exact:
        diagnostics["name_match_found"] = True
        diagnostics["name_match_type"] = "exact"
        exact_artist = exact.get("artist") or {}
        diagnostics["diagnostic_name_match_artist"] = exact_artist.get("artistName")
        diagnostics["diagnostic_name_match_album"] = exact.get("title")
        return exact, "name_exact", diagnostics

    for row in name_rows:
        artist_match = (
            normalized_artist == row["normalized_artist"]
            or normalized_artist in row["normalized_artist"]
            or row["normalized_artist"] in normalized_artist
        )
        album_match = (
            normalized_album == row["normalized_album"]
            or normalized_album in row["normalized_album"]
            or row["normalized_album"] in normalized_album
        )

        if artist_match and album_match:
            diagnostics["name_match_found"] = True
            diagnostics["name_match_type"] = "contains"
            diagnostics["diagnostic_name_match_artist"] = row["artist_name"]
            diagnostics["diagnostic_name_match_album"] = row["album_name"]
            return row["album"], "name_contains", diagnostics

    return None, "unmatched", diagnostics
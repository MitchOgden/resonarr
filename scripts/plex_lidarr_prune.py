#!/usr/bin/env python3
"""
Plex -> Lidarr pruning script
-----------------------------

What this script does
- Reads ratings from your Plex music library via PlexAPI.
- Scores albums from track ratings.
- Finds matching albums/artists in Lidarr (MBID first; optional name fallback).
- In DRY_RUN mode: logs what it *would* do.
- In live mode:
    1) unmonitors bad albums in Lidarr
    2) deletes the album in Lidarr with deleteFiles=true
    3) optionally deletes the artist if no albums remain

Design goals
- Conservative by default
- Very manageable: every setting lives at the top
- Heavy comments
- Dry-run first
- MBID-first matching

Notes
- Plex ratings are 0.0 to 10.0, where 0/2/4/6/8/10 map to 0..5 stars.
- This script treats <= 4.0 as "2 stars or lower".
- Track ratings are *kept* and used for scoring. This script does NOT delete tracks directly.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests
from plexapi.server import PlexServer


# =============================================================================
# CONFIGURATION
# =============================================================================

# --- Plex connection ----------------------------------------------------------
PLEX_URL = "http://10.3.12.20:32400"
PLEX_TOKEN = "vHMADgui6pgJAYTgtAwd"
PLEX_LIBRARY_NAME = "Music"

# --- Lidarr connection --------------------------------------------------------
LIDARR_URL = "http://10.3.12.20:8686"
LIDARR_API_KEY = "9a700cfa2ee34778a105fe2e9a8b8b43"

# --- Script safety ------------------------------------------------------------
# True  = log actions only, do not change Lidarr
# False = perform Lidarr changes
DRY_RUN = False

# --- Matching strategy --------------------------------------------------------
# Accepted values:
#   "mbid" = match Plex album/artist to Lidarr by MusicBrainz IDs first
#            (recommended; your requested mode)
MATCH_MODE = "mbid"

# If True, and MBID match is unavailable, try a normalized name fallback.
# If False, skip anything that does not have a usable MBID match.
ALLOW_NAME_FALLBACK = True

# --- Rating interpretation ----------------------------------------------------
# PlexAPI exposes ratings on a 0.0 - 10.0 scale.
# These thresholds convert that to star-style logic.
#
# <= TRACK_BAD_MAX_RATING  => "bad" signal (your <= 2-star rule)
# Current default 4.0 = 2 stars
TRACK_BAD_MAX_RATING = 4.0

# --- Album scoring ------------------------------------------------------------
# Minimum number of rated tracks required before an album is eligible for pruning.
# Recommended conservative range: 3 - 8
MIN_TRACKS_RATED = 5

# Fraction of rated tracks that must be "bad" before the album is pruned.
# 0.50 = 50%
# Conservative range: 0.50 - 0.70
ALBUM_BAD_RATIO = 0.50

# How to treat unrated tracks:
# "ignore"  = current behavior (only rated tracks count)
# "neutral" = treat unrated tracks as "not bad" (recommended)
UNRATED_TRACK_STRATEGY = "neutral"

# --- Small album handling ----------------------------------------------------
# If True:
#   Albums with fewer than MIN_TRACKS_RATED tracks will still be pruned
#   IF all rated tracks are "bad"
#
# Example:
#   3-track EP, all rated ≤2★ → pruned
#   1-track single rated ≤2★ → pruned
#
# If False:
#   Small albums are ignored entirely (original behavior)
ALLOW_SMALL_ALBUM_FULL_REJECT = True

# --- Artist pruning -----------------------------------------------------------
# You asked for:
#   "if we score all their albums bad or they have none left... like on the last
#    delete and none left then you can prune them."
#
# This script implements the simplest, strictest version:
#   after album deletions, if the artist has zero albums left in Lidarr, prune artist
ENABLE_ARTIST_PRUNE = True

# Safety delay between destructive requests, in seconds.
# Helps keep logs readable and API usage gentler.
REQUEST_DELAY_SECONDS = 0.25

# --- Logging -----------------------------------------------------------------
# Accepted values: "DEBUG", "INFO", "WARNING", "ERROR"
LOG_LEVEL = "INFO"
SCRIPT_VERSION = "2026-03-19 neutral-v1"

# =============================================================================
# IMPLEMENTATION
# =============================================================================

HEADERS = {
    "X-Api-Key": LIDARR_API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json",
}


@dataclass
class PlexAlbumScore:
    artist_name: str
    album_name: str
    album_rating_key: str
    album_guids: List[str] = field(default_factory=list)
    artist_guids: List[str] = field(default_factory=list)
    rated_tracks: int = 0
    bad_tracks: int = 0
    total_tracks_seen: int = 0

    @property
    def bad_ratio(self) -> float:
        if self.rated_tracks == 0:
            return 0.0
        return self.bad_tracks / self.rated_tracks

    @property
    def eligible(self) -> bool:
        return self.rated_tracks >= MIN_TRACKS_RATED

    @property
    def should_prune(self) -> bool:
        return self.eligible and self.bad_ratio >= ALBUM_BAD_RATIO


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def normalize_name(value) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value)
    return value


def extract_musicbrainz_id(guid_strings: List[str]) -> Optional[str]:
    """
    Best-effort extraction from Plex GUID strings.

    Plex exposes a list of guid objects, but exact providers can vary by library
    and agent. This function looks for strings that appear to carry a MusicBrainz ID.
    """
    for raw in guid_strings:
        g = (raw or "").strip().lower()
        # Examples encountered in ecosystems can include provider-prefixed forms.
        if "musicbrainz" in g or "mbid" in g:
            # keep the actual terminal identifier after the last separator if present
            parts = re.split(r"[:/]", raw)
            if parts:
                candidate = parts[-1].strip()
                if candidate:
                    return candidate
    return None


def plex_item_guid_strings(item) -> List[str]:
    """
    PlexAPI audio objects expose .guids as a list of Guid objects.
    Convert those to plain strings defensively.

    Some Plex items may 404 on reload when guids are accessed.
    In that case, return what we can and keep the run going.
    """
    results: List[str] = []

    try:
        for g in getattr(item, "guids", []) or []:
            val = getattr(g, "id", None)
            if val:
                results.append(str(val))
    except Exception as exc:
        logging.warning("Could not read Plex guids for item %s: %s", getattr(item, "title", "Unknown Item"), exc)

    try:
        direct_guid = getattr(item, "guid", None)
        if direct_guid:
            results.append(str(direct_guid))
    except Exception as exc:
        logging.warning("Could not read direct Plex guid for item %s: %s", getattr(item, "title", "Unknown Item"), exc)

    return list(dict.fromkeys(results))


def plex_rating_is_bad(user_rating: Optional[float]) -> bool:
    if user_rating is None:
        return False
    return float(user_rating) <= TRACK_BAD_MAX_RATING


def connect_plex() -> PlexServer:
    logging.info("Connecting to Plex: %s", PLEX_URL)
    return PlexServer(PLEX_URL, PLEX_TOKEN)


def get_music_library(plex: PlexServer):
    logging.info("Loading Plex library section: %s", PLEX_LIBRARY_NAME)
    return plex.library.section(PLEX_LIBRARY_NAME)

def rescan_plex_music_library(music_section) -> None:
    """
    Trigger a Plex scan of the configured music library so removals are reflected
    to Plex/Plexamp clients.
    """
    if DRY_RUN:
        logging.info("[DRY RUN] Would trigger Plex library scan for section: %s", PLEX_LIBRARY_NAME)
        return

    music_section.update()
    logging.info("Triggered Plex library scan for section: %s", PLEX_LIBRARY_NAME)

def build_album_scores(music_section) -> List[PlexAlbumScore]:
    """
    Iterate Plex albums, then tracks, and build album-level scores from track ratings.
    """
    logging.info("Reading albums from Plex library...")
    album_scores: List[PlexAlbumScore] = []

    albums = music_section.albums()
    total_albums = len(albums)
    logging.info(f"Found {total_albums} albums")

    for idx, album in enumerate(albums, start=1):
        artist_name_preview = getattr(album, "parentTitle", "Unknown Artist")
        album_name_preview = getattr(album, "title", "Unknown Album")

        if idx == 1 or idx % 10 == 0:
            logging.info(f"[{idx}/{total_albums}] Processing: {artist_name_preview} - {album_name_preview}")

        artist_name = getattr(album, "parentTitle", None)

        if not artist_name:
            try:
                artist_obj = album.artist()
                artist_name = getattr(artist_obj, "title", None)
            except Exception:
                artist_name = None

        artist_name = str(artist_name or "Unknown Artist")
        album_name = str(getattr(album, "title", "Unknown Album"))

        score = PlexAlbumScore(
            artist_name=artist_name,
            album_name=album_name,
            album_rating_key=str(getattr(album, "ratingKey", "")),
            album_guids=plex_item_guid_strings(album),
        )

        try:
            artist_obj = album.artist()
            score.artist_guids = plex_item_guid_strings(artist_obj)
        except Exception:
            score.artist_guids = []

        try:
            tracks = album.tracks()
        except Exception as exc:
            logging.warning("Could not load tracks for %s - %s: %s", artist_name, album_name, exc)
            continue

        album_user_rating = getattr(album, "userRating", None)

        # --- FIXED TRACK LOOP (correct indentation) ---
        for track in tracks:
            score.total_tracks_seen += 1
            track_user_rating = getattr(track, "userRating", None)

            # Rule:
            # 1. Track rating wins
            # 2. If track is unrated, inherit album rating
            # 3. If neither exists, fall back to unrated strategy
            if track_user_rating is not None:
                user_rating = track_user_rating
                rating_source = "track"
            elif album_user_rating is not None:
                user_rating = album_user_rating
                rating_source = "album-fallback"
            else:
                user_rating = None
                rating_source = "none"

            action = "ignored"

            # Unrated handling (only when neither track nor album rating exists)
            if user_rating is None:
                if UNRATED_TRACK_STRATEGY == "ignore":
                    action = "unrated-ignored"
                elif UNRATED_TRACK_STRATEGY == "neutral":
                    score.rated_tracks += 1
                    action = "unrated-counted-neutral"
                else:
                    action = "unrated-unknown-strategy"
            else:
                # Rated track (direct track rating OR inherited album rating)
                score.rated_tracks += 1
                if plex_rating_is_bad(user_rating):
                    score.bad_tracks += 1
                    action = f"{rating_source}-rated-bad"
                else:
                    action = f"{rating_source}-rated-not-bad"

            logging.debug(
                "Track score | %s - %s | track=%s | track_userRating=%s | album_userRating=%s | effective_userRating=%s | action=%s | total_tracks=%d | rated_tracks=%d | bad_tracks=%d",
                artist_name,
                album_name,
                getattr(track, "title", "Unknown Track"),
                track_user_rating,
                album_user_rating,
                user_rating,
                action,
                score.total_tracks_seen,
                score.rated_tracks,
                score.bad_tracks,
            )

        # IMPORTANT: append happens AFTER processing all tracks

        logging.info(
            "Album scored | %s - %s | total_tracks=%d | rated=%d | bad=%d | ratio=%.2f",
            score.artist_name,
            score.album_name,
            score.total_tracks_seen,
            score.rated_tracks,
            score.bad_tracks,
            score.bad_ratio,
        )

        album_scores.append(score)

    # IMPORTANT: return happens AFTER processing ALL albums
    return album_scores


def lidarr_get(path: str, params: Optional[dict] = None):
    url = f"{LIDARR_URL}{path}"
    response = requests.get(url, headers=HEADERS, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def lidarr_put(path: str, payload: dict):
    url = f"{LIDARR_URL}{path}"
    response = requests.put(url, headers=HEADERS, json=payload, timeout=60)
    response.raise_for_status()
    return response.json() if response.text.strip() else None


def lidarr_delete(path: str, params: Optional[dict] = None):
    url = f"{LIDARR_URL}{path}"
    response = requests.delete(url, headers=HEADERS, params=params, timeout=60)
    response.raise_for_status()
    return response.json() if response.text.strip() else None


def fetch_lidarr_albums() -> List[dict]:
    logging.info("Fetching albums from Lidarr...")
    return lidarr_get("/api/v1/album")


def fetch_lidarr_artists() -> List[dict]:
    logging.info("Fetching artists from Lidarr...")
    return lidarr_get("/api/v1/artist")

def fetch_lidarr_album(album_id: int) -> dict:
    """
    Fetch one fresh Lidarr album object by numeric album id.
    Used for robust candidate verification before destructive actions.
    """
    return lidarr_get(f"/api/v1/album/{album_id}")    


def index_lidarr_albums(albums: List[dict]) -> Tuple[Dict[str, dict], Dict[Tuple[str, str], List[dict]]]:
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


def index_lidarr_artists(artists: List[dict]) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    by_mbid: Dict[str, dict] = {}
    by_name: Dict[str, dict] = {}

    for artist in artists:
        foreign_artist_id = artist.get("foreignArtistId")
        artist_name = artist.get("artistName", "")

        if foreign_artist_id:
            by_mbid[str(foreign_artist_id).lower()] = artist

        if artist_name:
            by_name[normalize_name(artist_name)] = artist

    return by_mbid, by_name

def lidarr_album_track_count_candidates(album_obj: dict) -> List[int]:
    """
    Collect plausible track counts from album and release data.
    """
    counts: List[int] = []

    direct_track_count = album_obj.get("trackCount")
    if isinstance(direct_track_count, int) and direct_track_count > 0:
        counts.append(direct_track_count)

    for release in album_obj.get("releases") or []:
        track_count = release.get("trackCount")
        if isinstance(track_count, int) and track_count > 0:
            counts.append(track_count)

    return sorted(set(counts))


def lidarr_album_has_registered_files(album_obj: dict) -> bool:
    """
    Best-effort check that Lidarr knows about actual files for the album's tracks.

    Lidarr album payloads can vary by endpoint/version. We inspect common places:
    - album['statistics']['trackFileCount']
    - album['trackFileCount']
    - track entries carrying trackFileId / hasFile
    """
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


def verify_lidarr_album_candidate(score: PlexAlbumScore, candidate: dict) -> Tuple[bool, str, dict]:
    """
    Fetch a fresh album object and verify:
    1. Plex total track count matches one of Lidarr's album/release track counts
    2. Lidarr shows actual files registered to the album

    Returns:
        (is_valid, reason, fresh_album_obj)
    """
    album_id = candidate.get("id")
    if not isinstance(album_id, int):
        return False, "missing-album-id", candidate

    fresh = fetch_lidarr_album(album_id)

    plex_track_count = score.total_tracks_seen
    lidarr_track_counts = lidarr_album_track_count_candidates(fresh)
    if plex_track_count not in lidarr_track_counts:
        return False, f"track-count-mismatch plex={plex_track_count} lidarr={lidarr_track_counts}", fresh

    if not lidarr_album_has_registered_files(fresh):
        return False, "no-registered-files", fresh

    return True, "verified", fresh


def choose_best_name_fallback_candidate(score: PlexAlbumScore, candidates: List[dict]) -> Tuple[Optional[dict], str]:
    """
    Verify every same-name candidate with fresh Lidarr data.
    Accept only one verified candidate.
    Skip ambiguous or unverified sets.
    """
    if not candidates:
        return None, "no-name-candidates"

    verified_matches: List[dict] = []

    for candidate in candidates:
        ok, reason, fresh = verify_lidarr_album_candidate(score, candidate)
        logging.info(
            "Candidate verification | Plex=%s - %s | Lidarr id=%s | foreignAlbumId=%s | reason=%s",
            score.artist_name,
            score.album_name,
            fresh.get("id"),
            fresh.get("foreignAlbumId"),
            reason,
        )
        if ok:
            verified_matches.append(fresh)

    if len(verified_matches) == 1:
        return verified_matches[0], "name+verified"

    if len(verified_matches) > 1:
        return None, "ambiguous-verified-candidates"

    return None, "no-verified-candidates"

def match_album_to_lidarr(
    score: PlexAlbumScore,
    lidarr_album_by_mbid: Dict[str, dict],
    lidarr_album_by_name: Dict[Tuple[str, str], List[dict]],
) -> Tuple[Optional[dict], str]:
    """
    Returns (album_object_or_none, match_method)

    Matching priority:
    1. MBID exact match
    2. artist+album fallback with verification
    3. skip ambiguous/unverified candidates
    """
    plex_album_mbid = extract_musicbrainz_id(score.album_guids)

    if MATCH_MODE == "mbid":
        if plex_album_mbid:
            match = lidarr_album_by_mbid.get(plex_album_mbid.lower())
            if match:
                ok, reason, fresh = verify_lidarr_album_candidate(score, match)
                logging.info(
                    "MBID verification | Plex=%s - %s | plex_mbid=%s | Lidarr id=%s | foreignAlbumId=%s | result=%s",
                    score.artist_name,
                    score.album_name,
                    plex_album_mbid,
                    fresh.get("id"),
                    fresh.get("foreignAlbumId"),
                    reason,
                )
                if ok:
                    return fresh, "mbid+verified"

        if ALLOW_NAME_FALLBACK:
            key = (normalize_name(score.artist_name), normalize_name(score.album_name))
            candidates = lidarr_album_by_name.get(key, [])
            match, method = choose_best_name_fallback_candidate(score, candidates)
            if match:
                return match, method
            return None, method

        return None, "no-match"

    key = (normalize_name(score.artist_name), normalize_name(score.album_name))
    candidates = lidarr_album_by_name.get(key, [])
    match, method = choose_best_name_fallback_candidate(score, candidates)
    return (match, method) if match else (None, method)


def match_artist_to_lidarr(
    artist_name: str,
    artist_guid_strings: List[str],
    lidarr_artist_by_mbid: Dict[str, dict],
    lidarr_artist_by_name: Dict[str, dict],
) -> Tuple[Optional[dict], str]:
    if MATCH_MODE == "mbid":
        plex_artist_mbid = extract_musicbrainz_id(artist_guid_strings)
        if plex_artist_mbid:
            match = lidarr_artist_by_mbid.get(plex_artist_mbid.lower())
            if match:
                return match, "mbid"

        if ALLOW_NAME_FALLBACK:
            match = lidarr_artist_by_name.get(normalize_name(artist_name))
            if match:
                return match, "name-fallback"

        return None, "no-match"

    match = lidarr_artist_by_name.get(normalize_name(artist_name))
    return (match, "name") if match else (None, "no-match")


def unmonitor_album(album_obj: dict) -> None:
    """
    Uses standard album update pattern:
    GET album object -> set monitored false -> PUT album/{id}
    """
    album_id = album_obj["id"]
    fresh_album = lidarr_get(f"/api/v1/album/{album_id}")
    fresh_album["monitored"] = False

    if DRY_RUN:
        logging.info("[DRY RUN] Would unmonitor album: %s (id=%s)", fresh_album.get("title"), album_id)
        return

    lidarr_put(f"/api/v1/album/{album_id}", fresh_album)
    logging.info("Unmonitored album: %s (id=%s)", fresh_album.get("title"), album_id)
    time.sleep(REQUEST_DELAY_SECONDS)


def delete_album(album_obj: dict) -> None:
    """
    Deletes album and files.
    """
    album_id = album_obj["id"]
    title = album_obj.get("title", "Unknown Album")

    if DRY_RUN:
        logging.info("[DRY RUN] Would delete album+files: %s (id=%s)", title, album_id)
        return

    lidarr_delete(f"/api/v1/album/{album_id}", params={"deleteFiles": "true"})
    logging.info("Deleted album+files: %s (id=%s)", title, album_id)
    time.sleep(REQUEST_DELAY_SECONDS)


def delete_artist(artist_obj: dict) -> None:
    artist_id = artist_obj["id"]
    artist_name = artist_obj.get("artistName", "Unknown Artist")

    if DRY_RUN:
        logging.info("[DRY RUN] Would delete artist+files: %s (id=%s)", artist_name, artist_id)
        return

    lidarr_delete(f"/api/v1/artist/{artist_id}", params={"deleteFiles": "true"})
    logging.info("Deleted artist+files: %s (id=%s)", artist_name, artist_id)
    time.sleep(REQUEST_DELAY_SECONDS)


def artist_has_any_albums_remaining(artist_id: int) -> bool:
    albums = lidarr_get("/api/v1/album")
    for album in albums:
        artist = album.get("artist") or {}
        if artist.get("id") == artist_id:
            return True
    return False


def main() -> int:
    setup_logging()

    logging.info("==== Plex/Lidarr pruning run started ====")
    logging.info("DRY_RUN=%s | MATCH_MODE=%s | ALLOW_NAME_FALLBACK=%s", DRY_RUN, MATCH_MODE, ALLOW_NAME_FALLBACK)
    logging.info("SCRIPT_VERSION=%s", SCRIPT_VERSION)
    logging.info(
        "CONFIG | DRY_RUN=%s | UNRATED_TRACK_STRATEGY=%s | MIN_TRACKS_RATED=%s | ALBUM_BAD_RATIO=%s | ALLOW_SMALL_ALBUM_FULL_REJECT=%s",
        DRY_RUN,
        UNRATED_TRACK_STRATEGY,
        MIN_TRACKS_RATED,
        ALBUM_BAD_RATIO,
        ALLOW_SMALL_ALBUM_FULL_REJECT,
    )

    # Connect to Plex and build album scores
    plex = connect_plex()
    music = get_music_library(plex)
    album_scores = build_album_scores(music)
    logging.info("Built album scores for %d Plex albums", len(album_scores))

    # Load Lidarr state once up front
    lidarr_albums = fetch_lidarr_albums()
    lidarr_artists = fetch_lidarr_artists()

    lidarr_album_by_mbid, lidarr_album_by_name = index_lidarr_albums(lidarr_albums)
    lidarr_artist_by_mbid, lidarr_artist_by_name = index_lidarr_artists(lidarr_artists)

    artists_touched: Dict[str, List[int]] = {}
    albums_pruned = 0
    albums_skipped = 0
    albums_unmatched = 0

    for score in album_scores:
        logging.debug(
            "Album score | %s - %s | rated=%d bad=%d ratio=%.2f eligible=%s prune=%s",
            score.artist_name,
            score.album_name,
            score.rated_tracks,
            score.bad_tracks,
            score.bad_ratio,
            score.eligible,
            score.should_prune,
        )

        # --- Album pruning decision logic -------------------------------------------

        prune_album = False

        if score.eligible:
            # Standard rule (normal albums)
            if score.bad_ratio >= ALBUM_BAD_RATIO:
                prune_album = True
        else:
            # Small album rule
            if ALLOW_SMALL_ALBUM_FULL_REJECT:
                if score.rated_tracks >= 1 and score.bad_ratio == 1.0:
                    prune_album = True

        if not prune_album:
            albums_skipped += 1
            continue

        lidarr_album, match_method = match_album_to_lidarr(score, lidarr_album_by_mbid, lidarr_album_by_name)
        if not lidarr_album:
            albums_unmatched += 1
            logging.warning(
                "No Lidarr album match for %s - %s (match=%s)",
                score.artist_name,
                score.album_name,
                match_method,
            )
            continue

        logging.info(
            "Prune candidate | %s - %s | rated=%d bad=%d ratio=%.2f | Lidarr match=%s | Lidarr id=%s | foreignAlbumId=%s | plex_tracks=%d | lidarr_track_counts=%s | has_files=%s",
            score.artist_name,
            score.album_name,
            score.rated_tracks,
            score.bad_tracks,
            score.bad_ratio,
            match_method,
            lidarr_album.get("id"),
            lidarr_album.get("foreignAlbumId"),
            score.total_tracks_seen,
            lidarr_album_track_count_candidates(lidarr_album),
            lidarr_album_has_registered_files(lidarr_album),
        )

        # Action = unmonitor + delete
        unmonitor_album(lidarr_album)
        delete_album(lidarr_album)
        albums_pruned += 1

        # Track artist for follow-up pruning.
        artists_touched.setdefault(score.artist_name, [])
        lidarr_artist = lidarr_album.get("artist") or {}
        artist_id = lidarr_artist.get("id")
        if artist_id is not None:
            artists_touched[score.artist_name].append(int(artist_id))

    artists_pruned = 0

    if ENABLE_ARTIST_PRUNE:
        # Deduplicate artist ids gathered during album pruning
        unique_artist_ids = {aid for ids in artists_touched.values() for aid in ids}

        for artist_id in sorted(unique_artist_ids):
            # Reload artist object from current Lidarr state
            matching_artist = None
            for artist in fetch_lidarr_artists():
                if artist.get("id") == artist_id:
                    matching_artist = artist
                    break

            if not matching_artist:
                continue

            remaining = artist_has_any_albums_remaining(artist_id)
            if remaining:
                logging.info(
                    "Artist retained because albums still remain: %s (id=%s)",
                    matching_artist.get("artistName"),
                    artist_id,
                )
                continue

            logging.info(
                "Artist prune candidate because no albums remain: %s (id=%s)",
                matching_artist.get("artistName"),
                artist_id,
            )
            delete_artist(matching_artist)
            artists_pruned += 1

    # Trigger Plex scan so deletions propagate into Plex/Plexamp visibility
    rescan_plex_music_library(music)

    logging.info("==== Run summary ====")
    logging.info("Albums scored: %d", len(album_scores))
    logging.info("Albums pruned: %d", albums_pruned)
    logging.info("Albums skipped: %d", albums_skipped)
    logging.info("Albums unmatched: %d", albums_unmatched)
    logging.info("Artists pruned: %d", artists_pruned)
    logging.info("==== Plex/Lidarr pruning run complete ====")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        raise SystemExit(130)
    except requests.HTTPError as exc:
        logging.exception("HTTP error while talking to Lidarr/Plex: %s", exc)
        raise SystemExit(2)
    except Exception as exc:
        logging.exception("Unhandled error: %s", exc)
        raise SystemExit(1)
# src/resonarr/config/settings.py

import os

LIDARR_URL = os.getenv("LIDARR_URL")
LIDARR_API_KEY = os.getenv("LIDARR_API_KEY")

ROOT_FOLDER = os.getenv("LIDARR_ROOT_FOLDER", "/volume1/music/library")

QUALITY_PROFILE_NAME = os.getenv("LIDARR_QUALITY_PROFILE", "Lossless")
METADATA_PROFILE_NAME = os.getenv("LIDARR_METADATA_PROFILE", "Standard")

# --- Policy (MVP) ---

ACQUIRE_SCORE_THRESHOLD = int(os.getenv("RESONARR_ACQUIRE_THRESHOLD", 10))
RECOMMEND_SCORE_THRESHOLD = int(os.getenv("RESONARR_RECOMMEND_THRESHOLD", 2))

# --- Cooldown (MVP) ---

ARTIST_COOLDOWN_HOURS = int(os.getenv("RESONARR_ARTIST_COOLDOWN_HOURS", 24))

# --- Plex ---

PLEX_BASE_URL = os.getenv("PLEX_BASE_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
PLEX_MUSIC_LIBRARY = os.getenv("PLEX_MUSIC_LIBRARY", "Music")

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
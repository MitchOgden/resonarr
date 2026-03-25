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
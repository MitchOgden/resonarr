def _raw(item):
    return item.get("raw", item)


def _prefer(item, key, raw_key=None, default=None):
    value = item.get(key)
    if value is not None:
        return value

    raw = _raw(item)
    if raw_key is not None:
        return raw.get(raw_key, default)

    return default


def build_extend_review_card(item):
    raw = _raw(item)

    return {
        "kind": _prefer(item, "kind", default="extend_review"),
        "source": _prefer(item, "source", default="extend"),
        "status": _prefer(item, "status"),
        "live": _prefer(item, "live", default=True),
        "historical": _prefer(item, "historical", default=False),
        "artist_name": _prefer(item, "artist_name"),
        "artist_mbid": _prefer(item, "artist_mbid", "resolved_artist_mbid"),
        "album_title": _prefer(item, "album_title", "starter_album_title"),
        "album_id": _prefer(item, "album_id", "starter_album_id"),
        "score": _prefer(item, "score", "starter_album_score"),
        "reason": _prefer(item, "reason", "starter_album_reason"),
        "event_ts": _prefer(item, "event_ts"),
        "seed_count": raw.get("seed_count"),
        "seen_count": raw.get("seen_count"),
    }


def build_extend_promotable_card(item):
    raw = _raw(item)

    return {
        "kind": _prefer(item, "kind", default="extend_promotable"),
        "source": _prefer(item, "source", default="extend"),
        "status": _prefer(item, "status"),
        "live": _prefer(item, "live", default=True),
        "historical": _prefer(item, "historical", default=False),
        "artist_name": _prefer(item, "artist_name"),
        "artist_mbid": _prefer(item, "artist_mbid", "resolved_artist_mbid"),
        "album_title": _prefer(item, "album_title", "starter_album_title"),
        "album_id": _prefer(item, "album_id", "starter_album_id"),
        "score": _prefer(item, "score", "best_match_score"),
        "reason": _prefer(item, "reason", "starter_album_reason"),
        "event_ts": _prefer(item, "event_ts"),
        "seed_count": raw.get("seed_count"),
        "seen_count": raw.get("seen_count"),
        "source_seeds": raw.get("source_seeds", []),
        "in_recommendation_backoff": raw.get("in_recommendation_backoff"),
        "is_promotable": raw.get("is_promotable"),
    }


def build_deepen_candidate_card(item):
    raw = _raw(item)

    return {
        "kind": _prefer(item, "kind", default="deepen_candidate"),
        "source": _prefer(item, "source", default="deepen"),
        "status": _prefer(item, "status", default="candidate"),
        "live": _prefer(item, "live", default=True),
        "historical": _prefer(item, "historical", default=False),
        "artist_name": _prefer(item, "artist_name"),
        "artist_mbid": _prefer(item, "artist_mbid", "mbid"),
        "album_title": _prefer(item, "album_title"),
        "album_id": _prefer(item, "album_id"),
        "score": _prefer(item, "score", "lastfm_playcount"),
        "reason": _prefer(item, "reason", "suppression_reason"),
        "event_ts": _prefer(item, "event_ts"),
        "lastfm_playcount": raw.get("lastfm_playcount"),
        "partial_present": raw.get("partial_present"),
        "eligible_album_count": raw.get("eligible_album_count"),
        "fully_owned": raw.get("fully_owned"),
        "in_cooldown": raw.get("in_cooldown"),
        "in_recommendation_backoff": raw.get("in_recommendation_backoff"),
        "is_suppressed": raw.get("is_suppressed"),
    }


def build_suppressed_artist_card(item):
    return {
        "kind": _prefer(item, "kind", default="suppressed_artist"),
        "source": _prefer(item, "source", default="suppression"),
        "status": _prefer(item, "status", default="suppressed"),
        "live": _prefer(item, "live", default=True),
        "historical": _prefer(item, "historical", default=False),
        "artist_name": _prefer(item, "artist_name"),
        "artist_mbid": _prefer(item, "artist_mbid"),
        "album_title": _prefer(item, "album_title"),
        "album_id": _prefer(item, "album_id"),
        "score": _prefer(item, "score"),
        "reason": _prefer(item, "reason", "suppression_reason"),
        "event_ts": _prefer(item, "event_ts", "suppressed_ts"),
        "suppressed_ts": _prefer(item, "event_ts", "suppressed_ts"),
    }


def build_prune_candidate_card(item):
    raw = _raw(item)

    return {
        "kind": _prefer(item, "kind", default="prune_candidate"),
        "source": _prefer(item, "source", default="prune"),
        "status": _prefer(item, "status"),
        "live": _prefer(item, "live", default=True),
        "historical": _prefer(item, "historical", default=False),
        "artist_name": _prefer(item, "artist_name"),
        "artist_mbid": _prefer(item, "artist_mbid"),
        "album_title": _prefer(item, "album_title", "album_name"),
        "album_id": _prefer(item, "album_id", "lidarr_album_id"),
        "score": _prefer(item, "score", "bad_ratio"),
        "reason": _prefer(item, "reason"),
        "event_ts": _prefer(item, "event_ts", "last_seen_ts"),
        "rated_tracks": raw.get("rated_tracks"),
        "bad_tracks": raw.get("bad_tracks"),
        "total_tracks_seen": raw.get("total_tracks_seen"),
        "match_method": raw.get("match_method"),
        "matched": raw.get("matched"),
        "lidarr_has_files": raw.get("lidarr_has_files"),
    }

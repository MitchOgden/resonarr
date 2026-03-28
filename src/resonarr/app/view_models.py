def build_extend_review_card(item):
    return {
        "kind": "extend_review",
        "artist_name": item.get("artist_name"),
        "artist_mbid": item.get("resolved_artist_mbid"),
        "status": item.get("status"),
        "album_title": item.get("starter_album_title"),
        "album_id": item.get("starter_album_id"),
        "score": item.get("starter_album_score"),
        "reason": item.get("starter_album_reason"),
        "seed_count": item.get("seed_count"),
        "seen_count": item.get("seen_count"),
    }


def build_extend_promotable_card(item):
    return {
        "kind": "extend_promotable",
        "artist_name": item.get("artist_name"),
        "artist_mbid": item.get("resolved_artist_mbid"),
        "status": item.get("status"),
        "album_title": item.get("starter_album_title"),
        "album_id": item.get("starter_album_id"),
        "score": item.get("best_match_score"),
        "reason": item.get("starter_album_reason"),
        "seed_count": item.get("seed_count"),
        "seen_count": item.get("seen_count"),
        "source_seeds": item.get("source_seeds", []),
        "in_recommendation_backoff": item.get("in_recommendation_backoff"),
        "is_promotable": item.get("is_promotable"),
    }


def build_deepen_candidate_card(item):
    return {
        "kind": "deepen_candidate",
        "artist_name": item.get("artist_name"),
        "artist_mbid": item.get("mbid"),
        "status": "candidate",
        "album_title": None,
        "album_id": None,
        "score": None,
        "reason": None,
        "lastfm_playcount": item.get("lastfm_playcount"),
        "partial_present": item.get("partial_present"),
        "eligible_album_count": item.get("eligible_album_count"),
        "fully_owned": item.get("fully_owned"),
        "in_cooldown": item.get("in_cooldown"),
        "in_recommendation_backoff": item.get("in_recommendation_backoff"),
        "is_suppressed": item.get("is_suppressed"),
    }


def build_suppressed_artist_card(item):
    artist_key = item.get("artist_key")
    artist_mbid = artist_key if artist_key and ":" not in artist_key else None

    return {
        "kind": "suppressed_artist",
        "artist_name": item.get("artist_name"),
        "artist_mbid": artist_mbid,
        "status": "suppressed",
        "album_title": None,
        "album_id": None,
        "score": None,
        "reason": item.get("suppression_reason"),
        "suppressed_ts": item.get("suppressed_ts"),
    }
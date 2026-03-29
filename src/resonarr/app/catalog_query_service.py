from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.app.deepen_operator_service import DeepenOperatorService
from resonarr.app.deepen_service import DeepenService
from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.app.prune_query_service import PruneQueryService


class CatalogQueryService:
    def __init__(
        self,
        extend_query_service=None,
        extend_operator_service=None,
        extend_promotion_service=None,
        deepen_service=None,
        deepen_operator_service=None,
        prune_query_service=None,
        prune_operator_service=None,
    ):
        self.extend_query_service = extend_query_service or ExtendQueryService()
        self.extend_operator_service = extend_operator_service or ExtendOperatorService()
        self.extend_promotion_service = extend_promotion_service or ExtendPromotionService()
        self.deepen_service = deepen_service or DeepenService()
        self.deepen_operator_service = deepen_operator_service or DeepenOperatorService()
        self.prune_query_service = prune_query_service or PruneQueryService()
        self.prune_operator_service = prune_operator_service or PruneOperatorService()

    def _normalize_extend_review(self, item):
        return {
            "kind": "extend_review",
            "source": "extend",
            "status": item.get("status"),
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("resolved_artist_mbid"),
            "album_title": item.get("starter_album_title"),
            "album_id": item.get("starter_album_id"),
            "score": item.get("starter_album_score"),
            "reason": item.get("starter_album_reason"),
            "event_ts": None,
            "raw": item,
        }

    def _normalize_extend_promotable(self, item):
        return {
            "kind": "extend_promotable",
            "source": "extend",
            "status": item.get("status"),
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("resolved_artist_mbid"),
            "album_title": item.get("starter_album_title"),
            "album_id": item.get("starter_album_id"),
            "score": item.get("best_match_score"),
            "reason": item.get("starter_album_reason"),
            "event_ts": None,
            "raw": item,
        }

    def _build_extend_review_key_set(self, extend_review_items):
        keys = set()

        for item in extend_review_items:
            artist_mbid = (item.get("resolved_artist_mbid") or "").strip().lower()
            album_id = item.get("starter_album_id")

            if artist_mbid and album_id is not None:
                keys.add((artist_mbid, album_id))

        return keys

    def _normalize_deepen_candidate(self, item):
        return {
            "kind": "deepen_candidate",
            "source": "deepen",
            "status": item.get("status") or "candidate",
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("mbid"),
            "album_title": None,
            "album_id": None,
            "score": item.get("lastfm_playcount"),
            "reason": item.get("suppression_reason"),
            "event_ts": None,
            "raw": item,
        }

    def _normalize_deepen_review(self, item):
        return {
            "kind": "deepen_review",
            "source": "deepen",
            "status": item.get("status"),
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("mbid"),
            "album_title": None,
            "album_id": None,
            "score": item.get("lastfm_playcount"),
            "reason": item.get("suppression_reason"),
            "event_ts": None,
            "raw": item,
        }
    
    def _build_deepen_review_mbid_set(self, deepen_review_items):
        mbids = set()

        for item in deepen_review_items:
            mbid = (item.get("mbid") or "").strip().lower()
            if mbid:
                mbids.add(mbid)

        return mbids

    def _normalize_prune_live(self, item):
        return {
            "kind": "prune_candidate",
            "source": "prune",
            "status": item.get("status"),
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("artist_mbid"),
            "album_title": item.get("album_name"),
            "album_id": item.get("lidarr_album_id"),
            "score": item.get("bad_ratio"),
            "reason": item.get("reason"),
            "event_ts": item.get("last_seen_ts") or item.get("first_seen_ts"),
            "raw": item,
        }

    def _normalize_prune_history(self, item):
        event_ts = (
            item.get("prune_executed_ts")
            or item.get("prune_rejected_ts")
            or item.get("prune_approved_ts")
            or item.get("last_seen_ts")
            or item.get("first_seen_ts")
        )

        return {
            "kind": "prune_history",
            "source": "prune",
            "status": item.get("status"),
            "live": False,
            "historical": True,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("artist_mbid"),
            "album_title": item.get("album_name"),
            "album_id": item.get("lidarr_album_id"),
            "score": item.get("bad_ratio"),
            "reason": item.get("reason"),
            "event_ts": event_ts,
            "raw": item,
        }

    def _normalize_suppressed_artist(self, item):
        return {
            "kind": "suppressed_artist",
            "source": "suppression",
            "status": "suppressed",
            "live": False,
            "historical": True,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("artist_key"),
            "album_title": None,
            "album_id": None,
            "score": None,
            "reason": item.get("suppression_reason"),
            "event_ts": item.get("suppressed_ts"),
            "raw": item,
        }

    def _collect_records(self):
        records = []

        extend_review = self.extend_operator_service.list_review_queue()
        extend_review_keys = self._build_extend_review_key_set(extend_review["items"])

        extend_promotable = self.extend_promotion_service.list_promotable_candidates()
        for item in extend_promotable["items"]:
            artist_mbid = (item.get("resolved_artist_mbid") or "").strip().lower()
            album_id = item.get("starter_album_id")

            if artist_mbid and album_id is not None and (artist_mbid, album_id) in extend_review_keys:
                continue

            records.append(self._normalize_extend_promotable(item))

        for item in extend_review["items"]:
            records.append(self._normalize_extend_review(item))

        deepen_review = self.deepen_operator_service.list_review_queue()
        deepen_review_mbids = self._build_deepen_review_mbid_set(deepen_review["items"])

        deepen_candidates = self.deepen_service.list_candidates()
        for item in deepen_candidates["items"]:
            mbid = (item.get("mbid") or "").strip().lower()
            if mbid and mbid in deepen_review_mbids:
                continue

            records.append(self._normalize_deepen_candidate(item))

        for item in deepen_review["items"]:
            records.append(self._normalize_deepen_review(item))

        prune_live = self.prune_query_service.list_prune_candidates()
        for item in prune_live["items"]:
            records.append(self._normalize_prune_live(item))

        prune_history = self.prune_query_service.list_prune_history()
        for item in prune_history["items"]:
            records.append(self._normalize_prune_history(item))

        suppressed = self.extend_query_service.list_suppressed_artists()
        for item in suppressed["items"]:
            records.append(self._normalize_suppressed_artist(item))

        return records

    def _apply_filters(
        self,
        records,
        kind=None,
        source=None,
        status=None,
        artist_name_contains=None,
        album_title_contains=None,
        artist_mbid=None,
        live_only=False,
        historical_only=False,
    ):
        items = list(records)

        if kind:
            wanted = {value.strip() for value in kind}
            items = [item for item in items if item.get("kind") in wanted]

        if source:
            wanted = {value.strip() for value in source}
            items = [item for item in items if item.get("source") in wanted]

        if status:
            wanted = {value.strip() for value in status}
            items = [item for item in items if item.get("status") in wanted]

        if artist_name_contains:
            needle = artist_name_contains.lower().strip()
            items = [
                item
                for item in items
                if needle in (item.get("artist_name") or "").lower()
            ]

        if album_title_contains:
            needle = album_title_contains.lower().strip()
            items = [
                item
                for item in items
                if needle in (item.get("album_title") or "").lower()
            ]

        if artist_mbid:
            needle = artist_mbid.lower().strip()
            items = [
                item
                for item in items
                if (item.get("artist_mbid") or "").lower() == needle
            ]

        if live_only:
            items = [item for item in items if item.get("live")]

        if historical_only:
            items = [item for item in items if item.get("historical")]

        return items

    def query_records(
        self,
        kind=None,
        source=None,
        status=None,
        artist_name_contains=None,
        album_title_contains=None,
        artist_mbid=None,
        live_only=False,
        historical_only=False,
        records=None,
    ):
        if records is None:
            records = self._collect_records()
        items = self._apply_filters(
            records,
            kind=kind,
            source=source,
            status=status,
            artist_name_contains=artist_name_contains,
            album_title_contains=album_title_contains,
            artist_mbid=artist_mbid,
            live_only=live_only,
            historical_only=historical_only,
        )

        items.sort(
            key=lambda item: (
                item.get("source") or "",
                item.get("kind") or "",
                (item.get("artist_name") or "").lower(),
                (item.get("album_title") or "").lower(),
            )
        )

        counts_by_kind = {}
        counts_by_source = {}
        counts_by_status = {}

        for item in items:
            counts_by_kind[item["kind"]] = counts_by_kind.get(item["kind"], 0) + 1
            counts_by_source[item["source"]] = counts_by_source.get(item["source"], 0) + 1
            counts_by_status[item["status"]] = counts_by_status.get(item["status"], 0) + 1

        return {
            "status": "success",
            "count": len(items),
            "counts_by_kind": counts_by_kind,
            "counts_by_source": counts_by_source,
            "counts_by_status": counts_by_status,
            "items": items,
        }
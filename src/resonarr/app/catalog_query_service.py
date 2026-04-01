import time

from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.app.deepen_service import DeepenService
from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.app.prune_query_service import PruneQueryService
from resonarr.app.deepen_query_service import DeepenQueryService
from resonarr.config.settings import CATALOG_SNAPSHOT_TTL_SECONDS
from resonarr.state.memory_store import MemoryStore


class CatalogQueryService:
    SNAPSHOT_NAME = "catalog_records"
    CONTRACT_VERSION = "catalog-record-v1"
    COUNT_SCOPE = "full_filtered_result_set"

    def __init__(
        self,
        extend_query_service=None,
        extend_operator_service=None,
        extend_promotion_service=None,
        deepen_service=None,
        prune_query_service=None,
        prune_operator_service=None,
        deepen_query_service=None,
        memory=None,
    ):
        self.extend_query_service = extend_query_service or ExtendQueryService()
        self.extend_operator_service = extend_operator_service or ExtendOperatorService()
        self.extend_promotion_service = extend_promotion_service or ExtendPromotionService()
        self.deepen_service = deepen_service or DeepenService()
        self.prune_query_service = prune_query_service or PruneQueryService()
        self.prune_operator_service = prune_operator_service or PruneOperatorService()
        self.deepen_query_service = deepen_query_service or DeepenQueryService()
        self.memory = memory or MemoryStore()

    def get_contract_definition(self):
        return {
            "contract_version": self.CONTRACT_VERSION,
            "record_fields": {
                "kind": "normalized record family; stable discriminator for read consumers",
                "source": "top-level source domain: extend, deepen, prune, or suppression",
                "status": "source-native workflow/status value after normalization",
                "live": "true when the record represents current/live read state",
                "historical": "true when the record represents persisted history/state transitions",
                "artist_name": "display artist name",
                "artist_mbid": "artist MusicBrainz ID when available",
                "album_title": "album title when applicable",
                "album_id": "source-native album identifier when applicable",
                "score": "source-specific primary ranking metric",
                "reason": "source-specific explanation for the record state",
                "event_ts": "best available state/event timestamp when one exists",
                "raw": "source-native payload preserved for dashboard/detail shaping",
            },
            "field_semantics": {
                "score_by_source": {
                    "extend_review": "starter_album_score",
                    "extend_promotable": "best_match_score",
                    "deepen_candidate": "lastfm_playcount",
                    "deepen_review": "lastfm_playcount",
                    "prune_candidate": "bad_ratio",
                    "prune_review": "bad_ratio",
                    "prune_history": "bad_ratio",
                    "suppressed_artist": None,
                },
                "reason_by_source": {
                    "extend_review": "starter_album_reason",
                    "extend_promotable": "starter_album_reason",
                    "deepen_candidate": "suppression_reason when applicable, else None",
                    "deepen_review": "suppression_reason when applicable, else None",
                    "prune_candidate": "prune reason/policy explanation",
                    "prune_review": "prune reason/policy explanation",
                    "prune_history": "prune reason/policy explanation",
                    "suppressed_artist": "suppression_reason",
                },
                "event_ts_notes": (
                    "live records may have event_ts=None when no persisted event timestamp exists; "
                    "historical records should expose the best available persisted transition timestamp"
                ),
            },
            "query_semantics": {
                "count": "current page size after pagination",
                "total_count": "full filtered result size before pagination",
                "counts_by_kind": self.COUNT_SCOPE,
                "counts_by_source": self.COUNT_SCOPE,
                "counts_by_status": self.COUNT_SCOPE,
                "sorting": "applied before offset/limit pagination",
                "read_paths": [
                    "provided_records",
                    "snapshot",
                    "snapshot_miss",
                    "snapshot_expired",
                    "snapshot_invalid",
                    "live_refresh",
                ],
            },
        }

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
        if item.get("in_recommendation_backoff"):
            status = "extend_in_recommendation_backoff"
        else:
            status = item.get("status")

        return {
            "kind": "extend_promotable",
            "source": "extend",
            "status": status,
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
        if item.get("in_cooldown"):
            status = "deepen_in_cooldown"
        elif item.get("in_recommendation_backoff"):
            status = "deepen_in_recommendation_backoff"
        else:
            status = item.get("status") or "candidate"

        return {
            "kind": "deepen_candidate",
            "source": "deepen",
            "status": status,
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

    def _normalize_prune_review(self, item):
        return {
            "kind": "prune_review",
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
            "live": True,
            "historical": False,
            "artist_name": item.get("artist_name"),
            "artist_mbid": item.get("artist_key"),
            "album_title": None,
            "album_id": None,
            "score": None,
            "reason": item.get("suppression_reason"),
            "event_ts": item.get("suppressed_ts"),
            "raw": item,
        }

    def build_records_from_results(
        self,
        *,
        extend_review_items,
        extend_promotable_items,
        deepen_candidate_items,
        deepen_review_items,
        prune_live_items,
        prune_review_items,
        prune_history_items,
        suppressed_artist_items,
    ):
        records = []

        extend_review_keys = self._build_extend_review_key_set(extend_review_items)
        for item in extend_promotable_items:
            artist_mbid = (item.get("resolved_artist_mbid") or "").strip().lower()
            album_id = item.get("starter_album_id")

            if artist_mbid and album_id is not None and (artist_mbid, album_id) in extend_review_keys:
                continue

            records.append(self._normalize_extend_promotable(item))

        for item in extend_review_items:
            records.append(self._normalize_extend_review(item))

        deepen_review_mbids = self._build_deepen_review_mbid_set(deepen_review_items)
        for item in deepen_candidate_items:
            mbid = (item.get("mbid") or "").strip().lower()
            if mbid and mbid in deepen_review_mbids:
                continue

            records.append(self._normalize_deepen_candidate(item))

        for item in deepen_review_items:
            records.append(self._normalize_deepen_review(item))

        for item in prune_live_items:
            records.append(self._normalize_prune_live(item))

        for item in prune_review_items:
            records.append(self._normalize_prune_review(item))

        for item in prune_history_items:
            records.append(self._normalize_prune_history(item))

        for item in suppressed_artist_items:
            records.append(self._normalize_suppressed_artist(item))

        return records

    def _collect_live_records(self):
        extend_review = self.extend_operator_service.list_review_queue()
        extend_promotable = self.extend_promotion_service.list_promotable_candidates()

        deepen_candidates = self.deepen_service.list_candidates()
        deepen_review = self.deepen_query_service.list_review_queue_from_live_items(
            deepen_candidates["items"]
        )

        prune_live = self.prune_query_service.list_prune_candidates()
        prune_review = self.prune_query_service.list_reviewable_prune_candidates_from_live_items(
            prune_live["items"]
        )
        prune_history = self.prune_query_service.list_prune_history()

        suppressed = self.extend_query_service.list_suppressed_artists()

        return self.build_records_from_results(
            extend_review_items=extend_review["items"],
            extend_promotable_items=extend_promotable["items"],
            deepen_candidate_items=deepen_candidates["items"],
            deepen_review_items=deepen_review["items"],
            prune_live_items=prune_live["items"],
            prune_review_items=prune_review["items"],
            prune_history_items=prune_history["items"],
            suppressed_artist_items=suppressed["items"],
        )

    def _snapshot_meta(self, read_path, snapshot_age_seconds=None, snapshot_updated_ts=None):
        return {
            "read_path": read_path,
            "snapshot_age_seconds": snapshot_age_seconds,
            "snapshot_updated_ts": snapshot_updated_ts,
        }

    def get_snapshot_records(self):
        snapshot = self.memory.get_catalog_snapshot(self.SNAPSHOT_NAME) or {}
        payload = snapshot.get("payload") or {}
        updated_ts = snapshot.get("updated_ts")

        if not payload or not updated_ts:
            print("[PERF][catalog] snapshot_cache_miss: reason=missing")
            return [], self._snapshot_meta("snapshot_miss")

        age_seconds = int(time.time()) - int(updated_ts)
        if age_seconds < 0:
            age_seconds = 0

        if age_seconds > CATALOG_SNAPSHOT_TTL_SECONDS:
            print(
                f"[PERF][catalog] snapshot_cache_miss: "
                f"reason=expired age_seconds={age_seconds} "
                f"ttl_seconds={CATALOG_SNAPSHOT_TTL_SECONDS}"
            )
            return [], self._snapshot_meta(
                "snapshot_expired",
                snapshot_age_seconds=age_seconds,
                snapshot_updated_ts=updated_ts,
            )

        records = payload.get("records")
        if not isinstance(records, list):
            print("[PERF][catalog] snapshot_cache_miss: reason=invalid_payload")
            return [], self._snapshot_meta(
                "snapshot_invalid",
                snapshot_age_seconds=age_seconds,
                snapshot_updated_ts=updated_ts,
            )

        print(
            f"[PERF][catalog] snapshot_cache_hit: "
            f"age_seconds={age_seconds} ttl_seconds={CATALOG_SNAPSHOT_TTL_SECONDS}"
        )
        return records, self._snapshot_meta(
            "snapshot",
            snapshot_age_seconds=age_seconds,
            snapshot_updated_ts=updated_ts,
        )

    def persist_snapshot(self, records):
        payload = {
            "contract_version": self.CONTRACT_VERSION,
            "count_scope": self.COUNT_SCOPE,
            "records": records,
        }
        self.memory.set_catalog_snapshot(self.SNAPSHOT_NAME, payload)
        print(
            f"[PERF][catalog] snapshot_store: "
            f"ttl_seconds={CATALOG_SNAPSHOT_TTL_SECONDS} "
            f"record_count={len(records)}"
        )

    def refresh_snapshot(self):
        started_at = time.perf_counter()
        records = self._collect_live_records()
        self.persist_snapshot(records)
        elapsed = time.perf_counter() - started_at
        print(f"[PERF][catalog] refresh_snapshot: {elapsed:.2f}s")

        return {
            "status": "success",
            "contract_version": self.CONTRACT_VERSION,
            "read_path": "live_refresh",
            "record_count": len(records),
            "snapshot_ttl_seconds": CATALOG_SNAPSHOT_TTL_SECONDS,
            "elapsed_seconds": round(elapsed, 2),
        }

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
        event_ts_min=None,
        event_ts_max=None,
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

        if event_ts_min is not None:
            items = [
                item
                for item in items
                if item.get("event_ts") is not None and item.get("event_ts") >= event_ts_min
            ]

        if event_ts_max is not None:
            items = [
                item
                for item in items
                if item.get("event_ts") is not None and item.get("event_ts") <= event_ts_max
            ]

        return items

    def _sort_records(self, items, sort_by="source", sort_direction="asc"):
        reverse = (sort_direction or "asc").lower() == "desc"

        def sortable_value(item):
            if sort_by == "artist_name":
                return (item.get("artist_name") or "").lower()

            if sort_by == "album_title":
                return (item.get("album_title") or "").lower()

            if sort_by == "status":
                return (item.get("status") or "").lower()

            if sort_by == "score":
                value = item.get("score")
                return value if value is not None else float("-inf")

            if sort_by == "event_ts":
                value = item.get("event_ts")
                return value if value is not None else -1

            if sort_by == "kind":
                return (item.get("kind") or "").lower()

            return (
                (item.get("source") or "").lower(),
                (item.get("kind") or "").lower(),
                (item.get("artist_name") or "").lower(),
                (item.get("album_title") or "").lower(),
            )

        return sorted(items, key=sortable_value, reverse=reverse)

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
        event_ts_min=None,
        event_ts_max=None,
        sort_by="source",
        sort_direction="asc",
        limit=None,
        offset=0,
        records=None,
        force_refresh=False,
    ):
        read_meta = self._snapshot_meta("provided_records")

        if records is None:
            if force_refresh:
                self.refresh_snapshot()
                records, snapshot_meta = self.get_snapshot_records()
                read_meta = dict(snapshot_meta)
                read_meta["read_path"] = "live_refresh"
            else:
                records, read_meta = self.get_snapshot_records()

        filtered_items = self._apply_filters(
            records,
            kind=kind,
            source=source,
            status=status,
            artist_name_contains=artist_name_contains,
            album_title_contains=album_title_contains,
            artist_mbid=artist_mbid,
            live_only=live_only,
            historical_only=historical_only,
            event_ts_min=event_ts_min,
            event_ts_max=event_ts_max,
        )

        filtered_items = self._sort_records(
            filtered_items,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        total_count = len(filtered_items)

        if offset is None:
            offset = 0

        if offset < 0:
            offset = 0

        if limit is not None and limit < 0:
            limit = 0

        counts_by_kind = {}
        counts_by_source = {}
        counts_by_status = {}

        for item in filtered_items:
            counts_by_kind[item["kind"]] = counts_by_kind.get(item["kind"], 0) + 1
            counts_by_source[item["source"]] = counts_by_source.get(item["source"], 0) + 1
            counts_by_status[item["status"]] = counts_by_status.get(item["status"], 0) + 1

        if limit is None:
            paged_items = filtered_items[offset:]
        else:
            paged_items = filtered_items[offset:offset + limit]

        return {
            "status": "success",
            "contract_version": self.CONTRACT_VERSION,
            "count_scope": self.COUNT_SCOPE,
            "read_path": read_meta.get("read_path"),
            "snapshot_age_seconds": read_meta.get("snapshot_age_seconds"),
            "snapshot_updated_ts": read_meta.get("snapshot_updated_ts"),
            "count": len(paged_items),
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "sort_by": sort_by,
            "sort_direction": sort_direction,
            "counts_by_kind": counts_by_kind,
            "counts_by_source": counts_by_source,
            "counts_by_status": counts_by_status,
            "items": paged_items,
        }

# TODO — API Sprint

Sprint goal: complete the HTTP API layer before building the Flask UI.
Update this file as items are completed — mark with `[x]` and add a note if relevant.

---

## Operator Action Endpoints

These are the highest priority. Reject endpoints already exist; approve endpoints are the symmetric gap.

- [ ] `POST /api/v1/operator/extend/approve`
  - Approve a starter album recommendation for acquisition
  - Service: `extend_operator_service.py` (approve logic already exists)
  - Pattern: mirror `POST /api/v1/operator/extend/reject` in `routers/operator_actions.py`
  - Request body: `artist_name` (required)
  - Response: confirmation with action status, target info, applied flag, invalidated snapshots

- [ ] `POST /api/v1/operator/deepen/approve`
  - Approve a deepening acquisition for a proven-affinity artist
  - Service: `deepen_operator_service.py`
  - Request body: `artist_name` or `mbid` (at least one required)
  - Response: confirmation with action status, target info, applied flag, invalidated snapshots

- [ ] `POST /api/v1/operator/prune/approve`
  - Approve album deletion for a prune candidate
  - Service: `prune_operator_service.py`
  - Request body: `artist_name` (required), `album_name` (required)
  - Response: confirmation with action status, target info, applied flag, invalidated snapshots

---

## Read Model / Snapshot Management Endpoints

Currently only accessible via CLI runners. The UI needs to be able to trigger and inspect snapshot state.

- [ ] `POST /api/v1/read-model/refresh`
  - Trigger snapshot recomputation (catalog + dashboard snapshots)
  - Maps to: `run_read_model_refresh.py` runner logic
  - Note: this is an expensive operation — response should acknowledge the trigger, not block on completion
  - New router file: `routers/read_model.py`

- [ ] `GET /api/v1/read-model/status`
  - Return snapshot ages, availability, and staleness for catalog and dashboard snapshots
  - Maps to: `run_read_model_status.py` runner logic
  - More detailed than `/healthz` — should include snapshot file timestamps and TTL info

---

## Suppression Management Endpoints

No way to inspect or clear suppressions via API currently. UI needs this for the operator review workflow.

- [ ] `GET /api/v1/suppression/records`
  - List all suppression/cooldown records from the memory store
  - Source: `state/memory_store.py`
  - Support optional query params: `entity_type` filter (artist, album), `kind` filter (cooldown, blacklist, rejection, prune_memory)
  - New router file: `routers/suppression.py`

- [ ] `DELETE /api/v1/suppression/{entity_type}/{entity_key}`
  - Manually clear a specific suppression or cooldown record
  - Source: `state/memory_store.py`
  - Invalidates relevant snapshots on success
  - Returns confirmation of what was cleared

---

## Completed

_(Move items here when done, with date and any relevant notes.)_

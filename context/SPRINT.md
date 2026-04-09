# Current Sprint — Complete the HTTP API Layer

## Sprint Goal

**Finish the HTTP API before moving to the Flask UI.**

The Flask operator UI will consume this API entirely. Until the API surface is complete and consistent, the UI has nothing solid to build against. This sprint is about closing all meaningful gaps in the API so the UI can be built on a stable contract.

---

## What "Complete" Means

The API is complete when:

1. All operator actions (extend/deepen/prune) have both **reject** and **approve** endpoints
2. The read model (snapshots) can be **refreshed and inspected** via API — not just CLI
3. **Suppression records** are visible and clearable via API
4. The API surface is sufficient to drive the full operator workflow without touching the CLI

Cycle-triggering endpoints (run-cycle) and per-artist state inspection are lower priority and may remain CLI-only for now — they are not blockers for the UI.

---

## Sprint Scope

### In Scope
- Approve endpoints for Extend, Deepen, and Prune (symmetric to existing reject endpoints)
- Read model refresh endpoint (`POST /api/v1/read-model/refresh`)
- Read model status endpoint (`GET /api/v1/read-model/status`)
- Suppression list endpoint (`GET /api/v1/suppression/records`)
- Suppression clear endpoint (`DELETE /api/v1/suppression/{entity_type}/{entity_key}`)

### Out of Scope This Sprint
- Cycle-triggering endpoints (`POST /api/v1/extend/run-cycle`, etc.) — CLI-only for now
- Per-artist state inspection (`GET /api/v1/artists/{name}/state`) — deferred
- Feedback signal endpoints — deferred
- Run history / audit trail — deferred
- Flask UI — starts after API sprint is done

---

## Context for AI Models

- The service layer for all approve operations already exists in `src/resonarr/app/`:
  - `extend_operator_service.py` — has approve logic mirrored from CLI runner `run_operator_approve_extend.py`
  - `deepen_operator_service.py` — has approve logic mirrored from CLI runner `run_operator_approve_deepen.py`
  - `prune_operator_service.py` — has approve logic mirrored from CLI runner `run_operator_approve_prune.py`
- The reject endpoints in `src/resonarr/transport/http/routers/operator_actions.py` are the pattern to follow
- Request/response schemas live in `src/resonarr/transport/http/schemas/actions.py`
- All mutations must invalidate relevant snapshots (already handled in operator service layer)
- The `manual_operator_action_service.py` in `src/resonarr/app/` is the shared dispatch layer for operator actions
- Error handling follows the pattern in `src/resonarr/transport/http/errors.py`
- New routers get registered in `src/resonarr/transport/http/fastapi_app.py`

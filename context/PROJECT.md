# Resonarr — Project Context

## What It Is

Resonarr is a self-hosted, feedback-driven music discovery and curation engine for Plex/Plexamp and Lidarr. It closes the loop between passive listening behavior and active library management:

**discover → acquire → listen → rate → prune → influence future discovery**

Target user: self-hosted music enthusiasts who want an intelligent, explainable, conservative automation layer on top of Lidarr + Plex — not a magic black box.

---

## Three Core Capabilities

### 1. Extend (Discovery)
Find new artists from external providers, rank them, surface recommendations for operator approval, then send approved candidates to Lidarr for acquisition.

- Status flow: `starter_album_candidate` → `starter_album_recommendation` → `staged_artist` → approved → acquisition
- Gated by suppression memory and recommendation backoff
- Conservative by default: one best release per artist

### 2. Deepen (Artist Expansion)
Acquire additional releases from artists already in the library with proven positive listening affinity.

- Triggered by strong affinity signal (rating + replay density)
- Single best candidate per recommendation by default
- Cooldowns prevent over-expansion

### 3. Prune (Feedback-Driven Cleanup)
Identify and remove low-value albums based on Plex track ratings.

- Tracks rated ≤ 4.0 = "bad"
- Album pruned when bad-ratio exceeds threshold (unrated tracks = neutral)
- Small album override: prune if all rated tracks are bad
- Artist pruned only when zero albums remain
- Always dry-run first; operator review required for destructive actions

---

## Architecture

### Layer Boundaries

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Signals | `src/resonarr/signals/` | Extract feedback from Plex (ratings, play stats) and Last.fm (discovery candidates) |
| Policy | `src/resonarr/policy/` | Pure decision logic — scoring, ranking, prune eligibility |
| Memory/State | `src/resonarr/state/` | Suppression records, cooldowns, rejection history, Plex metadata cache |
| App Services | `src/resonarr/app/` | Orchestrate workflows; extend/deepen/prune each have dedicated service + query + operator service |
| Execution | `src/resonarr/execution/lidarr/` | Translate action intents to Lidarr API calls (MBID-first matching, monitoring strategies) |
| Transport | `src/resonarr/transport/http/` | FastAPI HTTP API — snapshot-backed reads, thin action endpoints |
| Runners | `src/resonarr/runner/` | 29 CLI entry points for cycles, queries, operator actions, and smoke tests |

### Read Model (Snapshot-Backed)
HTTP reads are backed by snapshot files (`catalog_records`, `home_summary`), not live recompute. Snapshots are refreshed out-of-process via CLI runner. Mutations (operator actions) invalidate snapshots immediately. This is intentional — keeps HTTP layer thin and fast.

### State Files
- `resonarr_state.json` — runtime state (candidates, suppression, artist state)
- `resonarr_plex_metadata_cache.json` — cached Plex library data
- `logs/` — timestamped runner output + `latest.log` files

---

## Current Implementation State

### Done
- Full service layer for Extend, Deepen, and Prune (cycle, query, operator)
- Snapshot-backed catalog query service + dashboard service
- CLI runners for all operations (29 runners total)
- FastAPI HTTP transport with 6 endpoints:
  - `GET /healthz`
  - `GET /api/v1/dashboard/home`
  - `GET /api/v1/catalog/records` (full filtering, sorting, pagination)
  - `POST /api/v1/operator/extend/reject`
  - `POST /api/v1/operator/deepen/reject`
  - `POST /api/v1/operator/prune/reject`
- Standardized error handling (`ErrorResponseModel` with code, message, details)
- Plex signal extraction (ratings, play count, replay density)
- Last.fm candidate extractor
- Lidarr execution adapter (MBID-first, monitoring presets)
- Suppression/cooldown memory store

### Not Yet Done (API Layer)
See `TODO.md` for itemized list.

### Explicitly Deferred (Out of v1 Scope)
- Multiple execution backends (beyond Lidarr)
- Multiple discovery providers / provider blending
- Polished dashboards / advanced UI
- Multi-user support / complex auth
- Postgres migration (currently JSON file state)
- Advanced approval workflows
- Sampler playlist / wishlist flows

---

## Key Design Decisions (Locked)

1. **Lidarr is the MVP execution backend** — not a permanent product boundary
2. **Action intents are product-level**, separate from Lidarr API semantics
3. **Artist discovery and monitoring strategy are separate decisions**
4. **Unrated tracks = neutral** — never negative for pruning
5. **Cooldowns over permanent bans** by default
6. **Conservative monitoring default**: `best_release_only` for new artists and deepening
7. **Dry-run and live modes share decision logic** — only execution differs
8. **Snapshot-backed reads** — no heavy recompute in the HTTP layer
9. **Approval required by default** for all operator actions
10. **Automation modes**: `suggest_only` → `approval_required` → `automatic` (destructive always requires approval)
11. **Explainability is a core principle** — every recommendation has a traceable reason
12. **Snapshot refresh stays outside HTTP** — expensive operation, triggered via CLI or dedicated endpoint only

---

## Automation Modes

| Mode | Behavior |
|------|----------|
| `suggest_only` | No actions executed; all surfaced for review. Default for onboarding. |
| `approval_required` | Actions generated; execution requires operator approval. Standard mode. |
| `automatic` | Non-destructive actions execute immediately. Destructive (prune) always require approval. |

---

## Monitoring Presets

| Preset | Behavior |
|--------|----------|
| `none` | Add artist, no releases monitored |
| `best_release_only` | Highest-confidence release (DEFAULT) |
| `latest_release_only` | Most recent release |
| `top_n_releases` | Top N releases (requires `n` parameter) |

---

## Domain Entities (Canonical)

- **Artist**: stable internal ID, canonical name, MBID, Lidarr ID, Plex ID, match confidence
- **Release/Album**: release_key, artist_key, title, release_type, canonical IDs, prune_status
- **Track**: track_key, artist_key, release_key, rating, play stats
- **Candidate**: discoverable item in policy evaluation with provider context and source reason
- **FeedbackSignal**: normalized feedback (rating, play count, recency) with signal type
- **SuppressionRecord**: memory entries (cooldown, blacklist, rejection, prune memory) with optional expiration
- **PolicyDecision**: evaluation outcome (allow, suppress, reject, recommend, acquire, prune)
- **ActionPlan**: action intent + monitoring strategy + execution mode
- **ActionResult**: execution outcome with status and executor reference IDs
- **RunHistory**: end-to-end run traceability container

---

## Next Phase

**Current sprint**: Complete the HTTP API layer (approve endpoints, read-model management, suppression visibility).

**After API is complete**: Build a Flask UI that consumes this API for operator workflows — review queues, dashboard, candidate cards, one-click approve/reject.

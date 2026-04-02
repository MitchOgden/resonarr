# Manual Action API Scope

## In scope for this sprint

This sprint adds the minimum safe manual operator action API over already surfaced review queues.

Endpoints in scope:

- `POST /api/v1/operator/extend/reject`
- `POST /api/v1/operator/deepen/reject`
- `POST /api/v1/operator/prune/reject`

These actions are intentionally narrow:
- they apply a concrete operator decision
- they mutate app state through app-layer action services
- they invalidate affected read-model snapshots
- they do not rebuild snapshots inline
- they do not trigger heavy refresh/recompute in HTTP

## Explicitly out of scope

Not in scope for this sprint:

- approve/execute endpoints
- refresh endpoints
- run-now/cycle endpoints
- generalized workflow action endpoints
- provider/admin/control-plane endpoints
- auth
- UI work
- background recompute infrastructure

## Read-after-write behavior

Read endpoints remain snapshot-backed.

After a successful action:
- `catalog_records` snapshot is invalidated
- `home_summary` snapshot is invalidated

The API does not rebuild those snapshots inline.

Until a non-HTTP refresh path repopulates them, snapshot-backed read routes may return:
- `503 snapshot_unavailable`

This is intentional. Controlled temporary read unavailability is preferred over hidden expensive recomputation in request handling.

## Why refresh/recompute stays outside HTTP

Snapshot priming is still materially expensive because it runs the same deepen/prune recomputation path used by the existing refresh flow.

That work remains outside HTTP so:
- request latency stays predictable
- operator actions stay thin
- transport does not become a generic execution surface
- read/write consistency remains explicit instead of implicit

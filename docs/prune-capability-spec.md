# Prune / Trim Capability Spec (Working Draft)

## 1. Purpose

Prune is an opt-in Resonarr capability that identifies low-value library content using listener feedback and policy, then produces reviewable or executable removal actions against the execution backend.

For v1 scope, the initial backend is Lidarr and the initial signal source is Plex track ratings, matching the behavior already proven in the prototype script: album scoring from track ratings, MBID-first Lidarr matching, dry-run-first execution, album deletion, optional artist deletion when nothing remains, and Plex rescan afterward. :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1} :contentReference[oaicite:2]{index=2}

## 2. Product framing

Prune is a first-class capability alongside:
- Extend
- Deepen
- Operator review

It is not just a maintenance script and it should not be buried inside deepen.

Resonarr owns:
- pruning policy
- decisioning
- memory / suppression
- audit / operator workflow

Lidarr owns:
- unmonitoring
- deleting albums/files
- deleting artists when requested

That matches the current product direction where Lidarr is the execution backend, not the product boundary.

## 3. Goals

For initial prune capability, Resonarr should:
- identify prune-eligible albums from listener feedback
- support dry-run / recommendation-only mode first
- optionally execute approved prune actions against Lidarr
- remember what was pruned and why
- block accidental reacquisition of content the user effectively rejected
- rescan Plex after destructive actions so the listening surface reflects changes quickly :contentReference[oaicite:3]{index=3}

## 4. Non-goals for first version

Not in first prune version:
- deleting individual tracks directly
- multi-source sentiment fusion beyond Plex ratings
- full artist-level taste modeling
- generalized media pruning beyond music
- broad autonomous destructive behavior by default

The first prune version should be conservative and operator-visible.

## 5. Inputs / signals

### Initial signal source

Plex track ratings.

The prototype already uses PlexAPI ratings on the 0.0–10.0 scale and treats `<= 4.0` as a “bad” signal, equivalent to about 2 stars or lower. 

### Initial scoring inputs

- track rating threshold for “bad”
- minimum rated tracks required before an album is eligible
- album bad-ratio threshold
- unrated track strategy
- small album handling rule
- optional artist prune when no albums remain 

## 6. Initial policy model

For v1, keep policy close to what the script already proved.

### Album prune eligibility

An album becomes prune-eligible when:
- it has at least `MIN_TRACKS_RATED` rated tracks, and
- `bad_tracks / rated_tracks >= ALBUM_BAD_RATIO`

### Small album override

If enabled:
- albums below `MIN_TRACKS_RATED` may still be prune-eligible if all rated tracks are bad

That mirrors current script behavior. 

### Unrated track handling

Supported policy values:
- `ignore`
- `neutral`

This should remain explicit policy, not hidden code behavior. :contentReference[oaicite:7]{index=7}

### Artist prune rule

Initial artist prune rule should remain strict and simple:
- only prune artist if zero albums remain after album prune execution

That matches the current script and is much safer than artist-wide taste inference in v1. 

## 7. Matching strategy

Initial matching contract:
- MBID-first
- optional normalized-name fallback
- fallback must be configurable and auditable

That is already how the script works and is the correct default. 

## 8. Execution behavior

### Album prune execution

For an approved prune action:
1. unmonitor album
2. delete album with files
3. record prune state
4. update suppression / reacquisition memory if applicable

That is exactly what the script does today in live mode. 

### Artist prune execution

If artist pruning is enabled and zero albums remain:
1. verify current backend state
2. delete artist
3. record prune state

Again, this is already in the prototype. 

### Post-action sync

After destructive prune actions:
- trigger Plex library rescan

This should remain part of the official capability, not an afterthought. :contentReference[oaicite:12]{index=12}

## 9. Safety model

Prune should be safer than acquisition by default.

### Required safety features

- global opt-in
- dry-run support
- operator review queue by default
- explicit execution mode toggle
- audit trail
- configurable destructive scope:
  - prune albums only
  - prune albums + artist cleanup
  - no auto-delete unless explicitly enabled

The script already demonstrates two core safety ideas to preserve:
- `DRY_RUN`
- conservative scoring knobs at the top of the workflow 

## 10. Product modes

### Mode A: Recommend-only

Resonarr creates:
- `prune_album_recommendation`
- optionally `prune_artist_recommendation`

No deletion occurs until operator approval.

### Mode B: Approve-to-execute

Operator approves recommendation and Resonarr executes against Lidarr.

### Mode C: Auto-prune

Only after operator trust is established:
- fully opt-in
- explicit guardrails
- likely album-only first

## 11. State model

Add prune-specific state separate from extend/deepen.

### Candidate / outcome statuses

For albums:
- `prune_candidate`
- `prune_recommendation`
- `prune_approved`
- `prune_executed`
- `prune_rejected`
- `prune_skipped`
- `prune_failed`

For artists:
- `artist_prune_recommendation`
- `artist_prune_executed`
- `artist_prune_rejected`

### Persisted fields

At minimum:
- artist name
- artist MBID
- album title
- album ID
- signal source
- rated track count
- bad track count
- bad ratio
- prune reason
- execution status
- timestamps
- whether reacquisition is blocked

## 12. Suppression / reacquisition policy

This is where Resonarr becomes more valuable than the standalone script.

When an album is pruned, Resonarr should be able to remember:
- this album was intentionally removed
- whether reacquisition should be blocked
- whether deepen should avoid recommending it again
- whether extend / artist-level policy should treat that as negative feedback

For v1, recommended behavior:
- block reacquisition of explicitly pruned albums by default
- do not automatically blacklist the whole artist unless explicitly configured

## 13. Operator workflow

### Review queue

Add a prune review queue similar to the starter-album review queue.

Each prune card should show:
- artist
- album
- rated tracks
- bad tracks
- bad ratio
- matching method
- reason
- proposed action

The script already logs these details in a useful shape during candidate generation. :contentReference[oaicite:14]{index=14}

### Operator actions

For album prune recommendations:
- approve
- reject
- suppress future prune for this album
- suppress prune for this artist

For artist prune recommendations:
- approve
- reject

## 14. Backend boundary

### Resonarr layer

Should own:
- prune policy
- candidate generation
- state transitions
- review queue
- audit log
- suppression / reacquisition memory

### Lidarr adapter layer

Should own:
- album unmonitor
- album delete
- artist delete

### Plex signal layer

Should own:
- extracting track ratings
- computing album-level prune inputs

## 15. Suggested v1 architecture slice

New conceptual components:

- `signals/plex/prune_extractor.py`
- `policy/prune_policy.py`
- `domain/prune_intent.py`
- `app/prune_service.py`
- `app/prune_query_service.py`
- `runner/run_prune_cycle.py`
- `runner/run_prune_service_smoke.py`
- `runner/run_operator_review_prune.py`
- `runner/run_operator_approve_prune.py`
- `runner/run_operator_reject_prune.py`

That follows the same pattern already established for extend and deepen.

## 16. Suggested initial action intent types

Define explicit prune intents like:
- `PRUNE_ALBUM`
- `PRUNE_ARTIST`
- `RECOMMEND_PRUNE_ALBUM`
- `RECOMMEND_PRUNE_ARTIST`
- `NO_ACTION`

This keeps prune policy separate from execution and aligns with the existing action-intent pattern.

## 17. MVP sequencing recommendation

### Phase 1

Recommendation-only prune flow:
- score prune candidates
- build prune review queue
- no destructive action by default

### Phase 2

Approval-based execution:
- approve album prune
- execute unmonitor + delete
- optional artist cleanup if no albums remain
- rescan Plex

### Phase 3

Automation:
- opt-in auto-prune
- reacquisition blocking
- richer negative-taste memory

## 18. Default policy recommendation

For first productized default behavior, keep it conservative:

- `enabled = false`
- `dry_run = true`
- `match_mode = mbid`
- `allow_name_fallback = false` by default in product, even though the script allows it
- `min_tracks_rated = 5`
- `album_bad_ratio = 0.50`
- `unrated_track_strategy = neutral`
- `allow_small_album_full_reject = true`
- `enable_artist_prune = false` by default until operator opts in

Reason: the product default should be safer than the personal script default.

## 19. Open questions to decide before implementation

1. Should prune start as recommendation-only, or execute-on-approval from day one?
2. Should pruned albums automatically be blocked from reacquisition?
3. Should artist prune be part of initial UI/operator flow, or deferred?
4. Should name fallback be allowed in product default mode, or only in advanced mode?
5. Should low-rated albums influence future extend/deepen artist scoring?

## 20. Recommendation

Add prune to the roadmap now and treat it as the next major product capability after the current dashboard/service/API planning work.

Recommended first implementation target:
- prune recommendation flow
- operator review queue
- approval-based album prune execution
- optional Plex rescan
- artist prune deferred behind a toggle
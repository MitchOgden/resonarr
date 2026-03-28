# Resonarr

Resonarr is a self-hosted, feedback-driven music discovery and curation engine for Plex/Plexamp and Lidarr.

It is designed to close the loop between:

**discover → acquire → listen → rate → prune → influence future discovery**

Instead of treating music acquisition as a one-way pipeline, Resonarr uses listening feedback, ratings, suppression memory, and pruning outcomes to make future discovery and acquisition decisions smarter over time.

## What it is

Resonarr is not just a pruning script and not just a discovery tool.

It is intended to become a product-level orchestration layer for self-hosted music users who want:

- smarter artist discovery
- conservative acquisition
- explainable automation
- pruning based on actual listening feedback
- memory and cooldowns to avoid rediscovering bad fits
- separation between discovery, policy, and execution

## Initial focus

The initial implementation is focused on:

- **Plex / Plexamp** for feedback ingestion
- **Lidarr** as the first execution backend
- conservative, explainable discovery and pruning workflows
- dry-runs, auditability, and operator trust

Lidarr is the initial execution target, **not** the permanent product boundary.

## Core product idea

Resonarr should eventually support:

- configurable discovery from multiple providers
- library/play-stat driven discovery
- behavior/rating driven discovery
- hybrid discovery
- Plex-based feedback ingestion
- suppression memory and cooldowns
- pruning influenced by actual user feedback
- recommendation-only and review-based workflows
- alternate acquisition or non-acquisition action paths in the future

A core design principle is that these should remain separate concerns:

1. **Discovery**  
   What should enter the system?

2. **Policy / Scoring**  
   Why should it be allowed, suppressed, queued, or preferred?

3. **Execution**  
   What should actually happen right now through a backend like Lidarr?

4. **Feedback / Memory**  
   What happened after the user listened, and how should that affect future decisions?

## Product principles

Resonarr is being designed around a few strong defaults:

- conservative by default
- explainable decisions
- dry-run before destructive execution
- cooldowns over permanent bans in many cases
- trust in automation matters more than aggressive behavior
- artist discovery and monitoring strategy are separate decisions

## MVP direction

The MVP is intended to validate a trustworthy, conservative, explainable loop using:

- one discovery provider
- Plex feedback
- suppression/cooldown memory
- Lidarr as the only execution backend in v1
- minimal operator UI or CLI surface

## Planned module boundaries

The core architecture is expected to separate:

- discovery provider connectors
- identity + normalization
- feedback ingestion
- memory / suppression
- policy / scoring
- action planning
- Lidarr execution
- operator UI / API

## Status

Planning / architecture phase.

Current work is focused on:

- product framing
- MVP boundaries
- module boundaries
- canonical entity modeling
- action-intent modeling
- policy and discovery design
- roadmap definition

## Docs

Project planning docs live in [`/docs`](./docs).

Suggested early docs:

- `project-brief.md`
- `mvp-spec-module-boundary.md`
- `decided.md`
- `deferred.md`
- `open-questions.md`014803
- `roadmap.md`

## Development workflow notes

During active MVP development, the repository intentionally keeps runtime artifacts that are useful for debugging and review:

- `resonarr_state.json` is currently tracked because the state model is still evolving and the file is useful for debugging promotion, backoff, starter-album planning, and other decision behavior.
- `logs/` is currently tracked so runner output can be reviewed directly from the repository.

Current runner commands:

- `python -m resonarr.runner.run_extend_cycle`
- `python -m resonarr.runner.run_extend_promotion_cycle`

Operator workflow runners:

- `python -m resonarr.runner.run_operator_review_queue`
- `python -m resonarr.runner.run_operator_approve_extend "Artist Name"`
- `python -m resonarr.runner.run_operator_reject_extend "Artist Name"`
- `python -m resonarr.runner.run_extend_query_smoke`
- `python -m resonarr.runner.run_extend_status_summary`
- `python -m resonarr.runner.run_extend_promotion_service_smoke`
- `python -m resonarr.runner.run_deepen_service_smoke`
- `python -m resonarr.runner.run_dashboard_service_smoke`
- `python -m resonarr.runner.run_dashboard_summary`
- `python -m resonarr.runner.run_prune_service_smoke`
- `python -m resonarr.runner.run_prune_cycle`
- `python -m resonarr.runner.run_prune_query_smoke`
- `python -m resonarr.runner.run_prune_status_summary`

Prune now has a query/read layer so candidate summaries and reviewable prune recommendations can be consumed as structured backend data before operator execution is added.
Prune now has an initial backend slice with Plex signal extraction, pure policy evaluation, Lidarr matching, and dry-run candidate generation before any destructive execution is introduced.
Dashboard sections and highlights now emit normalized UI-facing card shapes so future API/UI layers do not have to depend on raw service-specific item structures.
The query/smoke runners are intended as backend test points for future API/UI work. They expose summary and review data in stable structured shapes before any web transport is added.
Promotion orchestration now also has a service smoke runner so structured planning results can be validated independently of CLI formatting.
Deepen orchestration also has a dry-run service smoke runner so candidate evaluation can be previewed in structured form without mutating execution state.
The dashboard smoke/summary runners provide the first unified UI-facing read model by composing extend query, extend operator, extend promotion, and deepen service data into a single payload.

Current MVP operator flow:

1. Run extend discovery and extend promotion.
2. Review `starter_album_recommendation` and `starter_album_candidate` outputs.
3. Approve a recommendation to monitor and search the selected album in Lidarr.
4. Reject a recommendation to suppress the artist in Resonarr and remove the staged unmonitored artist from Lidarr.

Each runner writes output to:

- the console
- a timestamped log file in `logs/`
- a stable `*-latest.log` file in `logs/` that is overwritten on each run

This makes it easy to inspect both the latest run and recent run history directly from the codebase.

## Non-goals for early versions

Resonarr is **not** trying to start as:

- a giant generalized media platform
- a plugin marketplace
- a full multi-user product
- a polished dashboard-heavy web app
- a universal rule-builder DSL
- a many-backend system on day one

The first goal is to prove the loop and make it trustworthy.

## Why this exists

Plex/Plexamp and Lidarr users can already automate acquisition.

What is still missing is a reliable way to let a library evolve based on actual taste.

Resonarr exists to make a self-hosted music library feel less like a dumping ground and more like a system that learns what resonates.

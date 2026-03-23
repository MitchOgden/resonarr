# Canonical Entity Schema (Working Draft)

This schema defines the **product-level canonical model** for Resonarr, not the final database schema or API contract.

## Goals

- Normalize discovery/provider data into one internal shape
- Keep policy/scoring independent from Lidarr execution details
- Keep memory/feedback reusable across future backends
- Avoid designing the product around one provider or one executor too early

## Principles

- Prefer canonical IDs / MBIDs where possible
- Separate normalized entities from action/execution records
- Separate facts from decisions
- Keep executor-specific fields out of core entities unless clearly isolated

---

## 1. Artist

### Purpose
Represents the canonical internal artist entity used across providers, Plex, Lidarr, feedback, suppression, and action planning.

### Required fields
- `artist_key`
  - Internal stable ID for the product
- `name`
  - Canonical display name
- `canonical_ids`
  - Object or map of known external canonical IDs
  - Should support MusicBrainz artist ID when available
- `match_confidence`
  - Confidence level of the current resolved identity
- `created_at`
- `updated_at`

### Optional fields
- `sort_name`
- `provider_ids`
  - Provider-specific artist IDs by provider name
- `lidarr_artist_id`
- `plex_artist_id`
- `status`
  - `active` / `suppressed` / `blacklisted` / `unknown`
- `origin_sources`
  - Where this artist first entered the system
- `genres`
- `country`
- `formed_year`
- `disambiguation`
- `metadata_snapshot`
  - Normalized metadata from best available source

### Source of truth
- Internal canonical record, built from provider normalization and identity resolution

### Notes / constraints
- `artist_key` is the internal product ID, not a provider ID
- MBID should be preferred when available, but absence of MBID must not block the record
- Lidarr/Plex IDs are references, not identity truth

---

## 2. Release / Album

### Purpose
Represents a canonical release entity used for monitoring, acquisition planning, pruning, and feedback rollups.

### Required fields
- `release_key`
  - Internal stable ID
- `artist_key`
  - Parent artist reference
- `title`
- `release_type`
  - `album` / `ep` / `single` / `compilation` / `live` / `other`
- `canonical_ids`
  - Should support MusicBrainz release-group/release ID where available
- `match_confidence`
- `created_at`
- `updated_at`

### Optional fields
- `provider_ids`
- `lidarr_album_id`
- `plex_album_id`
- `release_date`
- `release_year`
- `track_count`
- `monitored_state`
  - Normalized internal monitoring state, not raw Lidarr field semantics
- `prune_status`
  - `none` / `candidate` / `pruned` / `suppressed`
- `metadata_snapshot`
- `edition_notes`
- `explicit`
- `origin_sources`

### Source of truth
- Internal canonical record built by normalization and matching

### Notes / constraints
- Keep internal release identity distinct from Lidarr’s representation
- Release type matters because pruning/monitoring policy may treat albums, EPs, and singles differently
- This entity should be able to exist even if no Lidarr match exists yet

---

## 3. Track

### Purpose
Represents a canonical track entity used mainly for feedback ingestion and album-level rollups.

### Required fields
- `track_key`
  - Internal stable ID
- `artist_key`
- `release_key`
- `title`
- `canonical_ids`
  - Recording ID or equivalent when available
- `match_confidence`
- `created_at`
- `updated_at`

### Optional fields
- `provider_ids`
- `plex_track_id`
- `lidarr_track_id`
  - Only if relevant/available later
- `track_number`
- `disc_number`
- `duration_ms`
- `rating_snapshot`
- `play_stats_snapshot`
- `metadata_snapshot`

### Source of truth
- Internal canonical record, usually built from Plex and/or provider metadata

### Notes / constraints
- Track identity can be messy; allow partial confidence
- MVP likely uses tracks mostly as feedback inputs rather than discovery outputs

---

## 4. Candidate

### Purpose
Represents a discoverable item entering policy evaluation before action planning.

### Required fields
- `candidate_key`
  - Internal stable ID for the candidate record
- `candidate_type`
  - `artist` / `release` / `track`
- `target_entity_key`
  - Reference to canonical artist/release/track when resolved
- `provider`
- `provider_object_id`
- `source_reason`
  - Human-readable or structured reason this candidate appeared
- `discovery_mode`
  - `library_play_stat` / `behavior_rating` / `hybrid`
- `generated_at`

### Optional fields
- `provider_score`
- `confidence_score`
- `seed_context`
  - What artist/play/rating/library signal caused this candidate to appear
- `provider_rank`
- `normalized_metadata_snapshot`
- `candidate_status`
  - `pending` / `evaluated` / `suppressed` / `planned` / `rejected`
- `dedupe_key`
  - For collapsing repeated discovery appearances
- `explainability_payload`

### Source of truth
- Generated from provider output + normalization pipeline

### Notes / constraints
- A candidate is not yet a decision
- A candidate can exist before perfect entity resolution, but unresolved state must be explicit
- Candidates are more ephemeral than core canonical entities, but should still be auditable
- Candidates may also represent missing releases from already-known artists surfaced through policy, including artist deepening by proven affinity

---

## 5. FeedbackSignal

### Purpose
Represents a normalized feedback event or snapshot from Plex and other future sources, used by policy and pruning.

### Required fields
- `feedback_key`
  - Internal stable ID
- `entity_type`
  - `artist` / `release` / `track`
- `entity_key`
- `signal_type`
  - `rating` / `play_count` / `play_recency` / `prune_outcome` / `manual_reject` / `manual_approve` / `other`
- `signal_value`
  - Normalized value
- `observed_at`
- `source`
  - `plex` / `internal` / future source name

### Optional fields
- `raw_value`
- `weight`
- `user_scope`
  - Future-proofing for multi-user, but can be nullable/unused in MVP
- `context`
  - Snapshot of what generated the signal
- `confidence`
- `run_key`
  - If tied to a run

### Source of truth
- Feedback ingestion pipeline and internal action outcomes

### Notes / constraints
- This should be generic from day one
- Do not hardwire this entity to Plex-only semantics
- MVP may only use a subset of signal types, but the schema should not block later additions

---

## 6. SuppressionRecord

### Purpose
Represents a memory record that reduces or blocks future rediscovery/reacquisition.

### Required fields
- `suppression_key`
- `entity_type`
  - `artist` / `release` / `track` / `candidate_pattern` if needed later
- `entity_key`
- `suppression_type`
  - `cooldown` / `blacklist` / `rejection_memory` / `prune_memory`
- `reason_code`
- `created_at`
- `active`

### Optional fields
- `expires_at`
- `source`
  - `policy` / `manual` / `prune` / `feedback` / `provider`
- `linked_feedback_key`
- `linked_action_result_key`
- `notes`
- `severity`
- `override_allowed`

### Source of truth
- Memory/suppression subsystem

### Notes / constraints
- Distinguish temporary cooldowns from durable blacklists
- This entity should influence policy but not replace policy decisions
- Suppression should be explainable and reversible where appropriate

---

## 7. PolicyDecision

### Purpose
Represents the evaluated outcome of policy/scoring against a candidate or entity before execution.

### Required fields
- `decision_key`
- `subject_type`
  - `candidate` / `artist` / `release` / `track`
- `subject_key`
- `decision_type`
  - `allow` / `suppress` / `reject` / `recommend` / `queue` / `acquire` / `prune` / `defer`
- `decision_reason_summary`
- `decided_at`

### Optional fields
- `score_total`
- `score_components`
  - Structured list/map of scoring contributors
- `matched_rules`
- `suppression_hits`
- `monitoring_recommendation`
- `confidence`
- `explainability_payload`
- `run_key`
- `supersedes_decision_key`

### Source of truth
- Policy/scoring engine

### Notes / constraints
- This is a decision artifact, not a command
- It must be explainable enough to support dry-run review
- Multiple policy decisions may exist over time for the same entity

---

## 8. ActionPlan

### Purpose
Represents an actionable plan derived from one or more policy decisions, before execution.

### Required fields
- `action_plan_key`
- `action_intent`
  - Generic product-level intent
- `subject_type`
- `subject_key`
- `planned_at`
- `execution_mode`
  - `suggest_only` / `approval_required` / `automatic`
- `reason_summary`

### Optional fields
- `monitoring_strategy`
- `executor_target`
  - `lidarr` in MVP
- `plan_payload`
  - Normalized details needed by the executor
- `related_decision_keys`
- `approval_status`
  - `pending` / `approved` / `rejected` / `not_required`
- `dry_run_preview`
- `safety_flags`
- `priority`

### Source of truth
- Action planner

### Notes / constraints
- Keep this generic from day one
- `action_intent` should not be a raw Lidarr API action
- Executor-specific translation should happen later in the adapter layer

---

## 9. ActionResult

### Purpose
Represents the outcome of attempting to execute an ActionPlan.

### Required fields
- `action_result_key`
- `action_plan_key`
- `executor`
  - `lidarr` in MVP
- `result_status`
  - `success` / `failed` / `skipped` / `dry_run` / `partially_applied`
- `executed_at`

### Optional fields
- `executor_operation`
  - Executor-specific operation label
- `executor_reference_ids`
  - IDs returned or affected by executor
- `result_summary`
- `error_code`
- `error_details`
- `changed_entities`
- `cleanup_followup_required`
- `raw_execution_payload`

### Source of truth
- Execution adapter

### Notes / constraints
- This should record what happened, not just whether it was intended
- Dry-run results may still create ActionResult-like records for audit consistency

---

## 10. RunHistory

### Purpose
Represents one end-to-end discovery, pruning, or mixed system run for audit, observability, and troubleshooting.

### Required fields
- `run_key`
- `run_type`
  - `discovery` / `prune` / `feedback_sync` / `mixed`
- `started_at`
- `completed_at`
- `status`
  - `running` / `success` / `failed` / `partial` / `cancelled`

### Optional fields
- `initiated_by`
  - `scheduler` / `manual` / `system`
- `config_snapshot`
- `provider_scope`
- `execution_mode`
- `candidate_count`
- `decision_count`
- `action_plan_count`
- `action_result_count`
- `warning_count`
- `error_count`
- `summary`
- `linked_entity_keys`

### Source of truth
- Orchestration layer / scheduler / job runner

### Notes / constraints
- This is the container for traceability
- Helps power dry-run history, audits, and trust/debug UX later

---

## Entity relationship summary

At a high level:

- **Artist** has many **Release / Album**
- **Release / Album** has many **Track**
- **Candidate** may point to **Artist**, **Release**, or **Track**
- **FeedbackSignal** points to **Artist**, **Release**, or **Track**
- **SuppressionRecord** points to **Artist**, **Release**, **Track**, or later other suppressible subjects
- **PolicyDecision** evaluates a **Candidate** or canonical entity
- **ActionPlan** is generated from **PolicyDecision** output
- **ActionResult** records what happened when **ActionPlan** execution was attempted
- **RunHistory** groups candidates, decisions, action plans, and outcomes into one auditable run

---

## Generic from day one vs executor-specific

### Must stay generic now
- Artist
- Release / Album
- Track
- Candidate
- FeedbackSignal
- SuppressionRecord
- PolicyDecision
- ActionPlan
- RunHistory

### Can include executor-specific references without becoming executor-owned
- `lidarr_artist_id`
- `lidarr_album_id`
- `plex_artist_id`
- `plex_album_id`
- `plex_track_id`

These are linkage fields only, not canonical identity.

### Should remain executor-specific elsewhere
- raw Lidarr API payloads
- exact Lidarr monitoring flags
- exact Lidarr delete/remove semantics
- executor operation names

Those belong in the execution adapter and ActionResult details, not in the product-level model.

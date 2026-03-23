# Action-Intent Schema (v1 Working Draft)

## Purpose

This document defines the v1 product-level action-intent model for Resonarr.

It defines the normalized action language between:

- policy/scoring
- action planning
- execution

It does not define:

- database tables
- API payloads
- Lidarr API calls
- provider contracts

## Goals

- Keep product decisions separate from Lidarr-specific execution details
- Support dry-runs, approvals, and explainability cleanly
- Avoid coupling policy output directly to Lidarr API semantics
- Allow future non-Lidarr action paths without redesigning core product decisions
- Keep v1 intentionally small and practical

## Principles

- Action intents are product-level instructions, not raw executor commands
- Action intents may exist even when no execution backend call will happen
- One policy decision may produce one or more action intents
- One action intent may produce zero, one, or multiple executor operations
- Action intents must remain explainable and auditable
- v1 includes only the action intents needed to support the MVP

---

## v1 Action-Intent List

The v1 action-intent set is:

- `recommend_candidate`
- `queue_for_review`
- `acquire_artist`
- `set_monitoring_strategy`
- `prune_release`
- `prune_artist`
- `suppress_entity`
- `defer_entity`

---

## Intent Definitions

## `recommend_candidate`

### Purpose
Represents a positive product recommendation that should be surfaced to the operator but not automatically sent to an execution backend.

### Allowed subjects
- `candidate`
- `artist`
- `release`

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `source_context`
- `recommended_at`

### Optional payload
- `score_total`
- `score_components`
- `monitoring_recommendation`
- `provider_context`
- `related_decision_keys`
- `display_priority`

### v1 support
- Supported in v1
- Product-level only
- No direct Lidarr execution required

---

## `queue_for_review`

### Purpose
Represents an action that should enter a review/approval workflow instead of being automatically executed.

### Allowed subjects
- `candidate`
- `artist`
- `release`
- `action_plan_bundle`

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `queue_reason`
- `queued_at`

### Optional payload
- `score_total`
- `score_components`
- `proposed_followup_intents`
- `related_decision_keys`
- `approval_required`
- `display_priority`
- `expires_at`

### v1 support
- Supported in v1
- Implemented initially as a simple review state rather than a full queue product

---

## `acquire_artist`

### Purpose
Represents the decision to send an artist into the acquisition backend.

### Allowed subjects
- `artist`
- `candidate` resolving to an artist

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `executor_target`
- `acquire_at`

### Optional payload
- `canonical_ids`
- `provider_ids`
- `match_confidence`
- `related_decision_keys`
- `seed_context`
- `safety_flags`

### v1 support
- Supported in v1
- Lidarr-backed execution

### Notes
- This intent does not implicitly mean full-catalog monitoring
- Discovery/admission and monitoring remain separate decisions

---

## `set_monitoring_strategy`

### Purpose
Represents the product-level decision for how aggressively an admitted artist or release should be monitored.

### Allowed subjects
- `artist`
- `release`

### Required payload
- `subject_type`
- `subject_key`
- `monitoring_strategy`
- `reason_summary`
- `set_at`

### Optional payload
- `executor_target`
- `strategy_context`
- `related_decision_keys`
- `safety_flags`

### Allowed v1 monitoring strategies
- `none`
- `latest_release_only`
- `top_1_release`
- `top_n_releases`
- `studio_albums_only`
- `full_catalog`

### v1 support
- Supported in v1
- Lidarr-backed mapping required

### Notes
- This is a product-level intent, not a raw Lidarr settings blob
- `top_n_releases` requires an additional numeric parameter in payload when used

---

## `prune_release`

### Purpose
Represents the decision to remove, unmonitor, or delete a release based on feedback-driven pruning logic.

### Allowed subjects
- `release`

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `prune_reason_code`
- `prune_at`

### Optional payload
- `executor_target`
- `feedback_context`
- `score_context`
- `delete_files`
- `unmonitor_first`
- `related_decision_keys`
- `safety_flags`

### v1 support
- Supported in v1
- Lidarr-backed execution

### Notes
- v1 pruning behavior should preserve the current product decisions:
  - unrated tracks treated as neutral
  - small-release full-reject logic retained
- Dry-run and live mode should share the same decision basis

---

## `prune_artist`

### Purpose
Represents the decision to remove an artist only when artist-level prune conditions are met.

### Allowed subjects
- `artist`

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `prune_reason_code`
- `prune_at`

### Optional payload
- `executor_target`
- `related_release_keys`
- `related_decision_keys`
- `safety_flags`
- `approval_required`

### v1 support
- Supported in v1
- Lidarr-backed execution
- More conservative than release pruning

### Notes
- v1 should not prune an artist simply because one release performed poorly
- Artist prune should generally require that no relevant releases remain

---

## `suppress_entity`

### Purpose
Represents the decision to create or update suppression memory that reduces or blocks future rediscovery or reacquisition.

### Allowed subjects
- `artist`
- `release`
- `track`
- `candidate`

### Required payload
- `subject_type`
- `subject_key`
- `suppression_type`
- `reason_summary`
- `suppress_at`

### Allowed v1 suppression types
- `cooldown`
- `blacklist`
- `rejection_memory`
- `prune_memory`

### Optional payload
- `expires_at`
- `severity`
- `override_allowed`
- `linked_feedback_keys`
- `linked_action_result_keys`
- `related_decision_keys`

### v1 support
- Supported in v1
- Product-level behavior
- No direct Lidarr execution required

### Notes
- This intent should usually result in creation or update of a `SuppressionRecord`
- Cooldowns should generally be preferred over permanent bans by default

---

## `defer_entity`

### Purpose
Represents the decision to intentionally do nothing now while preserving context for future reevaluation.

### Allowed subjects
- `candidate`
- `artist`
- `release`

### Required payload
- `subject_type`
- `subject_key`
- `reason_summary`
- `defer_reason_code`
- `defer_at`

### Optional payload
- `revisit_after`
- `related_decision_keys`
- `score_context`
- `provider_context`

### v1 support
- Supported in v1
- Product-level only
- No Lidarr execution required

### Notes
- Deferral is distinct from suppression
- Suppression means reduce or block resurfacing
- Deferral means wait and reconsider later

---

## Intent Support Matrix

| Action intent              | Product-level | Supported in v1 | Lidarr-backed in v1 | Internal-only in v1 |
|---------------------------|---------------|-----------------|---------------------|---------------------|
| `recommend_candidate`     | Yes           | Yes             | No                  | Yes                 |
| `queue_for_review`        | Yes           | Yes             | No                  | Yes                 |
| `acquire_artist`          | Yes           | Yes             | Yes                 | No                  |
| `set_monitoring_strategy` | Yes           | Yes             | Yes                 | No                  |
| `prune_release`           | Yes           | Yes             | Yes                 | No                  |
| `prune_artist`            | Yes           | Yes             | Yes                 | No                  |
| `suppress_entity`         | Yes           | Yes             | No                  | Yes                 |
| `defer_entity`            | Yes           | Yes             | No                  | Yes                 |

---

## Common Fields

All action intents should include these minimum common fields:

- `action_plan_key`
- `action_intent`
- `subject_type`
- `subject_key`
- `reason_summary`
- `planned_at`
- `execution_mode`

### Common optional fields
- `executor_target`
- `related_decision_keys`
- `dry_run_preview`
- `approval_status`
- `priority`
- `safety_flags`
- `explainability_payload`

---

## Execution Modes

Every action intent should carry one of these execution modes:

- `suggest_only`
- `approval_required`
- `automatic`

### Semantics

#### `suggest_only`
- The action is surfaced, but no executor call is attempted

#### `approval_required`
- The action is held until operator approval

#### `automatic`
- The action may proceed automatically if supported and safe

### Notes
- Some intents are inherently non-executor actions and may still use these modes as workflow state
- Destructive actions should default to more conservative execution behavior in early v1 usage

---

## Relationship to PolicyDecision

Action intents are derived from `PolicyDecision`, but are not the same thing.

### Separation
- A decision is not yet a plan
- One decision may produce multiple action intents
- Some intents may be review-only and never hit an executor
- This separation improves dry-run clarity and auditability

### Example
A policy decision such as:

- `decision_type = acquire`
- `monitoring_recommendation = latest_release_only`

may produce:

- `acquire_artist`
- `set_monitoring_strategy`

A policy decision such as:

- `decision_type = recommend`

may produce:

- `recommend_candidate`

with no execution call

### Example: Artist Deepening by Proven Affinity

A policy decision may determine that an artist has strong proven affinity based on user feedback signals.

That may produce:

- `recommend_candidate`
- `acquire_artist`
- `set_monitoring_strategy`

No new action intent is required; this capability should operate through existing intents.

---

## Relationship to ActionPlan

In v1, action intents are represented inside the `ActionPlan` layer rather than as a disconnected additional object type.

### Practical v1 model
`ActionPlan` should contain:

- the normalized action intent
- the subject
- the reason
- execution mode
- executor target if any
- payload needed for later execution

---

## Generic from Day One vs Lidarr-Specific in v1

## Must stay generic now
- intent names
- subject types
- execution modes
- reason and explainability fields
- suppression and deferral concepts
- monitoring strategy as a product concept

## Can remain Lidarr-specific in v1
- mapping of `acquire_artist` to Lidarr add behavior
- mapping of `set_monitoring_strategy` to Lidarr monitoring options
- mapping of `prune_release` and `prune_artist` to Lidarr delete, unmonitor, and remove semantics
- raw executor payloads and executor operation labels

---

## Explicit v1 Non-Goals

This v1 action-intent schema does not define:

- multiple execution backends
- shopping or purchase flows
- cart export or import actions
- generalized plugin or action marketplace semantics
- advanced batch workflow language
- every future action type Resonarr may ever need

---

## Design Recommendations

### 1. Keep the action-intent set small in v1
This is easier to reason about, easier to audit, and sufficient for MVP workflows.

### 2. Keep `acquire_artist` and `set_monitoring_strategy` separate
Artist admission and monitoring are distinct product decisions.

### 3. Use `prune_release` instead of `prune_album`
“Release” is the more general product term. Lidarr can still map this to album semantics in v1.

### 4. Keep `suppress_entity` and `defer_entity` separate
Suppression means reduce or block resurfacing. Deferral means wait and reconsider later.

### 5. Do not invent backend capability abstractions yet
v1 only needs one real executor. Action intents already provide enough decoupling at the product level.

---

## Not Yet Locked

This draft does not lock:

- exact enum storage format
- exact JSON payload shapes
- exact `ActionPlan` table structure
- exact approval workflow UI
- exact monitoring strategy ranking rules
- exact score thresholds that produce each intent
- exact Lidarr API mapping

---

## Immediate Follow-On Decisions

The next decisions to lock after this document are:

1. First discovery provider choice
2. MVP feedback signal set
3. First scoring dimensions
4. Monitoring preset definitions
5. Automation mode defaults
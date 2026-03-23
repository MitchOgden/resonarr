# Product name / framing

A self-hosted, feedback-driven music discovery and curation engine for Plex/Plexamp + Lidarr.

Initial execution backend is Lidarr, but the product boundary is broader: discovery, scoring/policy, memory, and explainable action planning should remain backend-agnostic from day one. That matches the project goal in the export.

## Problem

Plex/Plexamp + Lidarr users can automate music acquisition, but they still lack a trustworthy loop that:

- discovers likely-good artists/releases
- acquires conservatively
- uses real listening feedback
- prunes weak fits safely
- avoids repeatedly re-adding rejected content

The result today is overgrowth, weak recommendations, and manual cleanup. The product solves that by closing the loop:

**discover → acquire → listen → rate → prune → influence future discovery**

## Target user

Self-hosted users who:

- run Plex/Plexamp
- use Lidarr or are willing to
- want discovery without junk accumulation
- care about explainability, dry-runs, and conservative automation

## MVP goal

Validate that the system can produce a trustworthy, conservative, explainable discovery-and-prune loop using:

- one discovery provider
- Plex feedback
- suppression/cooldown memory
- Lidarr as the only execution backend in v1

## MVP in-scope

### Integrations

- Plex for ratings/feedback ingestion
- Lidarr for acquisition/monitoring/prune execution
- One discovery provider in real use for v1

### Core capabilities

- run discovery against provider + existing library context
- support three discovery modes at the product level:
  - library/play-stat driven
  - behavior/rating driven
  - hybrid
- normalize candidates into a canonical internal model
- score/filter candidates through a policy engine
- support artist deepening by proven affinity as a policy/scoring capability for conservative same-artist expansion
- separate:
  - artist discovery decision
  - monitoring strategy decision
- produce explainable action plans
- execute approved/automatic actions through Lidarr
- ingest Plex ratings and pruning outcomes
- store suppression, cooldown, and rejection memory
- support dry-run for discovery and pruning
- maintain action history / audit trail

### Minimum UI / operator surface

- connection/config screen
- policy settings screen
- dry-run results screen
- action history screen
- suppression/memory management screen

A CLI plus minimal web UI is acceptable for MVP. The export explicitly leaves room for a minimal UI rather than a polished platform first.

## MVP out of scope

- multiple execution backends
- polished dashboards
- complex auth
- multi-user support
- shopping cart / purchase flows
- wishlist exports/imports
- advanced provider blending
- universal rule builder / DSL
- full recommendation-only product mode as a polished end-user experience

These may be designed for later, but should not drive MVP complexity.

## Product defaults

The recommended MVP default is:

- Hybrid discovery
- Conservative monitoring
- Dry-run first
- Cooldowns over permanent bans by default
- Approval or suggest-only available for destructive actions

This follows the export’s preferred direction: hybrid discovery, conservative monitoring, explainability, preview before destructive changes, and cooldowns.

## Core module boundaries

### 1. Discovery Provider Connector

**Responsibility:**

- query one external discovery source
- return raw provider results

**Does not:**

- score candidates
- decide actions
- call Lidarr

### 2. Identity + Normalization

**Responsibility:**

- map provider data into canonical internal entities
- resolve artists/releases using MBIDs/canonical IDs where possible
- link Plex/Lidarr/provider records

**Does not:**

- decide policy
- execute actions

This is explicitly important in the export and should be generic from day one.

### 3. Feedback Ingestion

**Responsibility:**

- ingest Plex ratings and selected listening signals
- ingest pruning outcomes and action results
- produce feedback records usable by policy/memory

**Does not:**

- directly prune
- directly discover

### 4. Memory / Suppression

**Responsibility:**

- store blacklists
- cooldown windows
- rejection history
- prior prune outcomes
- rediscovery suppression state

**Does not:**

- generate candidates
- execute actions

### 5. Policy / Scoring Engine

**Responsibility:**

- evaluate normalized candidates
- support discovery mode behavior
- rank/filter candidates
- decide:
  - discover or reject
  - suppress or allow
  - suggested monitoring strategy
  - recommend / queue / acquire / skip

**Does not:**

- directly call Lidarr
- fetch provider data itself

This is the product core.

### 6. Action Planner

**Responsibility:**

- convert policy results into explicit action intents with reasons
- produce dry-run previews
- attach explainability metadata

**Examples of action intents:**

- `recommend_candidate`
- `queue_for_review`
- `acquire_artist`
- `set_monitoring_strategy`
- `prune_album`
- `prune_artist`
- `suppress_candidate`

This should be generic from day one even though only Lidarr-backed execution exists initially.

### 7. Lidarr Execution Adapter

**Responsibility:**

- translate action intents into Lidarr API calls
- handle Lidarr-specific monitoring/add/delete behavior
- return execution results

This can safely be Lidarr-specific in v1.

### 8. Operator UI / API

**Responsibility:**

- config
- dry-run review
- logs/history
- suppression overrides
- basic run control

**Does not:**

- own business logic

## Core entities

Minimum internal entities:

- Artist
- Release/Album
- Track
- Candidate
- FeedbackSignal
- SuppressionRecord
- PolicyDecision
- ActionPlan
- ActionResult
- RunHistory

## Key workflows

### Discovery workflow

provider input + same-artist affinity inputs → normalization → policy/scoring → dry-run/action plan → Lidarr execution or review

### Feedback/prune workflow

Plex feedback → feedback normalization → prune policy → dry-run/action plan → Lidarr prune execution → memory update

### Closed-loop learning workflow

prune/reject outcomes + ratings + cooldown state → influence future candidate ranking and suppression

## Generic from day one

These must be generic now:

- candidate schema
- identity model
- policy decisions
- action intents
- explainability model
- suppression/cooldown model
- discovery mode framework

## Safely Lidarr-specific in v1

These can stay narrow for MVP:

- execution adapter
- monitoring preset mapping
- add/delete API behavior
- Lidarr matching and fallback behavior
- some UI wording tied to Lidarr

## Success criteria for MVP

MVP is successful if a user can:

- connect Plex, Lidarr, and one discovery provider
- run a discovery dry-run
- understand why candidates were proposed or rejected
- send conservative adds to Lidarr
- ingest Plex feedback
- run a prune dry-run
- safely execute pruning with trust
- avoid immediate rediscovery of rejected content through memory/cooldowns

## Immediate next decisions

The next product/architecture decisions to lock are:

- canonical entity schema
- action-intent schema
- first discovery provider choice
- exact MVP feedback signals from Plex
- first scoring dimensions and weights
- monitoring preset definitions
- automation modes: suggest-only vs approval vs conservative auto

This spec is directly grounded in the attached export’s product framing, discovery modes, provider-agnostic architecture direction, memory/cooldown requirements, pruning logic goals, MVP recommendation, and conservative explainability-first principles.

The best next step is canonical entity schema + action-intent schema, because those two decisions lock most of the clean boundaries for everything else.
# Monitoring Presets (v1 Working Draft)

## Purpose

This document defines the monitoring presets used in MVP for Resonarr.

It establishes:
- how aggressively releases are monitored after acquisition
- default behavior for new artists and deepening
- safety constraints to prevent over-expansion

This document does not define:
- exact Lidarr API payloads
- executor-specific implementation details

---

## Goals

- Ensure conservative, trust-first acquisition behavior
- Prevent uncontrolled library expansion
- Keep monitoring predictable and explainable
- Minimize configuration complexity in MVP

---

## Principles

- Monitoring must be conservative by default
- Only one release should be targeted at a time in MVP
- Monitoring behavior must be explainable
- Monitoring must respect suppression and cooldowns
- Monitoring is a product-level decision, not a backend detail

---

## Preset List (v1)

The following presets are supported in MVP:

- `none`
- `best_release_only`
- `latest_release_only`
- `top_n_releases`

---

## Preset Definitions

### `none`

Behavior:
- Add artist without monitoring any releases

Use cases:
- Suggest-only flows
- Future manual workflows

---

### `best_release_only`

Behavior:
- Select the highest-confidence release
- Monitor only that release

Selection inputs:
- affinity alignment (if applicable)
- provider confidence
- popularity (light weighting)

Notes:
- This is the default preset for MVP
- Designed to be safe and predictable

---

### `latest_release_only`

Behavior:
- Select the most recent release
- Monitor only that release

Use cases:
- Users who prefer staying current
- Less dependent on popularity signals

---

### `top_n_releases`

Behavior:
- Select the top N highest-confidence releases
- Monitor those releases

Requirements:
- Requires parameter `n`

Constraints:
- Intended for controlled expansion
- N should remain small in MVP usage

---

## Default Behavior

### New artist acquisition

Default preset:
- `best_release_only`

Rationale:
- aligns with affinity-driven discovery
- avoids over-expansion
- produces explainable outcomes

---

### Artist deepening

Default preset:
- `best_release_only`

Rationale:
- deepening should remain conservative
- only one additional release should be targeted at a time

---

## Preset Selection Model

In MVP:

- Monitoring presets are fixed, not dynamically scaled by score
- Preset selection is determined by:
  - action type
  - system defaults

Future versions may allow score-based preset selection.

---

## Safety Controls

### Global caps

The system should enforce limits per run:
- maximum number of artists added
- maximum number of releases monitored

Purpose:
- prevent runaway automation
- maintain user trust

---

### Cooldowns

Monitoring must respect cooldown rules:

- recently acquired artist → short cooldown
- recently recommended → short cooldown
- negative feedback → longer cooldown or suppression

---

### Suppression

- hard suppression blocks monitoring entirely
- soft suppression reduces likelihood of monitoring

---

## Relationship to Automation Modes

Monitoring behavior is influenced by execution mode:

- `suggest_only`
  - no monitoring applied

- `approval_required`
  - preset proposed but not executed

- `automatic`
  - preset applied immediately

---

## Explainability

All monitoring decisions must be explainable.

Each action should include:

- selected preset
- reason for selection

Example:

> Monitoring strategy: best_release_only  
> Reason: strong affinity, conservative default

---

## Non-Goals for MVP

This model does not include:

- automatic full catalog monitoring
- dynamic preset selection based on score
- per-user configuration
- per-artist adaptive monitoring behavior

---

## Future Extensions

Possible future enhancements:

- full catalog preset (manual or advanced)
- score-driven preset selection
- per-library configuration
- adaptive behavior based on long-term affinity

---

## Summary

The MVP monitoring model:

- uses a small set of conservative presets
- defaults to single-release acquisition
- avoids aggressive expansion
- respects suppression and cooldowns
- remains fully explainable

The system prioritizes:
- safety
- predictability
- user trust
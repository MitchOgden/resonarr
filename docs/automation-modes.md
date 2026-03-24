# Automation Modes (v1 Working Draft)

## Purpose

This document defines the automation modes used in MVP for Resonarr.

It establishes:
- when actions are executed vs surfaced
- how user interaction controls execution
- how safety and guardrails are enforced

This document does not define:
- scoring behavior
- signal interpretation
- execution adapter implementation details

---

## Goals

- Provide safe and predictable system behavior
- Enable gradual trust-building with the user
- Support both manual and automated workflows
- Keep execution control simple in MVP
- Maintain full explainability across all modes

---

## Principles

- Automation mode controls execution, not decision-making
- Scoring and policy logic remain unchanged across modes
- Safety guardrails must apply in all modes
- Destructive actions require explicit user approval
- All actions must be explainable and auditable

---

## Mode List (v1)

- `suggest_only`
- `approval_required`
- `automatic`

---

## Default Mode

The default mode for new users is:

- `approval_required`

Rationale:
- allows users to review system behavior before trusting automation
- balances usability with safety
- aligns with explainability-first design

---

## Mode Definitions

### `suggest_only`

Behavior:
- no actions are executed
- all action plans are surfaced for review

Monitoring:
- monitoring presets are calculated but not applied

Use cases:
- initial onboarding
- debugging and validation
- recommendation-only workflows

---

### `approval_required`

Behavior:
- action plans are generated
- execution requires user approval

Capabilities:
- batch approval supported
- per-action approval and rejection supported

Monitoring:
- presets are calculated and displayed
- applied only after approval

Use cases:
- standard operating mode
- users building trust in the system

---

### `automatic`

Behavior:
- non-destructive actions execute immediately
- destructive actions require approval

Destructive actions:
- `prune_release`
- `prune_artist`

Monitoring:
- presets applied immediately for non-destructive actions

Use cases:
- trusted environments
- mature system usage

---

## Execution Rules

### Destructive Actions

The following actions always require approval:

- `prune_release`
- `prune_artist`

This behavior is not configurable in MVP.

---

### Non-Destructive Actions

Examples:
- `acquire_artist`
- `set_monitoring_strategy`
- `recommend_candidate`

These may execute automatically depending on mode.

---

## Global Guardrails (All Modes)

The following rules apply regardless of automation mode:

- scoring behavior is unchanged
- suppression rules are always enforced
- cooldowns are always enforced
- global caps are always enforced
- dry-run-style logging is always recorded

---

## Monitoring Behavior by Mode

### `suggest_only`
- monitoring presets are calculated
- not applied

### `approval_required`
- monitoring presets are displayed
- applied only after approval

### `automatic`
- monitoring presets are applied immediately for non-destructive actions
- destructive actions remain gated

---

## Explainability

All actions must include:

- reason summary
- contributing signals
- monitoring preset
- penalties applied (cooldown, suppression, diversity)

Example:

> Recommended because:
> - strong replay across multiple tracks  
> - positive ratings on album  
> - high-confidence candidate  
> - no recent suppression  

---

## Logging and Audit

All modes must produce audit records including:

- action intent
- decision inputs
- explainability details
- execution results (if applicable)

This applies even in automatic mode.

---

## Reversibility (v1)

- all actions are logged with sufficient detail for manual reversal
- automated undo functionality is not included in MVP

---

## User Interaction

### Approval Controls

In `approval_required` mode:

- users can approve multiple actions in batch
- users can approve or reject individual actions

---

### Override Behavior

Users can:
- reject individual actions
- approve specific actions

This allows fine-grained control without introducing complex configuration.

---

## Non-Goals for MVP

This model does not include:

- configurable destructive-action overrides
- disabling of cooldown or suppression rules
- multiple automation profiles
- per-user or per-library automation configurations
- dynamic scoring changes based on mode

---

## Future Extensions

Possible future enhancements:

- configurable automation profiles
- per-library automation settings
- advanced approval workflows
- partial automation (e.g., auto-recommend but manual acquire)
- configurable destructive-action handling

---

## Summary

The MVP automation model:

- provides three clear execution modes
- defaults to approval-required for safety
- enforces strict guardrails across all modes
- separates decision-making from execution
- maintains full explainability and auditability

The system prioritizes:

- user trust
- predictable behavior
- safe automation
- clarity over complexity
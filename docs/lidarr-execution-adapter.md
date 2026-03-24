# Lidarr Execution Adapter (v1 Working Draft)

## Purpose

This document defines how Resonarr executes actions against Lidarr in MVP.

It establishes:
- how action intents map to Lidarr operations
- required data and sequencing
- error handling and safety rules
- expected system behavior and constraints

This document does not define:
- full API implementation code
- advanced Lidarr features beyond MVP scope
- future multi-backend support

---

## Goals

- Execute actions safely and predictably
- Maintain full control over monitoring behavior
- Avoid reliance on undocumented Lidarr behavior
- Ensure idempotent and repeatable operations
- Support explainability and audit logging

---

## Principles

- MBID is required for execution
- Resonarr controls monitoring behavior explicitly
- Actions are executed in deterministic steps
- Destructive actions are conservative and controlled
- Failures must not corrupt system state
- All execution must be auditable

---

## Supported Actions (v1)

The adapter supports the following action intents:

- `acquire_artist`
- `set_monitoring_strategy`
- `prune_release`
- `prune_artist` (optional, conservative use)

---

## Identity Model

### Primary identifier

- MusicBrainz ID (MBID) is required for all execution actions

### Constraints

- Candidates without MBIDs must not be executed
- Such candidates may still be recommended or deferred
- No name-based fallback matching in v1

---

## Execution Flow

### High-level flow

```text
ActionPlan → Adapter → Lidarr API → Response → ActionResult
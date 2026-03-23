# MVP Feedback Signal Set (Working Draft)

## Purpose

This document defines the feedback signals used in MVP for Resonarr.

It establishes:
- which signals are used
- how they are interpreted
- how they contribute to policy decisions
- what is considered positive, neutral, and negative evidence

This document does not define:
- full scoring formulas
- exact weighting values
- final thresholds for all actions

---

## Goals

- Use reliable and explainable signals
- Prioritize explicit user intent where available
- Support conservative, trust-first automation
- Enable both discovery and pruning workflows
- Avoid ambiguous or noisy signals in MVP

---

## Principles

- Explicit signals are stronger than implicit signals
- Implicit signals may reinforce but not override explicit signals
- Unrated content is neutral, not negative
- Negative signals must be explicit in MVP
- Signals should be explainable to the user
- The system should favor safety over aggressive automation

---

## Signal Types

### Explicit signals

#### Rating
User-provided rating on a track.

Role:
- Primary signal for preference
- Only source of negative signal in MVP
- Strongest input for pruning decisions

---

### Implicit signals

#### Play count
Number of times a track has been played.

Role:
- Weak signal on its own
- Input to derived signals
- Not used directly as strong evidence

---

#### Replay density
Derived signal based on repeated listening behavior.

Definition:
- A normalized interpretation of play count relative to expected listening patterns

Role:
- Identifies tracks that are actively revisited
- Stronger than raw play count
- Used for:
  - candidate scoring
  - artist deepening
  - reinforcing positive affinity

---

#### Recency
How recently a track has been played.

Role:
- Modifier signal
- Increases or decreases confidence
- Does not independently determine outcomes

---

## Signal Interpretation

### Positive signals

A track may be considered positive if:

- It has a high rating  
- OR it has strong replay density  

---

### Neutral signals

A track is considered neutral if:

- It is unrated  
- AND has low play count or low replay density  

---

### Negative signals

A track is considered negative only if:

- It has a low rating  

No implicit signals are treated as negative in MVP.

---

## Core Rules

### Rule 1 — Ratings are authoritative
Ratings are the strongest signal and take precedence over all implicit signals.

---

### Rule 2 — No implicit negatives
Low play count, lack of replay, or lack of recency must not be treated as negative.

---

### Rule 3 — Unrated is neutral
Unrated tracks must be treated as neutral across all systems.

---

### Rule 4 — Implicit signals cannot override explicit ratings
Replay or play behavior cannot override a negative rating.

---

### Rule 5 — Play count is not used directly
Play count should only be used as input to replay density or other derived interpretations.

---

### Rule 6 — Recency is a modifier only
Recency should adjust confidence, not act as a gating condition.

---

### Rule 7 — Strong actions require stronger evidence
- Acquisition may be influenced by implicit signals  
- Pruning must require explicit negative signals  

---

## Usage by System Component

### Discovery / candidate scoring

Uses:
- rating
- replay density
- recency

Purpose:
- rank candidates
- identify strong affinity patterns
- support artist deepening

---

### Artist deepening by proven affinity

Uses:
- rating (primary)
- replay density (supporting)
- recency (modifier)

Behavior:
- strong affinity may justify recommending or acquiring another release from the same artist
- implicit signals may contribute, but ratings strengthen confidence

---

### Pruning

Uses:
- rating (primary and required)

Constraints:
- pruning requires explicit negative evidence
- implicit signals alone must not trigger pruning

---

### Suppression / memory

Uses:
- outcomes of actions
- feedback signals as context

Constraints:
- suppression should not be triggered solely by weak or ambiguous signals

---

## Non-Goals for MVP

The following signals are intentionally excluded:

- skip detection
- completion rate
- playlist interaction signals
- implicit negative inference from low engagement
- external behavioral signals beyond Plex

These may be revisited in future iterations.

---

## Future Extensions

Possible future signals:

- skip behavior (if reliable)
- completion percentage
- playlist inclusion/removal
- session-level listening patterns
- multi-user signal separation

These are deferred until signal quality and interpretation can be made reliable.

---

## Summary

MVP feedback is built on:

- rating as the primary and authoritative signal  
- replay density as the strongest implicit signal  
- play count as an input, not a decision signal  
- recency as a confidence modifier  

The system prioritizes:
- explainability
- conservative behavior
- avoidance of false negatives
- trust in automation decisions
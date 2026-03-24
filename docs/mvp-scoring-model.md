# MVP Scoring Model (Working Draft)

## Purpose

This document defines the scoring model used in MVP for Resonarr.

It establishes:
- how candidates are evaluated
- how signals are combined
- how decisions are made
- how explainability is structured

This document does not define:
- exact numeric weights
- finalized thresholds
- implementation-specific scoring formulas

---

## Goals

- Produce consistent and explainable decisions
- Prioritize user preference over provider popularity
- Support conservative, trust-first automation
- Enable both discovery and pruning workflows
- Avoid overfitting or over-complex scoring logic

---

## Principles

- Scoring is gated before it is additive
- Explicit signals are stronger than implicit signals
- Affinity is the most important dimension
- Popularity is supportive, not primary
- Suppression and cooldown must influence outcomes
- The system should remain explainable at all times

---

## Scoring Flow

### Step 1 — Pre-filter (hard rules)

Candidates are filtered before scoring.

Block if:
- entity is hard-suppressed
- entity already exists in the library
- entity fails identity resolution requirements

These candidates do not proceed to scoring.

---

### Step 2 — Affinity Gate

A candidate must meet minimum affinity criteria to be considered.

A candidate passes the gate if:
- it has positive rating evidence  
OR
- it has strong replay density  

If neither condition is met:
- the candidate is deferred without further scoring

---

### Step 3 — Multi-dimensional Scoring

Candidates that pass the gate are evaluated across four dimensions.

---

## Scoring Dimensions

### 1. Affinity (Primary)

Represents how strongly the user appears to like the artist or related content.

Inputs:
- rating (primary)
- replay density (supporting)
- recency (modifier)

Notes:
- ratings carry the highest weight
- replay density reinforces affinity
- recency adjusts confidence but does not gate decisions

---

### 2. Candidate Confidence

Represents how strong the candidate is as a target for acquisition or recommendation.

Inputs:
- provider signal strength (Last.fm)
- release popularity / canonical importance (light weighting)
- identity match confidence

Notes:
- popularity should not override affinity
- popularity is used to select among candidates, not to justify weak affinity

---

### 3. Suppression / Cooldown Modifier

Represents memory-based adjustments to scoring.

Types:

#### Hard suppression (block)
- blacklist
- strong negative feedback
- repeated rejection

#### Soft suppression (penalty)
- recent acquisition
- recent recommendation
- cooldown periods

Notes:
- hard suppression prevents scoring entirely
- soft suppression reduces score but does not block strong candidates

---

### 4. Diversity Penalty

Represents a reduction in score when the same artist is targeted repeatedly.

Purpose:
- prevent over-concentration on a small number of artists
- maintain library diversity

Notes:
- implemented as a soft penalty
- strong affinity can still overcome this penalty

---

## Decision Tiers

Decisions are based on qualitative tiers rather than fixed numeric thresholds.

### Very High Confidence
- eligible for automatic acquisition (if automation mode allows)

### High Confidence
- recommended to the user
- may be auto-acquired depending on automation mode

### Medium Confidence
- deferred or optionally queued for review

### Low Confidence
- ignored or deferred

---

## Action Mapping

Decisions map to action intents:

- `acquire_artist`
- `set_monitoring_strategy`
- `recommend_candidate`
- `queue_for_review`
- `defer_entity`

Action selection depends on:
- score tier
- execution mode (suggest_only, approval_required, automatic)

---

## Artist Deepening by Proven Affinity

### Trigger

Occurs when strong affinity exists for an artist.

Affinity may be based on:
- high percentage of positively rated tracks  
OR
- strong replay density across tracks  

---

### Behavior

- Identify missing releases for the artist
- Select a single best candidate release
- Use candidate confidence (including popularity) to rank options
- Apply standard scoring and decision tiers

---

### Constraints

- Only one release should be targeted at a time
- Popularity is used to select among candidates, not to justify deepening
- Deepening must respect suppression and diversity penalties

---

### Post-action Behavior

After a deepening action:
- apply a short cooldown to the artist
- reduce immediate re-targeting

---

## Pruning Model Integration

Pruning operates under stricter requirements.

### Requirements

- pruning requires explicit negative rating evidence

### Behavior

- remove or unmonitor release
- optionally delete files depending on configuration

### Post-prune Behavior

- create suppression record for the entity
- prevent immediate re-acquisition

Notes:
- pruning must not be triggered by implicit signals alone

---

## Cooldown Model

### After acquisition
- short cooldown on the artist
- prevents immediate repeated acquisition

### After recommendation
- short cooldown to prevent repeated suggestions

### After negative feedback
- longer cooldown or suppression
- reduces future recommendations

### After pruning
- suppression is applied instead of cooldown

---

## Explainability

All decisions must be explainable.

Each decision should include:
- primary contributing factors (e.g., high rating, strong replay)
- supporting factors (e.g., popularity, recency)
- penalties applied (e.g., cooldown, diversity)

Example:

> Recommended because:
> - strong replay across multiple tracks  
> - positive ratings on album  
> - high-confidence release candidate  
> - no recent suppression  

---

## Non-Goals for MVP

This model does not include:

- complex weighting systems
- machine learning models
- advanced behavioral inference (e.g., skip detection)
- cross-provider blending
- multi-user personalization

---

## Summary

The MVP scoring model is:

- gated before additive
- driven primarily by affinity
- supported by candidate confidence
- moderated by suppression and diversity controls
- organized into explainable decision tiers

The system prioritizes:
- trust
- clarity
- conservative automation
- strong alignment with user behavior
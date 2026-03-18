# Open Questions

- What is the canonical internal entity schema for `Artist`, `Release/Album`, `Track`, `Candidate`, `FeedbackSignal`, `SuppressionRecord`, `PolicyDecision`, `ActionPlan`, `ActionResult`, and `RunHistory`?
- What is the v1 action-intent schema, and which intents are generic platform concepts versus Lidarr-backed implementations?
- Which discovery provider should be the first real provider in MVP?
- Which Plex feedback signals are in MVP versus later?
  - ratings only?
  - ratings + play count?
  - ratings + recency?
- What are the first scoring dimensions and their relative weights?
- What exact monitoring policy presets should exist in v1?
- What are the exact automation modes in v1?
  - suggest only
  - approval required
  - conservative automatic
- What should be hard suppression versus cooldown-based suppression?
- What minimum explainability payload must every policy decision and action plan include?
- What minimum approval and override flow is required for destructive actions in MVP?
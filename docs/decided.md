# Decided

## Core decisions

- Initial execution backend is Lidarr, not the permanent product boundary.
- The product is best framed as a feedback-driven music discovery and curation engine for Plex + Lidarr, not just a pruning script with a UI.
- The main loop is: **discover → acquire → listen → rate → prune → influence future discovery**.
- Discovery should support three first-class modes:
  - library/play-stat driven
  - behavior/rating driven
  - hybrid
- Artist discovery and monitoring strategy are separate decisions.
- Discovery, policy/scoring, and backend execution should be treated as separate concerns.
- Explainability, dry-runs, and trust in automation are core product principles.
- Conservative defaults are preferred over aggressive automation.
- Cooldowns and rejection memory are core product behavior, not optional extras.
- The system should use Plex feedback and pruning outcomes to influence future discovery.
- MBIDs / canonical IDs should be used wherever possible for identity resolution across provider data, Lidarr, Plex, and future pruning memory.
- The pruning model should treat unrated tracks as neutral, not as implicit negatives, to avoid overly aggressive pruning.
- Small album / EP / single logic should remain, so fully disliked small releases can still be pruned.
- Artist pruning should only occur when no albums remain or all relevant albums have effectively been removed, not simply because one album performed poorly.
- Dry-run and live mode should share the same decision logic; the difference should only be whether actions are executed.
- The recommended MVP default behavior is hybrid discovery plus conservative monitoring.
- MVP should be minimal and may use a CLI or minimal UI rather than a polished full web app.

## Deferred / Later

- Multiple discovery providers in active production use
- Rich provider blending and advanced weighting across providers
- Multiple execution backends beyond Lidarr
- Recommendation-only mode as a polished user-facing experience
- Wishlist flows
- Purchase recommendation flows
- Shopping cart import/export where feasible
- Full manual review queue experience beyond the minimum needed for MVP
- Polished dashboards and analytics
- Complex auth
- Plex login-based auth design
- Multi-user support
- Rich notifications
- Postgres migration if and when SQLite becomes limiting
- Broader governance and approval workflows beyond MVP basics

These are compatible with the product direction, but they should not drive v1 scope.
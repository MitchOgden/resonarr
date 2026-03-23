# Project context export: Plex/Lidarr discovery + pruning platform

## Project goal

Treat Lidarr as the initial execution backend, not the permanent product boundary.

Build a self-hosted music automation platform for Plex/Plexamp + Lidarr that closes the feedback loop:

**discover → acquire → listen → rate → prune → influence future discovery**

The system should eventually support:
- configurable discovery from multiple providers
- Plex-based feedback ingestion
- automated pruning logic
- memory/cooldowns/blacklists
- optional web UI for configuration, scheduling, and monitoring

This started from combining:
- DiscoveryLastFM-style artist discovery
- Lidarr acquisition/monitoring
- Plex/Plexamp ratings and listening behavior
- a custom pruning script driven by Plex ratings

## Big product idea

This is not just “a pruning script with a UI.”

The product concept is better framed as:

**A feedback-driven music discovery and curation engine for Plex + Lidarr**

### Core value
- turns passive listening behavior into active library management
- uses user taste/ratings to influence both what gets added and what gets removed
- eventually prevents re-adding music the user consistently rejects

### Target users
- Plexamp users
- Lidarr users
- self-hosters
- people who want discovery but hate junk accumulating in their music library

## High-level system concept

### Main loop
- discover candidate artists/albums/tracks
- decide what to add to Lidarr
- decide what gets monitored
- let user listen in Plex/Plexamp
- ingest ratings / listening behavior from Plex
- prune albums/artists based on rules
- use that history to influence future discovery and suppress bad matches

## Artist deepening by proven affinity

Resonarr should support artist deepening based on proven affinity.

When the system detects strong positive evidence for a specific artist through listening or rating behavior, it may recommend or conservatively acquire additional high-confidence releases from that same artist.

This behavior should be:
- explainable
- policy-driven
- conservative by default
- subject to cooldown and diversity controls to prevent over-expansion

## Discovery modes discussed

Discovery should support three first-class modes:

### 1. Library/play-stat discovery
“DiscoveryLastFM style”

Use:
- current artists already in library
- play stats / recency
- similar artists from provider
- top or popular releases from provider

This is breadth-oriented and good for growing the library outward.

### 2. Behavior-based discovery

Use:
- Plex ratings
- prune history
- feedback memory
- user taste signals

This is precision-oriented and should bias toward music that aligns with actual user preferences.

### 3. Hybrid discovery

Use both of the above.

This is probably the best default:
- generate candidates from provider + library graph
- rank/filter them with behavior/rating signals
- monitor conservatively

## Core product distinction

Discovery should separate two decisions:

### A. Discover the artist
Should this artist even enter the system?

### B. Monitoring strategy
If yes, what should Lidarr monitor?
- latest album only
- top 1 album
- top N albums
- studio albums only
- add but don’t monitor until approved
- aggressive/full monitoring

This is important because “add artist” and “download all albums” should not be tightly coupled.

## Provider-agnostic architecture idea

Reimplement the useful behavior of DiscoveryLastFM, but make the provider pluggable.

Do not tightly couple to DiscoveryLastFM’s codebase.

Treat DiscoveryLastFM as:
- proof of useful behavior
- product inspiration
- reference implementation

But not the permanent architecture.

### Desired architecture shape

**providers → normalization → policy engine → Lidarr/Plex actions**

### Provider examples
- Last.fm
- ListenBrainz
- Spotify
- others later

### Internal normalized candidate model

All providers should normalize into one internal schema, for example:
- provider
- provider artist ID
- provider release ID
- artist name
- album/release title
- candidate type (artist / album / track)
- source reason
- confidence score
- MusicBrainz IDs where possible

## Identity resolution

Use MBIDs / canonical IDs whenever possible to map across:
- provider data
- Lidarr
- Plex
- future pruning memory

This is a key part of making the system robust.

## Core functional areas for eventual app

### 1. Discovery
- connect to one or more providers
- run discovery jobs on schedule
- preview candidates before adding
- provider-specific discovery settings
- configurable caps and limits

### 2. Feedback ingestion
- connect to Plex
- import ratings
- potentially use play count / recency / completion later
- map feedback to albums/artists/tracks

### 3. Pruning
- rule engine for albums and artists
- dry-run preview
- execution history / audit trail
- optional approval mode before deletes

### 4. Governance / management UI
- web UI
- logs
- scheduling
- test connections
- config editing
- dry-run status
- action history
- notifications

### 5. Memory / suppression
- blacklist artists/albums
- cooldown windows
- prevent re-adding previously rejected content
- use prune history to reduce rediscovery noise

## Pruning concept we built

A Python script was created to:
- connect to Plex
- read album tracks and ratings
- score albums based on track ratings
- match albums to Lidarr
- unmonitor and delete bad albums
- optionally prune artists if no albums remain

### Core current design
- use Plex track ratings as signal
- roll up track ratings to album-level decision
- use Lidarr API for actual actions
- support dry-run mode
- support small EP/single logic
- support artist pruning only when appropriate

## Pruning logic evolution / rules discussed

### Original issue

The initial logic was too aggressive:
- if only 1 track on an album was rated badly
- and the rest were unrated
- the script treated the whole album as bad

This was not acceptable.

### Improved logic chosen

Keep the small-album rule, but change treatment of unrated tracks.

### Selected behavior

Treat unrated tracks as neutral rather than ignoring them completely.

Effect:
- if 1 track is bad and 9 are unrated
- album ratio becomes 1 bad out of 10 total considered tracks
- so the album is not pruned

### Why this is preferred
- better matches human behavior
- avoids nuking albums based on tiny amounts of evidence
- still lets fully disliked EPs/singles get pruned

### Small album logic should stay

If a small album / EP / single has all its tracks rated badly, it should still be eligible for pruning.

## Current pruning behavior goals

### Albums
- use track ratings to infer album quality
- unrated tracks count as neutral
- if enough of an album is bad, prune it
- if a small release is entirely rated badly, prune it

### Artists
- do not prune just because one album is bad
- only prune artist when no albums remain / all relevant albums have effectively been removed

## Current script configuration ideas

These were important concepts in the script:
- `DRY_RUN` mode to preview actions without deleting
- `MATCH_MODE = "mbid"` preferred
- `ALLOW_NAME_FALLBACK = True`
- `UNRATED_TRACK_STRATEGY = "neutral"` desired
- small-album full-reject logic enabled
- artist prune only if no albums remain
- progress logging during album scan
- optional safety deletion limiter during first live run

## Safety limiter concept

During first live run, cap actual deletions to something like 10, then stop, so mistakes cannot mass-delete the library.

## Important operational behaviors validated

### Dry-run to live mode

Switching off dry-run should only change:
- from logging “would delete”
- to making the actual valid Lidarr API calls

The decision logic should remain identical between dry-run and live mode.

### Expected deletion behavior

The script should:
- unmonitor album
- delete album with files
- remove from Lidarr

### Empty folders issue

If album folders remain but are empty:
- that is not the ideal expected result
- likely causes include hidden Synology files like `@eaDir`
- empty folder cleanup may be needed as a follow-up process

Potential cleanup approach:
- delete empty directories
- optionally clean Synology metadata subfolders if safe

## Web UI concept discussed

There was interest in eventually building a web app around this.

### Possible web app purpose

A single UI for:
- discovery provider config
- DiscoveryLastFM-style runs
- Plex integration
- pruning config
- logs and monitoring
- scheduling
- dry-run previews
- action history
- approvals / governance

### Plex auth idea

Potentially authenticate users via Plex login and use that to simplify setup.

Caution:
- app auth and server token access are related but not identical
- needs a clean auth design, not a hand-wave

## Product framing ideas

The thing that makes this interesting is not just discovery.

It is the combination of:
- discovery
- behavior
- curation
- suppression memory
- explainable automation

## Important product principles
- explainability: every add/remove should say why it happened
- conservative by default
- preview before destructive changes
- cooldowns better than permanent bans in many cases
- dry-run and approval flows increase trust

## Features that felt especially important

### Rejection memory

If an album or artist was pruned/rejected, remember that and prevent easy re-add.

### Cooldowns

Instead of permanently banning everything:
- suppress artists/albums for X days
- reduce provider recommendations from recently pruned artists

### Explainability

Show:
- why artist was discovered
- why album was monitored
- why album was pruned
- which ratings contributed

### Approval modes

Support:
- fully automatic
- suggest only
- require approval for deletes
- require approval for artist prune

## Suggested app architecture direction

### Backend

Python is fine because current logic already exists there.

### Likely stack
- FastAPI backend
- simple frontend
- SQLite first
- Postgres later if needed
- job scheduler / worker for discovery + prune runs
- Docker-first deployment

### Data areas to model
- artists
- albums
- tracks
- provider candidates
- ratings / feedback snapshots
- actions
- rules
- suppressions / cooldowns
- run history

## MVP suggestion

Do not build the entire polished platform first.

### Suggested MVP
- provider interface
- one or two providers (Last.fm + maybe ListenBrainz)
- canonical candidate model
- Lidarr adapter
- Plex feedback ingestion
- pruning engine
- dry-run preview
- suppression memory
- CLI or minimal UI

### Then later
- web UI
- auth
- dashboards
- scheduling
- approval workflows
- richer provider blending

## Recommended product default behavior

Best default likely:
- Hybrid discovery
- Conservative monitoring

Meaning:
- discover from provider + library graph
- rank/filter using ratings/behavior
- only monitor latest album or top 1 release for new artists
- avoid downloading whole discographies immediately

## Practical next-step advice

Best next path from here is probably not continuing this bloated chat for code iteration.

### Recommended split

Use a fresh coding-focused chat or Codex for:
- refactoring the pruning script cleanly
- building a provider interface
- defining the data model
- starting a proper project structure

Use a separate planning/product chat for:
- requirements
- architecture decisions
- UI flows
- naming/positioning
- roadmap

That keeps implementation and concept work from stepping on each other.
<!--
Sync Impact Report
- Version change: (template, unversioned) → 1.0.0
- Modified principles: none (initial adoption)
- Added principles: I. Safety-Bounded Actuation; II. One Contract, Many Clients; III. Field-First
  Mobile; IV. Farm-Scoped Security & Privacy; V. Honest Intelligence; VI. Test the Risky Paths;
  VII. Simplicity & Incremental Delivery
- Added sections: Technology & Platform Constraints; Development Workflow & Quality Gates; Governance
- Removed sections: none
- Templates: plan-template.md / spec-template.md / tasks-template.md read the constitution at
  runtime; no template edits required.
- Deferred TODOs: none
-->

# FARMLINK Constitution

FARMLINK is a smart-farm platform for Tunisian agriculture: a Next.js web dashboard and its mobile
version, a backend that ingests IoT data and controls irrigation hardware, and decision-support
modules (crop planning, crop health, energy, post-harvest, marketplace). ROOTLOOP is its
water-recovery and underground-irrigation subsystem.

## Core Principles

### I. Safety-Bounded Actuation (NON-NEGOTIABLE)

Software that can move water or switch equipment MUST be unable to exceed physical safety limits.

- Hard limits (for example, maximum water per irrigation run and per day) MUST be enforced in
  three places: the device firmware, the backend validation layer, and the UI input bounds. The
  device is the final authority; the backend and UI MUST never assume their own check suffices.
- User-editable thresholds MUST be validated against hard limits on the server; requests that
  exceed them MUST be rejected, not clamped silently.
- Every command sent to a device MUST be authenticated (signed per device), time-bounded, and
  carry a monotonically increasing sequence number that is persisted across server restarts.
- On sensor fault, lost connectivity, or an unverifiable command, devices MUST fail safe
  (actuators off) and the platform MUST surface that state to users.
- Commands that change physical state MUST NOT be queued while a client is offline.

Rationale: a dashboard bug or a replayed request must never flood a field or burn out a pump.

### II. One Contract, Many Clients

The backend's published API schema is the single source of truth for every client.

- The web dashboard and its mobile version MUST consume types and clients generated from the
  backend's OpenAPI schema. Hand-written duplicate request/response types are forbidden.
- Breaking API changes MUST bump the API version and be accompanied by client regeneration in the
  same change.
- Real-time messages and device payloads MUST each have a written, versioned contract under
  `specs/*/contracts/`.

Rationale: the reference code base kept its models twice (Python and Dart) by hand; FARMLINK has
more clients and more entities, so drift would be guaranteed.

### III. Field-First Mobile

Farmers use the product on phones, outdoors, on unreliable networks.

- Every farmer-facing screen MUST be fully usable at 360 px width with touch targets of at least
  44 px, and MUST NOT require horizontal scrolling.
- Read views (latest readings, alerts, history already viewed) MUST remain available offline from
  the last successful sync, with the data age shown.
- Non-actuating writes (photos for scanning, notes, listings) MAY be queued offline and MUST be
  idempotent so retries cannot create duplicates.
- Interfaces MUST support right-to-left layout so that Arabic can be added without redesign.

Rationale: a dashboard that only works on a laptop on Wi-Fi does not reach the people it is for.

### IV. Farm-Scoped Security & Privacy

- Every business record MUST belong to exactly one farm (or be explicitly global reference data),
  and every read and write MUST be authorized on the server against the caller's membership and
  role for that farm. Client-side hiding of controls is never an authorization mechanism.
- Session tokens on the web MUST live in `HttpOnly`, `Secure` cookies; tokens MUST NOT appear in
  URLs (including WebSocket URLs) or in client-readable storage.
- Each device MUST have its own credential; one leaked device key MUST NOT compromise other
  devices or farms. Secrets MUST NOT be committed or shipped to clients.
- Security-relevant events (logins, failed signatures, role changes, commands) MUST be recorded
  in an audit log attributed to a user or device.

Rationale: the platform moves from one greenhouse to many farms with different owners.

### V. Honest Intelligence

- Every AI or rule-based output (plant identification, disease risk, crop recommendation,
  investment estimate) MUST display its confidence or basis, the engine or data source used, and
  an explicit "uncertain" state when below its threshold.
- Recommendations are advisory. The platform MUST NOT apply an AI recommendation to hardware
  without an explicit user action, and that action remains bounded by Principle I.
- Water-quality readings MUST be presented as monitoring indicators, never as certification that
  water is safe for reuse.
- Users MUST be able to correct an AI result, and corrections MUST be stored alongside the
  original output.

Rationale: farmers make financial and food-safety decisions from these screens.

### VI. Test the Risky Paths

- Contract tests MUST exist for every public API endpoint and every real-time message type.
- Automated tests MUST cover, before merge: authentication, per-farm authorization (including
  cross-farm access attempts), device signature verification, command signing and replay
  rejection, and hard-limit enforcement.
- An end-to-end scenario MUST run against the device simulator so the full loop (telemetry in →
  dashboard → command out) is verifiable without hardware.
- Tests for these paths MUST be written before or with the implementation, never deferred.

Rationale: these are the paths where a regression damages crops, equipment, or trust.

### VII. Simplicity & Incremental Delivery

- Each user story MUST be independently shippable and demonstrable.
- New services, data stores, or infrastructure components MUST be justified in the plan's
  Complexity Tracking table, including the simpler alternative that was rejected.
- Prefer one deployable web application and one backend over additional apps until a requirement
  forces otherwise.
- Code from the reference implementation MUST be reused where it meets these principles rather
  than rewritten.

Rationale: the scope (seven modules) is wide; delivery must stay narrow at each step.

## Technology & Platform Constraints

- Web dashboard: Next.js (App Router) with TypeScript in strict mode.
- Mobile: delivered from the same Next.js code base (see the plan for the chosen form). A second
  UI code base requires a constitution amendment.
- Backend: Python, retaining the reference implementation's AI and device-bridge code.
- Persistence choices, hosting, and external data providers are decided in each feature's plan
  and research documents, not here.
- All timestamps are stored in UTC; units are explicit in field names or schemas
  (for example `volume_ml`, `temp_c`).

## Development Workflow & Quality Gates

- Work follows the Spec Kit flow: specify → (clarify) → plan → tasks → implement. Each plan MUST
  pass the Constitution Check before Phase 0 and again after Phase 1.
- Every change is reviewed by at least one other person before merge to `main`.
- CI MUST run lint, type checks (TypeScript and Python), unit tests, contract tests, and the API
  client regeneration check (generated client matches the committed schema).
- Database schema changes MUST ship as forward migrations; destructive migrations require a
  documented data-preservation step.

## Governance

- This constitution supersedes other project conventions. Where a plan conflicts with it, the
  plan MUST either change or record a justified exception in Complexity Tracking.
- Amendments are proposed as a pull request that edits this file, states the version bump and
  its reason, and lists affected specs and plans. Amendments require agreement of the project
  maintainers.
- Versioning: MAJOR for removing or redefining a principle; MINOR for adding a principle or
  materially expanding guidance; PATCH for clarifications.
- Compliance is checked at plan review (Constitution Check) and at code review. Reviewers SHOULD
  cite the principle number when requesting changes.

**Version**: 1.0.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21

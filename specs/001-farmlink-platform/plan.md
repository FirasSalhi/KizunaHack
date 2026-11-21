# Implementation Plan: FARMLINK Platform — Web Dashboard and Mobile Version

**Branch**: `001-farmlink-platform` | **Date**: 2026-11-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-farmlink-platform/spec.md`

## Summary

Build FARMLINK as **one Next.js application** that serves both the desktop dashboard and the
mobile version (installable PWA), backed by the reference repository's **FastAPI** backend,
restructured for many farms and devices and moved from SQLite to **PostgreSQL + TimescaleDB**.
The reference Flutter app is used as the design and behavior reference; its backend code
(plant identification, MQTT bridge, simulator, validation rules, HMAC command signing) is ported.
A typed API client generated from FastAPI's OpenAPI schema is the only way the web app talks to
the backend. Delivery proceeds story by story: live monitoring (US1) is the MVP; safe control
(US2) and farm/device management (US3) follow; ROOTLOOP water loop, plant scanning, offline,
energy, crop planning, post-harvest and marketplace come after.

## Technical Context

**Language/Version**: TypeScript 5.x (strict) on Node.js 22 LTS; Python 3.12

**Primary Dependencies**: Next.js 15 (App Router), React 19, Tailwind CSS, shadcn/ui (Radix),
TanStack Query, Recharts, next-intl, Serwist, react-hook-form + zod, openapi-typescript +
openapi-fetch · FastAPI, Pydantic v2, SQLAlchemy 2 (async, asyncpg), Alembic, argon2-cffi, PyJWT,
cryptography (AES-GCM for device keys), paho-mqtt, onnxruntime + reference `plant_id` stack

**Storage**: PostgreSQL 16 with TimescaleDB (hypertables for readings/status, continuous
aggregates); S3-compatible object storage for photos (local directory in development);
IndexedDB on the client for offline cache and scan queue

**Testing**: pytest + httpx + Schemathesis (contract) + containerized Postgres; Vitest + Testing
Library; Playwright (desktop and 360×800 projects); device simulator for end-to-end

**Target Platform**: Linux containers for the backend; evergreen desktop browsers; Android Chrome
and iOS Safari (16.4+) as installed PWA

**Project Type**: Web application (Next.js frontend + Python API) with IoT device integration

**Performance Goals**: reading → open dashboards ≤ 3 s p95 (SC-001); overview first load ≤ 3 s
on 4G (SC-002); offline open ≤ 2 s (SC-006); scan result ≤ 10 s p90 (SC-008); history queries
≤ 300 points per series

**Constraints**: hard water limits enforced in device, API and UI (Principle I); same-origin
deployment for cookie auth over REST and WebSocket; no commands queued offline; RTL-capable
layouts; 360 px minimum width

**Scale/Scope**: no target user or device counts were given. Design assumption for capacity
checks only: tens of farms, hundreds of devices, 5 s reporting interval. Revisit with real
numbers (see research D3 "would change if").

## Architecture

```
            ┌───────────────────────── one origin: https://app.example ─────────────────────────┐
 Browser /  │  Reverse proxy (Caddy)                                                             │
 installed  │   ├── /            → Next.js (apps/web): RSC pages, PWA shell, service worker      │
 PWA ───────┼──►├── /api/v1/*    → FastAPI (services/api): REST, auth, authz, validation        │
            │   └── /ws/v1       → FastAPI WebSocket (cookie-authenticated)                      │
            └───────────────────────────────────────────────────────────────────────────────────┘
                         Next.js server ──(forwards cookie)──► FastAPI (server-side data fetch)

 FastAPI ──► PostgreSQL + TimescaleDB  (relational + hypertables + LISTEN/NOTIFY fan-out)
         ──► Object storage (scan photos)
         ──► Plant ID engines (Pl@ntNet API → BioCLIP 2 → verdant)   [ported reference code]
         ◄─► MQTT broker (Mosquitto, TLS, per-device ACL) ◄─► ESP32 devices / simulator
         ◄── Signed HTTP fallback from devices
```

**How the reference models map** (details in [data-model.md](./data-model.md)):

| Reference | FARMLINK backend (SQLAlchemy / Pydantic) | Web (generated TS) |
|---|---|---|
| `users.role` global | `Membership.role` per farm | `Me.memberships[]` |
| `telemetry` fixed columns | `Reading` (channels) + `DeviceStatus` | `ReadingSeries`, `DeviceStatus` |
| `settings` key-value | `IrrigationSettings` + `HardLimitProfile` | `IrrigationSettings`, `HardLimits` |
| in-memory counter / deque | `Command` + `Device.next_command_seq` | `Command` |
| `events` | `Event` (+ `farm_id`) | `Event` |
| `plant_scans.result` JSON | `PlantScan.ai_result` / `corrected_result` JSONB | `PlantScan`, `PlantIdResult` |
| Dart `AppUser`, `Telemetry` | — (deleted; generated instead) | generated |

**Authentication and access** (research D4): FastAPI issues a 15-minute access JWT and a rotating,
revocable 30-day refresh token, both in `HttpOnly; Secure; SameSite=Lax` cookies, plus a
double-submit CSRF token. Desktop and installed PWA share this mechanism because everything is on
one origin. The WebSocket authenticates with the same cookie. Every route resolves the target's
farm and checks the caller's membership role on the server (`viewer < operator < owner`).
Devices authenticate with their own HMAC secret. A bearer-token mode exists only for a possible
future native shell.

## Decisions to make, in order

| # | Decision | Recommendation | Status | Depends on |
|---|---|---|---|---|
| 1 | Backend framework | FastAPI (keep reference) | Recommended — confirm | — |
| 2 | Code reuse permission for `is9ini` | Ask the author | **Decided** — team's own code (OQ-6) | — |
| 3 | Mobile delivery | PWA from Next.js with web push | **Decided** (OQ-3) | 1 |
| 4 | Database | PostgreSQL 16 + TimescaleDB | Recommended — confirm hosting supports it | 1 |
| 5 | Auth model | Same-origin cookies, FastAPI-owned identity | Recommended | 1, 3 |
| 6 | Hosting | Containers + reverse proxy; provider open | **OPEN (OQ-4)** | 3, 4, 5 |
| 7 | Languages at launch | FR + Derja + EN, RTL-ready | **Decided** (OQ-1); Derja script open (OQ-9) | — |
| 8 | Hardware profiles and hard limits | Greenhouse = 150/600 ml; others with hardware team | **OPEN (OQ-8)** | — |
| 9 | External data sources (weather, prices) | FAO EcoCrop now; others TBD | **OPEN (OQ-7)** — blocks US8/US10 with real data | — |
| 10 | Marketplace scope | Listings + contact | **OPEN (OQ-2)** | — |

Decisions 1–5 must be settled before Phase 2 (Foundational) starts. 6 is needed before the first
deployment, not before development. 7–10 are needed only by the stories that use them.

## Highest-risk parts of the build

| Risk | Why it is risky | Mitigation in this plan |
|---|---|---|
| R1. Multi-tenancy retrofit | Every reference table and endpoint is global; one missed `farm_id` check leaks data | Single `require_farm_role` dependency; cross-farm tests for **every** endpoint generated from the OpenAPI route list (T-tasks in Phase 2 and each story) |
| R2. Safety of remote actuation | Wrong bounds or a replay can over-water or run a dry pump | Three-layer limits; DB check constraints; persisted `seq`; replay tests; firmware contract requires independent limits |
| R3. Real-time across instances | Reference `Hub` is in-process; breaks with >1 API instance or restart | Postgres LISTEN/NOTIFY fan-out; polling fallback in client |
| R4. iOS PWA limits | No background sync; push only when installed; storage eviction | Queue flush on open/online; web push requires home-screen install on iPhone, so the install prompt explains it; in-app alerts remain the fallback |
| R5. Offline writes | Duplicate scans, stale sessions | Idempotency keys; only non-actuating writes are queued; re-auth before flush |
| R6. ML footprint | Full models ≈ 2 GB; slow cold start; may not fit cheap hosting | `PlantIdentifier` interface; engine selection by config; small-model mode |
| R7. Data quality of advice | Crop/price data may be missing or outdated; low-cost sensors (pH, NPK) unreliable | Show source and date; `is_sample` flag; "indicator, not certification" wording (Principle V) |
| R8. Reuse rights | Reference repo has no licence | Resolved: team's own code (OQ-6); add a LICENSE |
| R9. Device credential handling | HMAC needs plaintext secret on server | AES-GCM encrypted at rest, key from environment/secret store, rotation endpoint |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Pre-research | Post-design |
|---|---|---|---|
| I. Safety-Bounded Actuation | Limits in device + API + UI; signed, time-bounded, persisted-seq commands; no offline command queue | ✅ planned | ✅ `IrrigationSettings` constraints, `Command.seq`, device contract step 4, FR-019 |
| II. One Contract, Many Clients | Generated TS client; versioned realtime & device contracts | ✅ | ✅ `packages/contracts`, contracts/*.md, CI `contracts:check` |
| III. Field-First Mobile | 360 px, offline read, idempotent queued writes, RTL | ✅ | ✅ PWA (D2), IndexedDB queue, logical CSS, next-intl |
| IV. Farm-Scoped Security | Server authz per farm; HttpOnly cookies; per-device keys; audit | ✅ | ✅ D4, `AuditEntry`, 404-for-foreign-farm rule |
| V. Honest Intelligence | Confidence, engine, uncertain state; advisory only; corrections stored | ✅ | ✅ `PlantScan.ai_result` immutable, `MarketPrice.is_sample`, apply via settings path |
| VI. Test the Risky Paths | Contract + security suites before merge; simulator E2E | ✅ | ✅ test tasks in every phase; quickstart suites |
| VII. Simplicity | One UI app, one backend; extra components justified | ⚠️ see Complexity Tracking | ✅ justified below |

Result: **PASS** with justified complexity.

## Project Structure

### Documentation (this feature)

```text
specs/001-farmlink-platform/
├── plan.md              # This file
├── research.md          # Decisions D1–D12, reuse map, open questions
├── data-model.md        # Entities, constraints, reference mapping
├── quickstart.md        # Validation scenarios Q1–Q18
├── contracts/
│   ├── rest-api.md
│   ├── realtime.md
│   └── device-protocol.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
apps/web/                         # Next.js 15 — dashboard + PWA (the only UI)
├── src/app/
│   ├── [locale]/(auth)/login/  invite/[token]/
│   ├── [locale]/(app)/farms/[farmId]/
│   │   ├── page.tsx                 # overview (US1)
│   │   ├── devices/[deviceId]/      # device detail, history, control, settings
│   │   ├── events/  alerts/  water/  energy/  storage/
│   │   ├── scans/  scans/[scanId]/
│   │   ├── planning/  members/  fields/  devices/new/
│   ├── [locale]/(app)/market/
│   ├── manifest.ts  sw.ts
├── src/components/{ui,layout,dashboard,charts,control,water,scan,market}/
├── src/lib/{api,auth,realtime,offline,platform,i18n,format}/
├── messages/{en,fr}.json
└── tests/{unit,e2e}/

services/api/                     # FastAPI — ported and restructured reference backend
├── app/
│   ├── main.py
│   ├── core/{config,db,logging,errors}.py
│   ├── security/{passwords,tokens,sessions,csrf,authz,device_keys,command_signing}.py
│   ├── models/*.py               # SQLAlchemy
│   ├── schemas/*.py              # Pydantic (OpenAPI source)
│   ├── routers/*.py
│   ├── services/*.py
│   ├── ingest/{pipeline,mqtt_bridge,http_device,v1_adapter}.py
│   ├── realtime/{hub,notify,messages}.py
│   ├── ml/{plant_id,identifier}.py
│   ├── storage/objects.py
│   └── seed.py
├── migrations/                   # Alembic
└── tests/{unit,integration,contract,security}/

packages/contracts/               # generated OpenAPI types + realtime zod schemas
tools/simulator/                  # ported simulator with profiles
tools/catalog/                    # ported build_catalog.py, download_models.py
infra/{docker-compose.yml,Caddyfile,mosquitto/}
```

**Structure Decision**: monorepo with one UI app, one API service, one generated-contract
package and two tool folders (research D5). The Flutter app is not imported.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| TimescaleDB extension | FR-011 retention + downsampled history for many channels | Plain tables need a hand-written downsampling job; fallback kept if hosting lacks the extension (D3) |
| MQTT broker | Low-power devices, push commands, reference already uses it | HTTP-only polling adds command latency and device power use; HTTP remains as fallback |
| Reverse proxy | Same-origin cookies for REST **and** WebSocket | Next.js rewrites do not proxy WebSockets; cross-origin cookies weaken CSRF posture |
| `packages/contracts` | Principle II generated client + CI drift check | Generating into `apps/web` hides the contract from the simulator/tests and from a future native shell |
| Object storage interface | Photos must survive multiple instances | Local disk (reference) breaks with more than one API instance |

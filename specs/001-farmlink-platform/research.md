# Research & Decisions: FARMLINK Platform

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-21

This document records each decision the plan depends on. Decisions are listed **in the order they
should be made**, because later ones depend on earlier ones. Each has a recommendation, the
alternatives, and what would change the recommendation. Items marked **OPEN** are not decided.

---

## 0. What the reference repository actually is

Reviewed: `RaziSnihaa/is9ini` at its default branch (cloned 2026-11-21).

| Part | Technology | Size |
|---|---|---|
| `backend/` | Python, FastAPI, SQLite (raw `sqlite3`), PyJWT, paho-mqtt, onnxruntime | ~1,100 lines |
| `mobile/` | **Flutter / Dart** (Android, iOS, web, Windows targets) | ~2,900 lines in `lib/` |
| `docs/` | AI report (French), presentations | — |

There is **no Next.js or TypeScript code** in the reference. Its *interface layer* is therefore
reusable as **design and behavior reference** (screens, flows, tokens, copy), not as code. Its
*backend* is reusable as code. This drives D1 and D2.

> ✅ OQ-6 answered 2026-11-21: the repository is the team's own code, so it may be reused freely.
> It still has no LICENSE file; adding one is recommended. Ported files keep a header naming
> their origin.

### 0.1 Reuse map — where each piece falls short of a dashboard + mobile product

**Backend modules**

| Reference file | Reuse | Shortfall for FARMLINK |
|---|---|---|
| `app/plant_id.py` (631 lines) | **Port as is** behind a service interface | Module-level state and model loading at import; ~2 GB models in "full" mode; ties result shape to its own dict format (needs a Pydantic schema). |
| `app/security.py` | **Keep the ideas, rewrite** | One global `DEVICE_KEY` and `COMMAND_KEY` for all devices; command counter is in memory (`itertools.count(time)`) so it is per-process and not shared between instances; JWT bearer for 12 h with no refresh or revocation. |
| `app/main.py` | **Split into routers/services** | One 370-line file; `CORS allow_origins=["*"]`; in-memory WebSocket `Hub` and `pending_http_commands` deque (lost on restart, broken with >1 instance); WebSocket token in the query string; no farm or device scoping on any endpoint; `owner_only` is a global role. |
| `app/db.py` | **Replace** | SQLite with a global lock; single global `settings` key-value table; `telemetry` has fixed columns (soil/temp/hum/light) and **no device id**; `events` and `plant_scans` have no farm id; users seeded from env only. |
| `app/mqtt_bridge.py` | **Adapt** | Fixed topics (`is9ini/telemetry`) without device id; no per-device authentication on MQTT payloads. |
| `simulator.py` | **Adapt** | Single device, greenhouse channels only; needs per-device key and ROOTLOOP/energy/storage profiles. |
| `build_catalog.py`, `download_models.py` | **Keep** | Paths and output locations need to move to object storage or a model volume. |
| Pydantic `Telemetry`, `SettingsIn`, `CommandIn` | **Keep validation rules** | Ranges are good (soil 0–100, temp −20–80, caps ≤150/600 ml); must become per-channel and per-hardware-profile. |

**Mobile screens and widgets (Flutter → design reference for Next.js)**

| Reference | Reuse in Next.js | Shortfall |
|---|---|---|
| `theme.dart` (`AppColors`, `Mood` enum, colors per mood) | **Port tokens** to the web theme (green palette, mood colors, Poppins, 18 px radius, soft shadow) | No dark mode; no RTL consideration; colors hard-coded. |
| `login_screen.dart` | Flow and copy | Asks the user to type a **server URL** (dev convenience — must disappear); no invite acceptance, no password reset. |
| `home_shell.dart` | Bottom navigation concept | 4 tabs with "Control" and "Settings" as "coming soon"; no farm switcher; no desktop layout (sidebar). |
| `dashboard_screen.dart` (445 lines) + `plant_mascot.dart` | Layout, mood card, metric tiles, "x s ago" freshness | One device, four hard-coded metrics; must render from a device's **declared channels**; no field/device selector; no charts. |
| `scan_screen.dart` | Flow: pick/take photo → result | `image_picker` → web uses `<input type="file" accept="image/*" capture="environment">`; no offline queue; no idempotency. |
| `plant_result_view.dart` (642 lines) | **Port structure** (species, confidence, health, alternatives, care sheet, "apply settings") | Large single widget; must become small components; uncertainty display must follow Principle V. |
| `history_screen.dart` | Scans + events tabs, scan detail, correct/delete | Fixed `limit=100`, no pagination, no filters, no farm scoping. |
| `live_feed.dart` | **Port logic**: WebSocket with 4 s polling fallback and 3 s reconnect | Only telemetry messages; no per-farm subscription; no backoff. |
| `session.dart` | Restore session on start, check `/api/me` | Stores the JWT in `SharedPreferences` (readable storage) — replaced by HttpOnly cookies on web. |
| `api/models.dart` (`AppUser`, `Telemetry`) | Field names | Hand-written duplicate of backend models (violates Principle II); `role` is global. |
| `api/api_client.dart` | Endpoint list | Hand-written; replaced by a generated client. |

---

## D1. Backend framework — **Decided (recommended): keep Python + FastAPI**

**Decision**: FastAPI (Python 3.12), restructured into routers, services and a data layer;
SQLAlchemy 2 (async) + Alembic for persistence; Pydantic v2 schemas as the API contract source.

**Rationale**
- The heaviest reusable assets are Python: plant identification (ONNX/BioCLIP, Pl@ntNet client),
  catalog building, MQTT bridge, simulator, and the future sensor "mood" model (Random Forest).
- FastAPI generates OpenAPI from Pydantic models, which gives Principle II (generated TS client)
  for free.
- A long-lived process is needed for the MQTT subscription and WebSocket fan-out; serverless
  Next.js route handlers are a poor fit for both.

**Alternatives considered**
- *Next.js route handlers / server actions as the whole backend (TypeScript end-to-end)*: one
  language and shared types without generation, but ML and MQTT would still need a Python
  service, so you end up with two backends anyway.
- *NestJS or Express*: same problem as above, plus rewriting working code.
- *Django + DRF*: good admin and auth, but heavier, and async/WebSocket support is less direct
  than FastAPI's; would discard the working FastAPI code.

**Would change if**: the AI features are dropped or moved to a hosted API, and the team prefers a
single TypeScript code base → then Next.js + a small worker for MQTT becomes competitive.

---

## D2. How the mobile version is delivered — **Decided: installable PWA from the same Next.js app, with web push (OQ-3 answered 2026-11-21)**

| Option | What it is | Code sharing with web | Camera | Offline | Push when app closed | Distribution | Effort |
|---|---|---|---|---|---|---|---|
| **A. Responsive web** | Same Next.js app, mobile layouts | 100% | Yes (file input with `capture`) | Weak (no service worker) | No | URL | Lowest |
| **B. PWA** (A + manifest + service worker) | Installable to home screen, offline cache | 100% | Yes | Read cache; write queue via IndexedDB | Android: yes. iOS: only when installed to home screen (iOS 16.4+) | URL + "Add to Home Screen" | Low–medium |
| **C. Native wrap** (Capacitor around the Next.js build) | Same UI in a native shell, store-distributed | ~95% (needs static export or remote URL mode, native plugins) | Native | Native storage | Yes (APNs/FCM) | App Store / Play Store | Medium–high (store review, signing, two release pipelines) |
| **D. Keep the Flutter app** | Extend the reference mobile app | **0%** with Next.js (Dart vs TypeScript) | Native | Native | Yes | Stores | Highest (two UIs, two model sets) |

**Recommendation**: **B — PWA**, built so that **C** remains possible later.

- It is the only option that satisfies "share as much logic, types and UI conventions as
  practical" *fully*: one code base, one generated API client, one design system.
- Everything in US1–US6 works in a PWA: live data, camera capture, offline read cache, offline scan
  queue, installability.
- The constitution forbids a second UI code base without amendment, which rules out D unless
  you decide otherwise.

**Tradeoff you are accepting**: on iPhone, background behavior is limited — there is no reliable
background sync, and push requires the user to install the app to the home screen first. If
alerts must reliably reach farmers whose app is closed (OQ-3), or a store listing is required for
trust/discoverability, move to **C (Capacitor)**. The plan keeps that path open by: (1) keeping
all API calls behind the generated client, (2) isolating camera, storage and notifications behind
small adapters (`src/lib/platform/*`), and (3) supporting bearer tokens in the API alongside
cookies (needed for a native shell, which runs on a different origin).

**What happens to the Flutter app**: it stays in the reference repository as a design reference.
No new FARMLINK features are built in it. (OQ-5 if your team wants to keep it.)

---

## D3. Database — **Recommended: PostgreSQL 16 + TimescaleDB extension**

**Data shapes in play**
1. **Relational, farm-scoped** records with strong integrity: users, farms, memberships, fields,
   devices, settings, commands, listings — needs foreign keys, unique constraints, check
   constraints (e.g., `soil_dry_pct < soil_wet_pct`) and transactions.
2. **Time series**: readings from many channels on many devices, queried by time range and
   downsampled for charts (the reference already downsamples to ≤300 points in Python).
3. **Semi-structured documents**: plant-scan AI results and care sheets (nested JSON in the
   reference), recommendation run inputs/outputs.
4. **Reference data**: crop profiles (FAO EcoCrop, 2,568 crops), compatibility pairs, prices.
5. (Later) **Geospatial**: field boundaries.

PostgreSQL covers 1, 3 (JSONB) and 4 natively; TimescaleDB adds hypertables, automatic retention,
and continuous aggregates for 2 (FR-011: 30 days full resolution, longer downsampled); PostGIS can
be added for 5 without changing databases. `LISTEN/NOTIFY` also gives a no-extra-infrastructure
way to fan out real-time messages across API instances (D6).

**Alternatives considered**
- *Stay on SQLite*: fine for one greenhouse; fails at concurrent writes from many devices and
  multiple API instances; no hypertables.
- *Firebase/Firestore* (suggested in the FARMLINK brainstorm): good offline sync and realtime,
  but weak at relational integrity and authorization across farms, time-series aggregation, and
  would bypass the FastAPI layer that holds the safety rules (Principle I).
- *Supabase*: is PostgreSQL; acceptable as a hosting choice for D3 later, but its auth and
  row-level-security model would duplicate FastAPI's authorization — use only as managed Postgres.
- *MongoDB*: convenient for scan documents, worse for everything else here.
- *Separate time-series DB (InfluxDB)*: a second data store to operate; justified only at much
  larger scale.

**Would change if**
- The product stays a single-site demo → SQLite remains enough (but the plan's multi-farm model
  still applies).
- Sensor volume grows to the order of thousands of devices at second-level rates → evaluate a
  dedicated time-series store or a managed Timescale service.
- The hosting provider cannot run the TimescaleDB extension → plain PostgreSQL with native
  partitioning + a scheduled downsampling job (the schema in data-model.md works either way).
- Offline-first multi-device editing of the same records becomes core → consider a sync engine
  (e.g., a Postgres-backed sync layer) rather than changing the database.

---

## D4. Authentication and access across web and mobile — **Recommended**

**Decision**
- FastAPI owns identity: users, password hashes (Argon2id), sessions, memberships.
- **Same-origin deployment**: a reverse proxy serves Next.js at `/` and FastAPI at `/api` and
  `/ws` on the **same domain**. This means the browser — desktop or installed PWA — sends the
  session cookie to FastAPI directly; no token handling in JavaScript.
- **Session model**: short-lived access token (15 min, signed JWT) + rotating refresh token
  (30 days, stored hashed in `sessions`, revocable). Both in `HttpOnly; Secure; SameSite=Lax`
  cookies; refresh cookie scoped to `/api/auth/refresh`.
- **CSRF**: `SameSite=Lax` plus a double-submit token (`csrf_token` cookie mirrored in an
  `X-CSRF-Token` header) for all state-changing requests.
- **Next.js server components** forward the incoming cookie when fetching from FastAPI on the
  server; Next.js middleware only checks cookie presence for redirects — authorization stays in
  FastAPI (Principle IV).
- **WebSocket**: authenticated by the same cookie at upgrade (same origin) — removes the
  reference's token-in-URL. Server re-checks membership on subscribe and closes sockets on
  membership removal.
- **Authorization**: one dependency `require_farm_role(min_role)` resolves `farm_id` from the
  path or the target record, loads the membership, and enforces the role. Role order:
  `viewer < operator < owner`. Device-scoped routes resolve the device's farm first.
- **Devices**: per-device secret (32 bytes), stored encrypted with a server key (needed because
  HMAC requires the plaintext secret), shown once at registration; key version supports rotation.
- **Native shell path (if D2 becomes C)**: the same endpoints accept `Authorization: Bearer`
  with tokens kept in the OS secure store; refresh works the same way.

**Alternatives considered**: Auth.js/NextAuth in Next.js (would split identity between Next.js
and FastAPI and make device/WebSocket auth harder); a hosted identity provider (Auth0, Clerk,
Supabase Auth) — reasonable later if social/phone login is needed, at the cost of an external
dependency and per-user pricing; keeping the reference's bearer JWT in client storage (violates
Principle IV).

---

## D5. Repository layout and shared code — **Recommended: one monorepo, pnpm workspaces**

```
apps/web          Next.js dashboard + PWA (the only UI)
services/api      FastAPI backend (ported reference backend)
packages/contracts Generated OpenAPI types + realtime message schemas (TS)
tools/simulator   Device simulator (Python)
infra/            docker-compose, reverse proxy config
```

Rationale: Principle II needs a place where the generated client lives and a CI check that it is
current; Principle VII argues against more packages (no separate `ui` package while there is
only one UI app). Turborepo is optional; plain pnpm scripts are enough at this size.

---

## D6. Real-time delivery — **Recommended: WebSocket from FastAPI + Postgres LISTEN/NOTIFY**

- Clients open one WebSocket and subscribe to a farm; the server pushes `reading`,
  `device_status`, `event`, `alert` messages (see [contracts/realtime.md](./contracts/realtime.md)).
- Ingest writes to the database and issues `NOTIFY farm_<id>`; each API instance listens and
  forwards to its connected clients. This replaces the reference's in-process `Hub`.
- Client keeps the reference's resilience pattern: polling fallback while the socket is down,
  reconnect with backoff.

Alternatives: Server-Sent Events (simpler through proxies, one-way is enough for most needs; a
reasonable swap if WebSockets cause proxy issues); Redis pub/sub (adds infrastructure; adopt only
if NOTIFY payload limits or throughput become a problem).

---

## D7. Device protocol — **Recommended: keep MQTT + signed HTTP fallback, version 2 payloads**

- Topics become per device: `farmlink/v2/{device_id}/readings`, `/status`, `/events`, `/cmd`.
- Payloads carry a `channels` map instead of fixed fields, so ROOTLOOP, energy and storage devices
  use the same pipeline.
- HTTP fallback: `X-Device-Id`, `X-Signature` (HMAC-SHA256 of the raw body with that device's key).
- Commands: `{cmd, value, ts, seq, sig}`, `seq` persisted per device in the database
  (`devices.next_command_seq`), so it survives restarts and multiple instances.
- Details: [contracts/device-protocol.md](./contracts/device-protocol.md).
- A **v1 compatibility adapter** accepts the reference payload so existing firmware/simulator keep
  working during transition.

---

## D8. Web stack details — **Recommended**

| Concern | Choice | Why |
|---|---|---|
| Styling / components | Tailwind CSS + shadcn/ui (Radix primitives) | Accessible primitives, logical CSS properties for RTL, easy to port reference tokens |
| Server state | TanStack Query | Caching, retries, persistence to IndexedDB for offline read |
| Charts | Recharts | Sufficient for time-series lines/areas; small API |
| i18n | next-intl | App Router support, RTL `dir` per locale |
| PWA / service worker | Serwist (`@serwist/next`) | Maintained successor to `next-pwa` patterns |
| Offline write queue | IndexedDB queue flushed on `online`/app open (not Background Sync, unsupported on iOS Safari) | Works on all target browsers |
| Forms / validation | react-hook-form + zod (zod schemas generated or derived from OpenAPI types) | Same bounds as server in the UI (Principle I, third layer) |
| API client | `openapi-typescript` + `openapi-fetch` | Typed client generated from FastAPI's OpenAPI |

---

## D9. AI model hosting — **Recommended: same backend code base, optional separate process**

The plant scanner loads large models. Run it in the API process for development (as the
reference does) but behind `PlantIdentifier` service interface and a `PLANT_ENGINE` setting, so it
can run as a separate process or be reduced to the Pl@ntNet API + small offline model in
constrained hosting. Photos move from local disk to an object-storage interface (local directory
in development; S3-compatible in production).

---

## D10. Testing strategy — **Recommended**

- Backend: pytest, httpx `AsyncClient`, a real PostgreSQL+Timescale in a container for integration
  tests; Schemathesis property tests against the OpenAPI schema for contract coverage.
- Web: Vitest + Testing Library for components and hooks; Playwright for end-to-end with a
  360×800 mobile viewport and desktop viewport, against the API with the simulator running.
- Required-before-merge suites per Principle VI: auth, cross-farm authorization, device signature,
  command signing/replay, hard limits.

---

## D11. Hosting and deployment — **OPEN (OQ-4)**

Not decided by the request. The plan only requires: a container runtime for FastAPI (long-lived
process), PostgreSQL with TimescaleDB (or fallback per D3), an MQTT broker (Mosquitto) if MQTT is
used, object storage for photos, and a reverse proxy providing the same-origin layout from D4.
Development uses docker-compose. Choosing Vercel for Next.js is possible but breaks the
same-origin layout unless `/api` is rewritten to the backend — the rewrite approach works for REST
but not for WebSockets, so a single reverse proxy in front of both is simpler.

---

## D12. External data for decision support — **OPEN (OQ-7)**

| Need | Candidate | Status |
|---|---|---|
| Crop profiles (water, climate, root depth) | FAO EcoCrop (already used by the reference) | Usable now |
| Weather history / forecast | A free weather API (e.g., Open-Meteo) | To verify terms and coverage of Tunisian regions |
| Market prices | Tunisian public agricultural market data (source to be identified and verified) | **Unknown** — sample data until confirmed |
| Satellite vegetation indices | Copernicus Sentinel-2 | Out of scope for this plan's tasks |
| Storage ranges per crop | Curated table from published post-harvest guidance | To compile |

---

## Open Questions (consolidated)

| ID | Question | Affects | Default until answered |
|---|---|---|---|
| OQ-1 | Interface languages at launch (EN / FR / AR)? | i18n tasks, RTL QA | **Decided 2026-11-21**: FR + Tunisian Derja (`aeb`) + EN, RTL-ready |
| OQ-2 | Marketplace: listings + contact only, or orders/payments? | US10 scope, compliance | Listings + contact |
| OQ-3 | Must alerts reach farmers with the app closed (push/SMS)? | **D2** (PWA vs Capacitor) | **Decided 2026-11-21**: web push to the installed PWA; no Capacitor |
| OQ-4 | Hosting target and budget? | D11, D3 fallback | docker-compose; undecided prod |
| OQ-5 | Keep investing in the Flutter app? | D2, constitution | No; reference only |
| OQ-6 | Permission/licence to reuse code from `RaziSnihaa/is9ini`? | T-port tasks | **Decided 2026-11-21**: team's own code; reuse allowed (add a LICENSE) |
| OQ-7 | Data sources for prices and weather? | US8, US10 | Labeled sample data |
| OQ-9 | Is Tunisian Derja written in Arabic script (RTL), Latin script (Arabizi), or both? | Derja catalog, RTL QA | Arabic script, RTL |
| OQ-8 | Which hardware profiles exist (greenhouse, ROOTLOOP rig, energy, storage) and their hard limits? | Hard-limit table, simulator | Greenhouse profile = reference caps; others TBD with hardware team |

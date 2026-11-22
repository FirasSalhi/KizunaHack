---

description: "Task list for FARMLINK Platform — Web Dashboard and Mobile Version"
---

# Tasks: FARMLINK Platform — Web Dashboard and Mobile Version

**Input**: Design documents from `/specs/001-farmlink-platform/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The constitution (Principle VI) makes tests mandatory for auth, per-farm
authorization, device signatures, command signing/replay, hard limits, and contracts. Each story
also has one end-to-end test that matches its quickstart scenario.

**Organization**: Tasks are grouped by user story so each story can be built, tested and shown on
its own. Tasks are deliberately small: one file or one concern per task, so they can be assigned
and run in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story the task belongs to (US1–US10)
- `API` = `services/api`, `WEB` = `apps/web/src` in short descriptions; full paths are given

## Path Conventions

- Backend: `services/api/app/…`, tests in `services/api/tests/…`
- Web/PWA: `apps/web/src/…`, tests in `apps/web/tests/…`
- Shared contract: `packages/contracts/…`; tools: `tools/…`; infrastructure: `infra/…`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository, tooling and local infrastructure

- [X] T001 Record the answer to OQ-6 (permission to reuse code from RaziSnihaa/is9ini) in specs/001-farmlink-platform/research.md — blocks T019, T020, T061, T194
- [X] T002 Create pnpm workspace root (package.json, pnpm-workspace.yaml listing apps/*, packages/*) in package.json
- [X] T003 [P] Add .nvmrc pinning Node.js 22 LTS in .nvmrc
- [X] T004 [P] Add root .gitignore for Node, Python, .env*, model files and local data in .gitignore
- [X] T005 [P] Add .editorconfig in .editorconfig
- [X] T006 [P] Document repository layout and setup pointer to quickstart in README.md
- [X] T007 Scaffold Next.js 15 app (App Router, TypeScript strict, src dir) in apps/web/package.json
- [X] T008 [P] Configure ESLint (next + jsx-a11y) in apps/web/eslint.config.mjs
- [X] T009 [P] Configure Prettier in apps/web/.prettierrc
- [X] T010 [P] Configure Tailwind CSS v4 (CSS-first config, logical-property utilities for RTL) in apps/web/src/app/globals.css
- [X] T011 [P] Initialize shadcn/ui in apps/web/components.json
- [X] T012 [P] Configure Vitest + Testing Library in apps/web/vitest.config.ts
- [X] T013 [P] Configure Playwright with "desktop" and "mobile-360x800" projects in apps/web/playwright.config.ts
- [X] T014 Scaffold FastAPI project with uv (Python 3.12, dependencies from plan.md) in services/api/pyproject.toml
- [X] T015 [P] Configure ruff in services/api/ruff.toml
- [X] T016 [P] Configure mypy (strict for app/security and app/services) in services/api/mypy.ini
- [X] T017 [P] Configure pytest markers `contract`, `security`, `integration` in services/api/pytest.ini
- [X] T018 [P] Create contracts package with `generate` and `check` scripts in packages/contracts/package.json
- [X] T019 [P] Port reference build_catalog.py and download_models.py (with attribution header) into tools/catalog/
- [X] T020 [P] Port reference simulator.py unchanged as a baseline into tools/simulator/sim.py
- [X] T021 [P] Add docker-compose with timescale/timescaledb (PG16), eclipse-mosquitto, SeaweedFS (S3 gateway; MinIO images are no longer public), caddy in infra/docker-compose.yml
- [X] T022 [P] Add same-origin routing (`/` → web, `/api/*` and `/ws/*` → api) with local TLS in infra/Caddyfile
- [X] T023 [P] Add Mosquitto TLS config in infra/mosquitto/mosquitto.conf
- [X] T024 [P] Add Mosquitto per-device ACL template in infra/mosquitto/acl.template
- [X] T025 [P] Add backend development environment example (dev-only values, including empty VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT) in services/api/.env.example
- [X] T026 [P] Add web development environment example in apps/web/.env.example
- [X] T027 Add CI workflow running lint, typecheck, unit, contract and security tests in .github/workflows/ci.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data layer, security, ingestion, real-time, contract pipeline and web shell that every
story uses.

**CRITICAL**: No user story work can begin until this phase is complete.

### 2A — Backend core

- [ ] T028 Implement settings loading (pydantic-settings, secrets from env) in services/api/app/core/config.py
- [ ] T029 [P] Implement structured JSON logging with request ids in services/api/app/core/logging.py
- [ ] T030 [P] Implement error envelope and exception handlers per contracts/rest-api.md "Conventions" in services/api/app/core/errors.py
- [ ] T031 [P] Implement cursor pagination helper (limit ≤ 100) in services/api/app/core/pagination.py
- [ ] T032 Implement async engine and session dependency (asyncpg) in services/api/app/core/db.py
- [ ] T033 Initialize Alembic with async env in services/api/migrations/env.py
- [ ] T034 Implement app factory with `/api/v1` prefix, router registry, no wildcard CORS in services/api/app/main.py
- [ ] T035 [P] Implement `GET /health` (db, mqtt) in services/api/app/routers/health.py

### 2B — Data layer (identity, tenancy, devices, time series)

- [ ] T036 [P] Create declarative Base with UUIDv7 ids and created_at mixin in services/api/app/models/base.py
- [ ] T037 [P] Create User model (data-model.md User.email, User.name, User.password_hash, User.locale) in services/api/app/models/user.py
- [ ] T038 [P] Create Session model (data-model.md Session.refresh_token_hash, Session.expires_at, Session.replaced_by, Session.user_agent) in services/api/app/models/session.py
- [ ] T039 [P] Create Farm and Membership models (data-model.md Farm.name, Farm.region, Membership.role) in services/api/app/models/farm.py
- [ ] T040 [P] Create HardLimitProfile model (data-model.md HardLimitProfile.max_per_run_ml, HardLimitProfile.max_per_day_ml, HardLimitProfile.min_battery_v) in services/api/app/models/hard_limits.py
- [ ] T041 [P] Create Device model (data-model.md Device.name, Device.status, Device.report_interval_s, Device.next_command_seq, Device.key_version, Device.protocol_version, Device.field_id/Device.storage_unit_id exclusivity) in services/api/app/models/device.py
- [ ] T042 [P] Create Channel model (data-model.md Channel.key, Channel.kind, Channel.valid_min, Channel.valid_max, Channel.target_min, Channel.target_max) in services/api/app/models/channel.py
- [ ] T043 [P] Create Reading and DeviceStatus models (data-model.md Reading.time, Reading.value, DeviceStatus.mood, DeviceStatus.mood_confidence, DeviceStatus.mode, DeviceStatus.water_today_ml) in services/api/app/models/timeseries.py
- [ ] T044 [P] Create Event model (data-model.md Event.type, Event.message) in services/api/app/models/event.py
- [ ] T045 [P] Create AuditEntry model (data-model.md AuditEntry.actor_type, AuditEntry.action, AuditEntry.target) in services/api/app/models/audit.py
- [ ] T046 [P] Implement channel-kind registry (units and valid ranges from data-model.md "Channel kinds") in services/api/app/domain/channel_kinds.py
- [ ] T047 Write migration 0001 users, sessions, farms, memberships in services/api/migrations/versions/0001_identity.py
- [ ] T048 Write migration 0002 hard_limit_profiles (seed `greenhouse_v1` = 150/600 ml), devices, channels in services/api/migrations/versions/0002_devices.py
- [ ] T049 Write migration 0003 readings and device_status hypertables, 30-day retention, `reading_5m`/`reading_1h` continuous aggregates in services/api/migrations/versions/0003_timeseries.py
- [ ] T050 Write migration 0004 events and audit_log in services/api/migrations/versions/0004_events.py

### 2C — Security

- [ ] T051 [P] Implement Argon2id hashing with PBKDF2 legacy verify-and-rehash in services/api/app/security/passwords.py
- [ ] T052 [P] Implement 15-minute access JWT issue/verify in services/api/app/security/tokens.py
- [ ] T053 Implement refresh session create/rotate/revoke with reuse detection in services/api/app/security/sessions.py
- [ ] T054 [P] Implement double-submit CSRF middleware in services/api/app/security/csrf.py
- [ ] T055 [P] Implement login rate limiter (5/min per IP+email) in services/api/app/security/rate_limit.py
- [ ] T056 Implement current-user dependency (cookie, or bearer for native shell) in services/api/app/security/deps.py
- [ ] T057 Implement `require_farm_role(min_role)` with 404-for-foreign-farm rule in services/api/app/security/authz.py
- [ ] T058 [P] Implement device secret generation and AES-GCM encryption at rest in services/api/app/security/device_keys.py
- [ ] T059 [P] Implement device HMAC body verification per contracts/device-protocol.md in services/api/app/security/device_auth.py
- [ ] T060 [P] Implement command signing v2 and v1 formats per contracts/device-protocol.md in services/api/app/security/command_signing.py
- [ ] T061 Implement audit writer service in services/api/app/services/audit.py
- [ ] T062 [P] Implement auth schemas (LoginIn, Me with memberships) in services/api/app/schemas/auth.py
- [ ] T063 Implement auth router: login, refresh, logout, logout-all (cookies per research D4) in services/api/app/routers/auth.py
- [ ] T064 Implement `GET/PATCH /me` in services/api/app/routers/me.py

### 2D — Ingestion and real-time

- [ ] T065 [P] Implement device payload v2 Pydantic schemas in services/api/app/schemas/device_protocol.py
- [ ] T066 Implement ingest pipeline (per-channel validation, timestamp window, store, status-change events) in services/api/app/ingest/pipeline.py
- [ ] T067 [P] Implement v1 reference-payload adapter in services/api/app/ingest/v1_adapter.py
- [ ] T068 Implement device HTTP endpoints readings/status/events/telemetry(v1) in services/api/app/routers/device.py
- [ ] T069 Port and adapt MQTT bridge to per-device v2 topics in services/api/app/ingest/mqtt_bridge.py
- [ ] T070 [P] Implement realtime message models per contracts/realtime.md in services/api/app/realtime/messages.py
- [ ] T071 Implement NOTIFY publisher (8 KB payload guard) in services/api/app/realtime/notify.py
- [ ] T072 Implement LISTEN consumer and per-farm subscriber hub in services/api/app/realtime/hub.py
- [ ] T073 Implement `/ws/v1` endpoint (cookie auth, subscribe membership check, ping/pong) in services/api/app/routers/ws.py
- [ ] T074 Implement device presence job (online/offline transitions → events) in services/api/app/services/presence.py

### 2E — Contract pipeline (Principle II)

- [ ] T075 Implement OpenAPI export script in services/api/scripts/export_openapi.py
- [ ] T076 Generate TypeScript types with openapi-typescript into packages/contracts/src/openapi.d.ts
- [ ] T077 [P] Write realtime zod schemas mirroring contracts/realtime.md in packages/contracts/src/realtime.ts
- [ ] T078 [P] Export typed openapi-fetch client factory in packages/contracts/src/index.ts
- [ ] T079 Implement drift check (regenerate and diff) in packages/contracts/scripts/check.mjs

### 2F — Web shell

- [ ] T080 Implement browser API client (CSRF header, refresh-on-401 once) in apps/web/src/lib/api/client.ts
- [ ] T081 [P] Implement server-side fetch helper forwarding request cookies in apps/web/src/lib/api/server.ts
- [ ] T082 [P] Implement TanStack Query provider in apps/web/src/lib/api/QueryProvider.tsx
- [ ] T083 [P] Configure next-intl (fr default, aeb, en; `dir` per locale, aeb = rtl per OQ-9 default) in apps/web/src/lib/i18n/config.ts
- [ ] T084 [P] Create message catalogs with shell strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json
- [ ] T085 Implement middleware for locale routing and redirect-to-login when no session cookie in apps/web/src/middleware.ts
- [ ] T086 Port reference design tokens (theme.dart colors, mood colors, 18 px radius, soft shadow, Poppins) in apps/web/src/app/globals.css
- [ ] T087 [P] Port mood metadata (label, description, color, isAlarm) from theme.dart in apps/web/src/lib/format/mood.ts
- [ ] T088 [P] Implement `useMe` session hook in apps/web/src/lib/auth/useMe.ts
- [ ] T089 [P] Implement responsive AppShell (sidebar ≥ 1024 px, bottom nav < 768 px) in apps/web/src/components/layout/AppShell.tsx
- [ ] T090 [P] Implement FarmSwitcher in apps/web/src/components/layout/FarmSwitcher.tsx
- [ ] T091 [P] Implement ConnectionBadge ("live" / "live updates paused") in apps/web/src/components/layout/ConnectionBadge.tsx
- [ ] T092 Implement authenticated app layout using AppShell in apps/web/src/app/[locale]/(app)/layout.tsx
- [ ] T093 Port login screen (no server-URL field) in apps/web/src/app/[locale]/(auth)/login/page.tsx
- [ ] T094 [P] Implement logout action in apps/web/src/lib/auth/logout.ts

### 2G — Seed data and simulator

- [ ] T095 Implement seed script (demo farm, owner/operator/viewer, second farm, one greenhouse device, settings) in services/api/app/seed.py
- [ ] T096 Upgrade simulator to per-device key and signed v2 payloads, profile `greenhouse` in tools/simulator/sim.py
- [ ] T097 [P] Implement simulator command receiver (verify sig, age, seq; `--replay-last`) in tools/simulator/commands.py

### 2H — Foundational tests (required before merge)

- [ ] T098 [P] Create test fixtures (Postgres+Timescale container, async client, user/farm/device factories) in services/api/tests/conftest.py
- [ ] T099 [P] Security test: login success/failure, rate limit, refresh rotation, refresh reuse revokes chain in services/api/tests/security/test_auth.py
- [ ] T100 [P] Security test: CSRF required on every mutating cookie-authenticated route in services/api/tests/security/test_csrf.py
- [ ] T101 [P] Security test: device signature valid/invalid/unknown device in services/api/tests/security/test_device_auth.py
- [ ] T102 [P] Unit test: command signing vectors for v1 and v2 in services/api/tests/unit/test_command_signing.py
- [ ] T103 [P] Security test: cross-farm access returns 404 for every farm-scoped route enumerated from OpenAPI in services/api/tests/security/test_cross_farm.py
- [ ] T104 [P] Integration test: out-of-range values rejected, timestamp window, status-change events in services/api/tests/integration/test_ingest.py
- [ ] T105 [P] Integration test: v1 adapter accepts reference payload in services/api/tests/integration/test_v1_adapter.py
- [ ] T106 [P] Integration test: NOTIFY fan-out reaches subscribers on two hub instances in services/api/tests/integration/test_realtime_fanout.py
- [ ] T107 [P] Integration test: WebSocket rejects unauthenticated and non-member subscribe in services/api/tests/security/test_ws_auth.py
- [ ] T108 [P] Contract test: Schemathesis over `/api/openapi.json` in services/api/tests/contract/test_openapi.py

**Checkpoint**: Foundation ready — user stories can start in parallel.

---

## Phase 3: User Story 1 — Monitor my farm live, on the web and on my phone (Priority: P1), MVP

**Goal**: A member sees live readings, status, pump, water today, online state, history and events
on desktop and phone.

**Independent Test**: quickstart Q1–Q3.

### Tests for User Story 1

- [ ] T109 [P] [US1] Contract tests for overview, readings, status history, devices list, events in services/api/tests/contract/test_monitoring.py
- [ ] T110 [P] [US1] Integration test: readings history returns ≤ 300 points and uses aggregates for week/month in services/api/tests/integration/test_history.py
- [ ] T111 [P] [US1] E2E: live update ≤ 3 s, offline badge, no horizontal scroll at 360 px in apps/web/tests/e2e/us1-monitoring.spec.ts

### Implementation for User Story 1 — backend

- [ ] T112 [P] [US1] Create monitoring schemas (Overview, ReadingSeries, DeviceStatusOut, DeviceOut) in services/api/app/schemas/monitoring.py
- [ ] T113 [P] [US1] Create event schemas (EventOut, filters) in services/api/app/schemas/events.py
- [ ] T114 [US1] Implement overview query (latest status, latest value per channel, open-alert count) in services/api/app/services/monitoring.py
- [ ] T115 [US1] Implement readings history (raw vs `reading_5m`/`reading_1h`, ≤ 300 points) in services/api/app/services/history.py
- [ ] T116 [US1] Implement events query with range/type filters and cursor in services/api/app/services/events.py
- [ ] T117 [US1] Implement `GET /farms/{id}/overview`, `/devices/{id}/readings`, `/devices/{id}/status/history` in services/api/app/routers/monitoring.py
- [ ] T118 [US1] Implement `GET /farms/{id}/devices` and `GET /devices/{id}` in services/api/app/routers/devices.py
- [ ] T119 [US1] Implement `GET /farms/{id}/events` in services/api/app/routers/events.py
- [ ] T120 [US1] Send `snapshot` on subscribe using the overview query in services/api/app/realtime/hub.py

### Implementation for User Story 1 — web/mobile

- [ ] T121 [P] [US1] Port live feed (WebSocket, subscribe, 4 s polling fallback, backoff, ping) from live_feed.dart in apps/web/src/lib/realtime/useLiveFeed.ts
- [ ] T122 [P] [US1] Implement realtime → Query cache updater in apps/web/src/lib/realtime/applyMessage.ts
- [ ] T123 [P] [US1] Implement channel value formatting (units, locale numbers) in apps/web/src/lib/format/channel.ts
- [ ] T124 [P] [US1] Implement relative time ("x s ago") formatter in apps/web/src/lib/format/relativeTime.ts
- [ ] T125 [P] [US1] Build MoodCard (port plant_mascot concept as SVG) in apps/web/src/components/dashboard/MoodCard.tsx
- [ ] T126 [P] [US1] Build channel-driven MetricTile in apps/web/src/components/dashboard/MetricTile.tsx
- [ ] T127 [P] [US1] Build PumpWaterCard (pump state, water today vs daily limit) in apps/web/src/components/dashboard/PumpWaterCard.tsx
- [ ] T128 [P] [US1] Build DeviceOnlineIndicator in apps/web/src/components/dashboard/DeviceOnlineIndicator.tsx
- [ ] T129 [P] [US1] Build DeviceCard (combines status and tiles for one device) in apps/web/src/components/dashboard/DeviceCard.tsx
- [ ] T130 [P] [US1] Build TimeSeriesChart with range switch (hour/day/week/month) in apps/web/src/components/charts/TimeSeriesChart.tsx
- [ ] T131 [P] [US1] Build EventList with type/range filters in apps/web/src/components/dashboard/EventList.tsx
- [ ] T132 [P] [US1] Build loading, empty and error states in apps/web/src/components/dashboard/States.tsx
- [ ] T133 [US1] Build farm overview page in apps/web/src/app/[locale]/(app)/farms/[farmId]/page.tsx
- [ ] T134 [US1] Build device detail page with history chart in apps/web/src/app/[locale]/(app)/farms/[farmId]/devices/[deviceId]/page.tsx
- [ ] T135 [US1] Build events page in apps/web/src/app/[locale]/(app)/farms/[farmId]/events/page.tsx
- [ ] T136 [P] [US1] Unit tests for MetricTile, MoodCard and useLiveFeed reconnect in apps/web/tests/unit/dashboard.test.tsx
- [ ] T137 [US1] Add US1 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

**Checkpoint**: US1 works alone with seeded data and the simulator (MVP).

---

## Phase 4: User Story 2 — Control irrigation safely (Priority: P2)

**Goal**: Owners/operators send water-now, set mode and edit thresholds within hard limits;
viewers cannot.

**Independent Test**: quickstart Q4–Q7.

### Tests for User Story 2

- [ ] T138 [P] [US2] Security test: settings beyond hard limits rejected (not clamped); dry ≥ wet and temp_min ≥ temp_max rejected in services/api/tests/security/test_hard_limits.py
- [ ] T139 [P] [US2] Security test: viewer refused on settings and commands; operator allowed in services/api/tests/security/test_control_roles.py
- [ ] T140 [P] [US2] Integration test: command seq unique under concurrency and after restart in services/api/tests/integration/test_command_seq.py
- [ ] T141 [P] [US2] Integration test: expired commands never delivered by poll in services/api/tests/integration/test_command_expiry.py
- [ ] T142 [P] [US2] Integration test: stale settings `version` returns 409 in services/api/tests/integration/test_settings_concurrency.py
- [ ] T143 [P] [US2] Contract tests for settings, commands, device poll/ack in services/api/tests/contract/test_control.py
- [ ] T144 [P] [US2] E2E: operator waters; viewer sees disabled controls; offline disables controls in apps/web/tests/e2e/us2-control.spec.ts

### Implementation for User Story 2 — backend

- [ ] T145 [P] [US2] Create IrrigationSettings model (data-model.md IrrigationSettings.mode, .max_per_run_ml, .max_per_day_ml, .soil_dry_pct, .soil_wet_pct, .temp_min_c, .temp_max_c, .plant_profile, .version) in services/api/app/models/irrigation.py
- [ ] T146 [P] [US2] Create Command model (data-model.md Command.seq, Command.type, Command.value, Command.status, Command.expires_at) in services/api/app/models/command.py
- [ ] T147 [US2] Write migration 0005 irrigation_settings and commands with check constraints in services/api/migrations/versions/0005_control.py
- [ ] T148 [P] [US2] Create control schemas (SettingsIn with bounds, SettingsOut with hard_limits, CommandIn, CommandOut) in services/api/app/schemas/control.py
- [ ] T149 [US2] Implement settings service (validate vs HardLimitProfile, optimistic version, event + audit) in services/api/app/services/settings.py
- [ ] T150 [US2] Implement atomic sequence allocator (`UPDATE … RETURNING`) in services/api/app/services/command_seq.py
- [ ] T151 [US2] Implement command service (sign, MQTT or poll delivery, warnings, realtime `command` message) in services/api/app/services/commands.py
- [ ] T152 [US2] Implement command expiry sweeper in services/api/app/services/command_expiry.py
- [ ] T153 [US2] Add device `commands/poll` and `commands/{seq}/ack` endpoints in services/api/app/routers/device.py
- [ ] T154 [US2] Implement settings GET/PUT and commands POST/GET routes in services/api/app/routers/control.py
- [ ] T155 [P] [US2] Simulator: enforce its own hard limits and report refusals in tools/simulator/limits.py

### Implementation for User Story 2 — web/mobile

- [ ] T156 [P] [US2] Build zod settings schema from returned hard limits in apps/web/src/lib/control/settingsSchema.ts
- [ ] T157 [P] [US2] Implement `useCanControl` (role ≥ operator and online) in apps/web/src/lib/auth/useCanControl.ts
- [ ] T158 [P] [US2] Build SettingsForm (bounded inputs, inline errors, version-conflict reload) in apps/web/src/components/control/SettingsForm.tsx
- [ ] T159 [P] [US2] Build WaterNowButton (confirm dialog, warning display) in apps/web/src/components/control/WaterNowButton.tsx
- [ ] T160 [P] [US2] Build ModeToggle in apps/web/src/components/control/ModeToggle.tsx
- [ ] T161 [P] [US2] Build CommandHistory with live status in apps/web/src/components/control/CommandHistory.tsx
- [ ] T162 [US2] Build control page in apps/web/src/app/[locale]/(app)/farms/[farmId]/devices/[deviceId]/control/page.tsx
- [ ] T163 [US2] Build settings page in apps/web/src/app/[locale]/(app)/farms/[farmId]/devices/[deviceId]/settings/page.tsx
- [ ] T164 [US2] Add US2 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

**Checkpoint**: US1 + US2 work; control is provably bounded.

---

## Phase 5: User Story 3 — Manage my farms, fields, devices and people (Priority: P2)

**Goal**: Owners create farms and fields, register/rotate/revoke devices, invite and manage members.

**Independent Test**: quickstart Q8–Q9.

### Tests for User Story 3

- [ ] T165 [P] [US3] Integration test: last-owner rule on demote/remove/leave in services/api/tests/integration/test_last_owner.py
- [ ] T166 [P] [US3] Integration test: invitation create, accept (new and existing user), expiry, revoke in services/api/tests/integration/test_invitations.py
- [ ] T167 [P] [US3] Integration test: device secret shown once; rotate invalidates old key; revoke → 401 in services/api/tests/integration/test_device_lifecycle.py
- [ ] T168 [P] [US3] Integration test: removed member's WebSocket receives `membership_revoked` in services/api/tests/integration/test_membership_ws.py
- [ ] T169 [P] [US3] Contract tests for farms, members, invitations, fields, device management in services/api/tests/contract/test_management.py
- [ ] T170 [P] [US3] E2E: create farm → field → device → simulator reading in apps/web/tests/e2e/us3-onboarding.spec.ts

### Implementation for User Story 3 — backend

- [ ] T171 [P] [US3] Create Field model (data-model.md Field.name, Field.area_m2, Field.soil_type, Field.latitude/Field.longitude) in services/api/app/models/field.py
- [ ] T172 [P] [US3] Create Invitation model (data-model.md Invitation.email, Invitation.role, Invitation.token_hash, Invitation.expires_at) in services/api/app/models/invitation.py
- [ ] T173 [US3] Write migration 0006 fields, invitations and last-owner deferred trigger in services/api/migrations/versions/0006_management.py
- [ ] T174 [P] [US3] Create management schemas (FarmIn/Out, MemberOut, InvitationIn, FieldIn/Out, DeviceRegisterOut with secret) in services/api/app/schemas/management.py
- [ ] T175 [P] [US3] Implement email sender interface with console dev implementation in services/api/app/services/email.py
- [ ] T176 [US3] Implement farm service (create → owner membership, update) in services/api/app/services/farms.py
- [ ] T177 [US3] Implement membership service (role change, remove, last-owner rule, realtime revoke) in services/api/app/services/memberships.py
- [ ] T178 [US3] Implement invitation service (create, send, accept, expire, revoke) in services/api/app/services/invitations.py
- [ ] T179 [US3] Implement field service in services/api/app/services/fields.py
- [ ] T180 [US3] Implement device admin service (register, rotate, revoke, declare channels, confirm pending channels) in services/api/app/services/devices.py
- [ ] T181 [US3] Implement MQTT ACL provisioning on register/rotate/revoke in services/api/app/ingest/mqtt_acl.py
- [ ] T182 [US3] Implement farms, members and invitations routes in services/api/app/routers/farms.py
- [ ] T183 [US3] Implement invitation acceptance route in services/api/app/routers/invitations.py
- [ ] T184 [US3] Implement fields routes in services/api/app/routers/fields.py
- [ ] T185 [US3] Add device register/patch/rotate/revoke/channels routes in services/api/app/routers/devices.py

### Implementation for User Story 3 — web/mobile

- [ ] T186 [P] [US3] Build create-farm page in apps/web/src/app/[locale]/(app)/farms/new/page.tsx
- [ ] T187 [P] [US3] Build FieldForm in apps/web/src/components/farm/FieldForm.tsx
- [ ] T188 [P] [US3] Build fields page in apps/web/src/app/[locale]/(app)/farms/[farmId]/fields/page.tsx
- [ ] T189 [P] [US3] Build InviteDialog in apps/web/src/components/farm/InviteDialog.tsx
- [ ] T190 [P] [US3] Build members page (roles, remove, pending invites) in apps/web/src/app/[locale]/(app)/farms/[farmId]/members/page.tsx
- [ ] T191 [P] [US3] Build invitation acceptance page in apps/web/src/app/[locale]/(auth)/invite/[token]/page.tsx
- [ ] T192 [P] [US3] Build device registration wizard (secret shown once, copy, firmware hints) in apps/web/src/app/[locale]/(app)/farms/[farmId]/devices/new/page.tsx
- [ ] T193 [P] [US3] Build DeviceAdmin panel (rename, rotate, revoke, confirm channels) in apps/web/src/components/devices/DeviceAdmin.tsx
- [ ] T194 [US3] Add US3 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

**Checkpoint**: New users can onboard their own farm without seed data.

---

## Phase 6: User Story 4 — Watch the ROOTLOOP water loop (Priority: P3)

**Goal**: Tank, water-quality, flow, pressure and leak monitoring with range alerts.

**Independent Test**: quickstart Q10.

### Tests for User Story 4

- [ ] T195 [P] [US4] Integration test: one alert per excursion, min duration respected, resolves on recovery in services/api/tests/integration/test_alert_engine.py
- [ ] T196 [P] [US4] Integration test: `hold_irrigation` rule blocks water-now with reason in services/api/tests/integration/test_alert_hold.py
- [ ] T197 [P] [US4] Contract tests for alerts and alert rules in services/api/tests/contract/test_alerts.py
- [ ] T198 [P] [US4] E2E: turbidity spike raises and clears one alert in apps/web/tests/e2e/us4-water.spec.ts

### Implementation for User Story 4 — backend

- [ ] T199 [P] [US4] Create AlertRule and Alert models (data-model.md AlertRule.min_value/AlertRule.max_value, AlertRule.min_duration_s, AlertRule.severity, AlertRule.hold_irrigation; Alert.ended_at) in services/api/app/models/alert.py
- [ ] T200 [US4] Write migration 0007 alert_rules, alerts, partial unique open-alert index in services/api/migrations/versions/0007_alerts.py
- [ ] T201 [P] [US4] Create alert schemas in services/api/app/schemas/alerts.py
- [ ] T202 [P] [US4] Define default ROOTLOOP rule templates per channel kind in services/api/app/domain/default_rules.py
- [ ] T203 [US4] Implement alert evaluator called from the ingest pipeline (open, resolve, realtime `alert`) in services/api/app/services/alert_engine.py
- [ ] T204 [US4] Apply open `hold_irrigation` alerts as a refusal reason in services/api/app/services/commands.py
- [ ] T205 [US4] Implement alerts, acknowledge and alert-rule routes in services/api/app/routers/alerts.py
- [ ] T206 [P] [US4] Add simulator `rootloop` profile (tanks, pH, EC, turbidity, flow, pressure, leak, `--spike`) in tools/simulator/profiles/rootloop.py

### Implementation for User Story 4 — web/mobile

- [ ] T207 [P] [US4] Build WaterLoopDiagram (collection → treatment → tank → underground delivery) in apps/web/src/components/water/WaterLoopDiagram.tsx
- [ ] T208 [P] [US4] Build TankGauge in apps/web/src/components/water/TankGauge.tsx
- [ ] T209 [P] [US4] Build QualityIndicator with range, status and "monitoring, not certification" note in apps/web/src/components/water/QualityIndicator.tsx
- [ ] T210 [P] [US4] Build FlowPressurePanel in apps/web/src/components/water/FlowPressurePanel.tsx
- [ ] T211 [P] [US4] Build AlertBanner for the overview in apps/web/src/components/alerts/AlertBanner.tsx
- [ ] T212 [P] [US4] Build AlertList with acknowledge in apps/web/src/components/alerts/AlertList.tsx
- [ ] T213 [P] [US4] Build AlertRuleForm in apps/web/src/components/alerts/AlertRuleForm.tsx
- [ ] T214 [US4] Build water page in apps/web/src/app/[locale]/(app)/farms/[farmId]/water/page.tsx
- [ ] T215 [US4] Build alerts page in apps/web/src/app/[locale]/(app)/farms/[farmId]/alerts/page.tsx
- [ ] T216 [US4] Add US4 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

**Checkpoint**: ROOTLOOP demo can run end to end with the simulator.

---

## Phase 7: User Story 5 — Scan a plant with my phone and track crop health (Priority: P3)

**Goal**: Camera/file scan → species, confidence, health, care sheet; history with corrections;
apply recommended thresholds safely.

**Independent Test**: quickstart Q11–Q12.

### Tests for User Story 5

- [ ] T217 [P] [US5] Integration test: identify with stub engine, 10 MB limit, non-image rejected, 503 when unavailable in services/api/tests/integration/test_scans.py
- [ ] T218 [P] [US5] Integration test: same `Idempotency-Key` returns the first scan in services/api/tests/integration/test_scan_idempotency.py
- [ ] T219 [P] [US5] Security test: correct/delete allowed for author or owner only; correction keeps `ai_result` in services/api/tests/security/test_scan_permissions.py
- [ ] T220 [P] [US5] Security test: apply-plant goes through hard-limit validation in services/api/tests/security/test_apply_plant.py
- [ ] T221 [P] [US5] E2E: upload reference test photos, uncertain label shown in apps/web/tests/e2e/us5-scan.spec.ts

### Implementation for User Story 5 — backend

- [ ] T222 [US5] Port reference plant_id.py with lazy model loading in services/api/app/ml/plant_id.py
- [ ] T223 [P] [US5] Implement PlantIdentifier interface, engine selection and test stub in services/api/app/ml/identifier.py
- [ ] T224 [P] [US5] Create PlantIdResult and care-sheet schemas from the reference result shape in services/api/app/schemas/plants.py
- [ ] T225 [P] [US5] Implement object storage interface (local dir + S3) with signed URLs in services/api/app/storage/objects.py
- [ ] T226 [P] [US5] Create PlantScan model (data-model.md PlantScan.client_request_id, PlantScan.confidence, PlantScan.sure, PlantScan.ai_result, PlantScan.corrected_result) in services/api/app/models/plant_scan.py
- [ ] T227 [US5] Write migration 0008 plant_scans in services/api/migrations/versions/0008_scans.py
- [ ] T228 [P] [US5] Port photo resize (1280 px + 360 px thumb, EXIF transpose) in services/api/app/services/photos.py
- [ ] T229 [US5] Implement scan service (validate, identify in thread, store photos, event, idempotency) in services/api/app/services/scans.py
- [ ] T230 [US5] Implement scan routes (create, list, detail, photo, correct, delete) in services/api/app/routers/scans.py
- [ ] T231 [US5] Implement plant search, care sheet and apply-plant routes in services/api/app/routers/plants.py

### Implementation for User Story 5 — web/mobile

- [ ] T232 [P] [US5] Implement camera capture adapter (`capture="environment"`, Capacitor-ready interface) in apps/web/src/lib/platform/camera.ts
- [ ] T233 [P] [US5] Implement client-side image downscale before upload in apps/web/src/lib/platform/resizeImage.ts
- [ ] T234 [P] [US5] Build SpeciesHeader with ConfidenceBadge and uncertain state in apps/web/src/components/scan/SpeciesHeader.tsx
- [ ] T235 [P] [US5] Build HealthPanel (status, diseases, treatment) in apps/web/src/components/scan/HealthPanel.tsx
- [ ] T236 [P] [US5] Build AlternativesList with "this is the right plant" correction in apps/web/src/components/scan/AlternativesList.tsx
- [ ] T237 [P] [US5] Build CareSheet with apply-settings action in apps/web/src/components/scan/CareSheet.tsx
- [ ] T238 [P] [US5] Build ScanThumb card for history in apps/web/src/components/scan/ScanThumb.tsx
- [ ] T239 [US5] Build new-scan page in apps/web/src/app/[locale]/(app)/farms/[farmId]/scans/new/page.tsx
- [ ] T240 [US5] Build scan history page in apps/web/src/app/[locale]/(app)/farms/[farmId]/scans/page.tsx
- [ ] T241 [US5] Build scan detail page (correct, delete) in apps/web/src/app/[locale]/(app)/farms/[farmId]/scans/[scanId]/page.tsx
- [ ] T242 [US5] Add US5 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

**Checkpoint**: Reference scanner parity reached on web and phone.

---

## Phase 8: User Story 6 — Use it in the field with a weak or no connection (Priority: P4)

**Goal**: Installable PWA, offline read cache, offline scan queue, controls disabled offline.

**Independent Test**: quickstart Q13–Q14.

### Tests for User Story 6

- [ ] T243 [P] [US6] E2E: offline reopen shows cached data with age; queued scan submitted once on reconnect in apps/web/tests/e2e/us6-offline.spec.ts
- [ ] T244 [P] [US6] Unit test: outbox retries keep the same Idempotency-Key in apps/web/tests/unit/outbox.test.ts

### Implementation for User Story 6

- [ ] T245 [P] [US6] Add web app manifest (name, icons, standalone, theme color) in apps/web/src/app/manifest.ts
- [ ] T246 [P] [US6] Add PWA icon set in apps/web/public/icons/
- [ ] T247 [US6] Implement Serwist service worker (precache shell; network-first for GET overview/readings/events; never cache mutations) in apps/web/src/app/sw.ts
- [ ] T248 [US6] Wire Serwist into the build in apps/web/next.config.ts
- [ ] T249 [P] [US6] Persist Query cache to IndexedDB keyed per user with max age in apps/web/src/lib/offline/persistQueryCache.ts
- [ ] T250 [P] [US6] Implement IndexedDB outbox for scans with Idempotency-Key in apps/web/src/lib/offline/outbox.ts
- [ ] T251 [US6] Implement outbox flusher on `online`/visibility with session check in apps/web/src/lib/offline/flushOutbox.ts
- [ ] T252 [P] [US6] Implement `useOnline` hook in apps/web/src/lib/offline/useOnline.ts
- [ ] T253 [P] [US6] Build DataAgeBanner in apps/web/src/components/layout/DataAgeBanner.tsx
- [ ] T254 [P] [US6] Build InstallPrompt (Android prompt; iOS "Add to Home Screen" instructions) in apps/web/src/components/layout/InstallPrompt.tsx
- [ ] T255 [US6] Route offline scans through the outbox on the new-scan page in apps/web/src/app/[locale]/(app)/farms/[farmId]/scans/new/page.tsx
- [ ] T256 [US6] Clear cache and outbox on logout in apps/web/src/lib/auth/logout.ts
- [ ] T257 [US6] Add US6 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

### Web push for alerts (FR-037, OQ-3) — needs the US4 alert engine (T203)

- [ ] T324 [P] [US6] Contract tests for push key and subscription endpoints in services/api/tests/contract/test_push.py
- [ ] T325 [P] [US6] Unit test: 404/410 from the push service deletes the subscription; payload holds only title, severity, alert id in services/api/tests/unit/test_push.py
- [ ] T326 [P] [US6] Create PushSubscription model (data-model.md PushSubscription.endpoint) in services/api/app/models/push_subscription.py
- [ ] T327 [US6] Write migration 0012 push_subscriptions in services/api/migrations/versions/0012_push.py
- [ ] T328 [US6] Implement push sender (pywebpush, VAPID from settings) in services/api/app/services/push.py
- [ ] T329 [US6] Implement push key and subscription routes in services/api/app/routers/push.py
- [ ] T330 [US6] Send push to members of the farm when an alert opens in services/api/app/services/alert_engine.py
- [ ] T331 [US6] Handle `push` and `notificationclick` in the service worker in apps/web/src/app/sw.ts
- [ ] T332 [P] [US6] Build PushToggle (asks permission only on tap; explains home-screen install on iPhone) in apps/web/src/components/settings/PushToggle.tsx
- [ ] T333 [US6] Unsubscribe this browser on logout in apps/web/src/lib/auth/logout.ts

**Checkpoint**: Phone experience usable without network for reading and scanning; alerts reach a closed app (quickstart Q19).

---

## Phase 9: User Story 7 — See my farm's energy (Priority: P4)

**Goal**: Solar production, battery and consumption, with low-battery warning before irrigation.

**Independent Test**: quickstart Q15.

- [ ] T258 [P] [US7] Integration test: daily energy totals and low-battery warning in services/api/tests/integration/test_energy.py
- [ ] T259 [P] [US7] Add simulator `energy` profile (`--battery-low`) in tools/simulator/profiles/energy.py
- [ ] T260 [P] [US7] Create energy schemas in services/api/app/schemas/energy.py
- [ ] T261 [US7] Implement daily energy integration service in services/api/app/services/energy.py
- [ ] T262 [US7] Add low-battery warning (data-model.md HardLimitProfile.min_battery_v) to command service in services/api/app/services/commands.py
- [ ] T263 [US7] Implement `GET /farms/{id}/energy/summary` in services/api/app/routers/energy.py
- [ ] T264 [P] [US7] Build EnergyCharts in apps/web/src/components/energy/EnergyCharts.tsx
- [ ] T265 [P] [US7] Build BatteryCard in apps/web/src/components/energy/BatteryCard.tsx
- [ ] T266 [US7] Build energy page in apps/web/src/app/[locale]/(app)/farms/[farmId]/energy/page.tsx
- [ ] T267 [US7] Add US7 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

---

## Phase 10: User Story 8 — Choose what to plant (Priority: P5)

**Goal**: Ranked, explained crop recommendations and companion suggestions.

**Independent Test**: quickstart Q16.

- [ ] T268 [US8] Record OQ-7 decision (weather and price sources) in specs/001-farmlink-platform/research.md
- [ ] T269 [P] [US8] Unit tests: water fit, climate fit, ranking changes when water is halved in services/api/tests/unit/test_crop_scoring.py
- [ ] T270 [P] [US8] Contract tests for recommendations, companions, prices in services/api/tests/contract/test_crops.py
- [ ] T271 [P] [US8] Create CropProfile and CropCompatibility models (data-model.md CropProfile.scientific_name, CropProfile.root_depth, CropProfile.light; CropCompatibility.relation) in services/api/app/models/crops.py
- [ ] T272 [P] [US8] Create MarketPrice and RecommendationRun models (data-model.md MarketPrice.is_sample, MarketPrice.unit; RecommendationRun.inputs, RecommendationRun.data_versions) in services/api/app/models/planning.py
- [ ] T273 [US8] Write migration 0009 crop reference and planning tables in services/api/migrations/versions/0009_crops.py
- [ ] T274 [US8] Implement EcoCrop import into crop_profiles in tools/catalog/import_ecocrop.py
- [ ] T275 [P] [US8] Add sample compatibility pairs and prices flagged `is_sample` in tools/catalog/fixtures/sample_planning.json
- [ ] T276 [P] [US8] Implement weather client interface and provider in services/api/app/services/weather.py
- [ ] T277 [P] [US8] Create planning schemas in services/api/app/schemas/planning.py
- [ ] T278 [US8] Implement transparent scoring engine (per-factor basis) in services/api/app/services/crop_scoring.py
- [ ] T279 [US8] Implement recommendation service storing inputs, results, data versions in services/api/app/services/recommendations.py
- [ ] T280 [US8] Implement recommendations, companions and prices routes in services/api/app/routers/crops.py
- [ ] T281 [P] [US8] Build FieldProfileForm in apps/web/src/components/planning/FieldProfileForm.tsx
- [ ] T282 [P] [US8] Build RecommendationList with basis breakdown and sources/dates in apps/web/src/components/planning/RecommendationList.tsx
- [ ] T283 [P] [US8] Build CompanionPanel with validation notice in apps/web/src/components/planning/CompanionPanel.tsx
- [ ] T284 [US8] Build planning page in apps/web/src/app/[locale]/(app)/farms/[farmId]/planning/page.tsx
- [ ] T285 [US8] Add US8 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

---

## Phase 11: User Story 9 — Protect my harvest in storage (Priority: P5)

**Goal**: Storage units with crop-specific ranges, alerts and guidance.

**Independent Test**: quickstart Q17. Depends on US4 alert engine and US8 crop profiles.

- [ ] T286 [P] [US9] Integration test: setting a stored crop derives alert rules; humid excursion alerts in services/api/tests/integration/test_storage.py
- [ ] T287 [P] [US9] Create StorageUnit model (data-model.md StorageUnit.name, StorageUnit.kind) in services/api/app/models/storage_unit.py
- [ ] T288 [US9] Write migration 0010 storage_units in services/api/migrations/versions/0010_storage.py
- [ ] T289 [P] [US9] Create storage schemas in services/api/app/schemas/storage.py
- [ ] T290 [P] [US9] Write crop/condition guidance table in services/api/app/domain/storage_guidance.py
- [ ] T291 [US9] Implement storage service (create, set crop → derive AlertRules from CropProfile storage ranges) in services/api/app/services/storage_units.py
- [ ] T292 [US9] Implement storage routes in services/api/app/routers/storage.py
- [ ] T293 [P] [US9] Add simulator `storage` profile (`--humid`) in tools/simulator/profiles/storage.py
- [ ] T294 [P] [US9] Build StorageCard in apps/web/src/components/storage/StorageCard.tsx
- [ ] T295 [US9] Build storage page in apps/web/src/app/[locale]/(app)/farms/[farmId]/storage/page.tsx
- [ ] T296 [US9] Add US9 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

---

## Phase 12: User Story 10 — Find buyers and suppliers (Priority: P6)

**Goal**: Listings, search, contact requests with consent-based contact reveal, price trends.

**Independent Test**: quickstart Q18. Depends on US8 crop profiles and prices.

- [ ] T297 [US10] Record OQ-2 decision (marketplace scope) in specs/001-farmlink-platform/research.md
- [ ] T298 [P] [US10] Integration test: listing lifecycle, search filters, expiry hides listing in services/api/tests/integration/test_listings.py
- [ ] T299 [P] [US10] Security test: contact details hidden until request accepted in services/api/tests/security/test_contact_reveal.py
- [ ] T300 [P] [US10] Create MarketProfile, Listing, ContactRequest models (data-model.md Listing.kind, Listing.title, Listing.quantity, Listing.status, Listing.available_from/Listing.available_to; ContactRequest.message, ContactRequest.status) in services/api/app/models/market.py
- [ ] T301 [US10] Write migration 0011 marketplace tables in services/api/migrations/versions/0011_market.py
- [ ] T302 [P] [US10] Create marketplace schemas in services/api/app/schemas/market.py
- [ ] T303 [US10] Implement listing service with expiry job in services/api/app/services/listings.py
- [ ] T304 [US10] Implement contact-request service with reveal rule in services/api/app/services/contacts.py
- [ ] T305 [US10] Implement marketplace routes in services/api/app/routers/market.py
- [ ] T306 [P] [US10] Build market profile page in apps/web/src/app/[locale]/(app)/market/profile/page.tsx
- [ ] T307 [P] [US10] Build ListingForm in apps/web/src/components/market/ListingForm.tsx
- [ ] T308 [P] [US10] Build ListingCard in apps/web/src/components/market/ListingCard.tsx
- [ ] T309 [P] [US10] Build PriceTrend chart (labels sample data) in apps/web/src/components/market/PriceTrend.tsx
- [ ] T310 [US10] Build listing search page in apps/web/src/app/[locale]/(app)/market/page.tsx
- [ ] T311 [US10] Build contact-requests inbox in apps/web/src/app/[locale]/(app)/market/requests/page.tsx
- [ ] T312 [US10] Add US10 strings in apps/web/messages/en.json, apps/web/messages/fr.json and apps/web/messages/aeb.json

---

## Phase 13: Polish & Cross-Cutting Concerns

- [ ] T313 [P] Accessibility checks with axe on every route in apps/web/tests/e2e/a11y.spec.ts
- [ ] T314 [P] RTL smoke test with a pseudo-RTL locale in apps/web/tests/e2e/rtl.spec.ts
- [ ] T315 [P] 360 px viewport sweep over all routes (SC-007) in apps/web/tests/e2e/viewport-sweep.spec.ts
- [ ] T316 [P] Ingest + fan-out load test for SC-001 in tools/loadtest/ingest.js
- [ ] T317 [P] Security headers (CSP, HSTS, frame-ancestors) in infra/Caddyfile
- [ ] T318 [P] Production image for the API in services/api/Dockerfile
- [ ] T319 [P] Production image for the web app in apps/web/Dockerfile
- [ ] T320 [P] Backup, restore and retention runbook in infra/README.md
- [ ] T321 [P] Firmware integration guide derived from contracts/device-protocol.md in docs/firmware-integration.md
- [ ] T322 [P] Migration tool from a reference is9ini SQLite database to PostgreSQL in tools/migrate_is9ini/migrate.py
- [ ] T323 Run quickstart Q1–Q18 and record results in specs/001-farmlink-platform/quickstart.md

**Deferred / conditional (not scheduled)**: Capacitor native shell (dropped: OQ-3 answered with
web push); Modern Standard Arabic catalog (not required at launch, OQ-1); a Latin-script Derja
catalog if OQ-9 says both scripts; orders and payments (OQ-2); satellite monitoring (research D12).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T001 gates every porting task (T019, T020, T069, T222, T228).
- **Foundational (Phase 2)**: depends on Setup; blocks all stories. Inside it: 2A → 2B → (2C ∥ 2D)
  → 2E; 2F needs 2E's generated client (T076); 2G needs 2B–2D; 2H tests run alongside their
  subjects.
- **User stories (Phase 3+)**: all depend on Phase 2.
- **Polish (Phase 13)**: after the stories you intend to ship.

### User Story Dependencies

| Story | Depends on | Can run in parallel with |
|---|---|---|
| US1 (P1) | Phase 2 | US2, US3, US5 |
| US2 (P2) | Phase 2 (uses US1 pages for navigation only) | US1, US3, US5 |
| US3 (P2) | Phase 2 | US1, US2, US5 |
| US4 (P3) | Phase 2; T204 edits the US2 command service | US5, US6 |
| US5 (P3) | Phase 2 (apply-plant reuses US2 settings service T149) | US1–US4 |
| US6 (P4) | US1 (cached views), US5 (scan queue), US4 (alert engine, for web push T324–T333) | US7 |
| US7 (P4) | Phase 2; T262 edits the US2 command service | US6, US8 |
| US8 (P5) | Phase 2 | US7, US9 |
| US9 (P5) | US4 (alert engine), US8 (crop profiles) | US10 |
| US10 (P6) | US8 (crop profiles, prices) | US9 |

Files edited by more than one story (sequence these): `services/api/app/services/commands.py`
(T151 → T204 → T262), `services/api/app/services/alert_engine.py` (T203 → T330), `apps/web/src/app/sw.ts` (T247 → T331), `services/api/app/routers/device.py` (T068 → T153),
`services/api/app/routers/devices.py` (T118 → T185), `apps/web/messages/*.json` (one strings task
per story), `scans/new/page.tsx` (T239 → T255), `lib/auth/logout.ts` (T094 → T256 → T333).

### Within Each User Story

- Tests first (they must fail), then models → migration → schemas → services → routes → UI
  components → pages → strings.
- Models and schemas marked [P] can be written together; the migration waits for its models.

### Parallel Opportunities

- Phase 1: T003–T006, T008–T013, T015–T026 are all [P].
- Phase 2: all model files T036–T046, security primitives T051/T052/T054/T055/T058–T060, and all
  2H tests.
- Each story: every test task, every model/schema task, and every component task is [P].

---

## Parallel Example: User Story 1

```bash
# Tests together:
T109 services/api/tests/contract/test_monitoring.py
T110 services/api/tests/integration/test_history.py
T111 apps/web/tests/e2e/us1-monitoring.spec.ts

# Schemas together:
T112 services/api/app/schemas/monitoring.py
T113 services/api/app/schemas/events.py

# All UI building blocks together (after Phase 2):
T121 useLiveFeed.ts   T122 applyMessage.ts   T123 channel.ts   T124 relativeTime.ts
T125 MoodCard.tsx     T126 MetricTile.tsx    T127 PumpWaterCard.tsx
T128 DeviceOnlineIndicator.tsx  T129 DeviceCard.tsx  T130 TimeSeriesChart.tsx
T131 EventList.tsx    T132 States.tsx
```

## Parallel Example: User Story 2

```bash
T138 test_hard_limits.py   T139 test_control_roles.py   T140 test_command_seq.py
T145 models/irrigation.py  T146 models/command.py       T148 schemas/control.py
T156 settingsSchema.ts     T157 useCanControl.ts        T158 SettingsForm.tsx
T159 WaterNowButton.tsx    T160 ModeToggle.tsx          T161 CommandHistory.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup (resolve T001 first).
2. Phase 2 Foundational, including the 2H security tests.
3. Phase 3 US1.
4. **Stop and validate** with quickstart Q1–Q3 on desktop and a phone.

### Incremental Delivery

1. Foundation → US1 (MVP: remote monitoring).
2. + US2 (safe control) and US3 (self-service onboarding) → reference parity plus multi-farm.
3. + US4 (ROOTLOOP) and US5 (scanner) → the physical centerpiece and the scanner.
4. + US6 (offline PWA) → field-ready.
5. + US7, US8, US9, US10 as data sources and open questions are resolved.

### Parallel Work Split

After Phase 2, independent streams can proceed: US1 UI, US2 control, US3 management, US5
scanner. Keep one owner per shared file listed under "Files edited by more than one story".

---

## Notes

- [P] = different files and no dependency on incomplete tasks.
- Every constrained field cites `data-model.md` `Entity.field`; constraints are not restated.
- Commit after each task or logical group; never merge with failing `security` or `contract`
  tests (Principle VI).
- Task count: 333.

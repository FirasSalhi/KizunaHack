# Contract: REST API v1

**Source of truth at runtime**: FastAPI's generated OpenAPI document at `/api/openapi.json`. This
file is the human-reviewed contract; the generated schema MUST match it (contract tests).
Clients use the generated TypeScript client in `packages/contracts` (Principle II).

## Conventions

- Base path `/api/v1`. JSON bodies, `snake_case` fields, UTC ISO-8601 timestamps.
- Auth: session cookie (`fl_access`) or `Authorization: Bearer` (native shell only).
- State-changing requests require `X-CSRF-Token` matching the `fl_csrf` cookie (cookie auth only).
- Errors: `{"error": {"code": "string", "message": "human text", "details": {...}}}` with
  status 400/401/403/404/409/413/422/429/503. `403` and `404` for another farm's resources are
  indistinguishable (always `404`) so existence is not revealed (spec US1 scenario 5).
- Pagination: `?cursor=&limit=` (limit ≤ 100) → `{"items": [...], "next_cursor": "..."|null}`.
- Idempotency: `Idempotency-Key` header (UUID) on `POST /scans`; repeated keys return the first
  result.
- **Min role** column: `viewer`, `operator`, `owner` for the farm that owns the resource;
  `auth` = any signed-in user; `public` = no auth; `device` = device signature.

## Auth & account (US1, US3)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| POST | `/auth/login` | public | email + password → sets cookies; returns `Me`. Rate limited (5/min/IP+email). |
| POST | `/auth/refresh` | public (refresh cookie) | Rotates refresh token, new access cookie |
| POST | `/auth/logout` | auth | Revokes current session |
| POST | `/auth/logout-all` | auth | Revokes all sessions of the user |
| GET | `/me` | auth | `Me` = user + memberships `[{farm_id, farm_name, role}]` |
| PATCH | `/me` | auth | name, locale |
| POST | `/invitations/{token}/accept` | public or auth | Accept invite (creates user if needed with password) |
| GET | `/push/vapid-public-key` | auth | Public key the browser needs to subscribe (FR-037) |
| POST | `/me/push-subscriptions` | auth | Register this browser's push subscription (upsert by endpoint) |
| DELETE | `/me/push-subscriptions` | auth | Remove a subscription by endpoint |

## Farms, members, fields (US3)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| POST | `/farms` | auth | Create farm; caller becomes owner |
| GET | `/farms/{farm_id}` | viewer | Farm detail |
| PATCH | `/farms/{farm_id}` | owner | Rename, region |
| GET | `/farms/{farm_id}/members` | viewer | List members |
| PATCH | `/farms/{farm_id}/members/{user_id}` | owner | Change role (last-owner rule → 409) |
| DELETE | `/farms/{farm_id}/members/{user_id}` | owner (or self) | Remove (last-owner rule → 409) |
| POST | `/farms/{farm_id}/invitations` | owner | email + role → invitation (token sent by email) |
| GET/DELETE | `/farms/{farm_id}/invitations[/{id}]` | owner | List / revoke |
| GET/POST | `/farms/{farm_id}/fields` | viewer / owner | List / create field |
| PATCH/DELETE | `/fields/{field_id}` | owner | Edit / delete field |

## Devices and channels (US1, US3)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| GET | `/farms/{farm_id}/devices` | viewer | Devices with `online`, `last_seen_at`, channels, latest status |
| POST | `/farms/{farm_id}/devices` | owner | Register → returns `{device, secret}`; **secret returned once** |
| GET | `/devices/{device_id}` | viewer | Detail |
| PATCH | `/devices/{device_id}` | owner | Name, field/storage link, report interval |
| POST | `/devices/{device_id}/rotate-key` | owner | New secret (once), old key invalid |
| POST | `/devices/{device_id}/revoke` | owner | Status → revoked |
| PUT | `/devices/{device_id}/channels` | owner | Declare channels (also auto-declared from first v2 payload, pending owner confirm) |
| PATCH | `/channels/{channel_id}` | owner | Target range |

## Readings, status, events (US1, US4, US7)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| GET | `/farms/{farm_id}/overview` | viewer | Per device: latest status + latest value per channel + open alerts count |
| GET | `/devices/{device_id}/readings?channel=&range=hour\|day\|week\|month` | viewer | ≤ 300 points; raw for hour/day, `reading_5m`/`reading_1h` aggregates for week/month |
| GET | `/devices/{device_id}/status/history?range=` | viewer | Mood/pump timeline |
| GET | `/farms/{farm_id}/events?range=&type=&cursor=` | viewer | Event log |
| GET | `/farms/{farm_id}/energy/summary?date=` | viewer | Daily production/consumption totals (US7) |

## Control (US2)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| GET | `/devices/{device_id}/settings` | viewer | Settings + `hard_limits` from the device's profile |
| PUT | `/devices/{device_id}/settings` | operator | Body includes `version` (409 on stale). Validates against hard limits (422, never clamp). Emits signed `settings` command. |
| POST | `/devices/{device_id}/commands` | operator | `{type: water_now \| set_mode, value?}` → `{command_id, seq, warning?}`; `warning` e.g. soil wet or battery low |
| GET | `/devices/{device_id}/commands?cursor=` | viewer | Command history with status |

## Water loop & alerts (US4, US9)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| GET | `/farms/{farm_id}/alerts?state=open\|resolved` | viewer | Alerts |
| POST | `/alerts/{alert_id}/acknowledge` | operator | Acknowledge |
| GET/POST | `/channels/{channel_id}/alert-rules` | viewer / owner | Rules for a channel |
| PATCH/DELETE | `/alert-rules/{rule_id}` | owner | Edit / delete |
| GET/POST | `/farms/{farm_id}/storage-units` | viewer / owner | Storage units (US9) |
| PATCH | `/storage-units/{id}` | owner | Name, stored crop (re-derives default rules) |

## Plant scans (US5)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| POST | `/farms/{farm_id}/scans` | viewer | `multipart/form-data` (`photo`, optional `field_id`) + `Idempotency-Key`; ≤ 10 MB → `PlantScan` with `ai_result: PlantIdResult` |
| GET | `/farms/{farm_id}/scans?cursor=` | viewer | History (thumb URLs) |
| GET | `/scans/{scan_id}` | viewer | Detail |
| GET | `/scans/{scan_id}/photo?size=thumb\|full` | viewer | Short-lived signed redirect to object storage |
| PATCH | `/scans/{scan_id}` | author or owner | `{species_id}` → sets `corrected_result` |
| DELETE | `/scans/{scan_id}` | author or owner | Delete scan and photos |
| GET | `/plants/search?q=` | auth | Catalog search (≥ 2 chars) |
| GET | `/plants/{species_id}` | auth | Care sheet |
| POST | `/fields/{field_id}/apply-plant/{species_id}` | operator | Applies recommended settings to the field's devices via the `PUT settings` path |

`PlantIdResult` mirrors the reference `plant_id.identify()` output: `species` (care sheet),
`confidence`, `sure`, `engine`, `alternatives[]`, `health {engine, status, confidence, diseases[]}`.

## Crop planning (US8)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| POST | `/farms/{farm_id}/recommendations` | viewer | Field profile inputs → `RecommendationRun` |
| GET | `/farms/{farm_id}/recommendations?cursor=` | viewer | Past runs |
| GET | `/crops/{crop_id}/companions` | auth | Compatibility list with reasons |
| GET | `/crops/{crop_id}/prices?market=` | auth | `MarketPrice[]` with `source`, `is_sample` |

## Marketplace (US10)

| Method | Path | Min role | Purpose |
|---|---|---|---|
| GET/PUT | `/market/profile` | auth | Own market profile |
| GET | `/market/listings?kind=&crop=&category=&region=&cursor=` | auth | Search active listings |
| POST | `/market/listings` | auth (+ owner of `farm_id` for produce) | Create |
| PATCH | `/market/listings/{id}` | listing owner | Edit, status |
| POST | `/market/listings/{id}/contact` | auth | Create ContactRequest |
| GET | `/market/contact-requests?direction=in\|out` | auth | List |
| POST | `/market/contact-requests/{id}/accept\|decline` | listing owner | Respond; accept reveals contact details to both |

## Device HTTP fallback (see device-protocol.md)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/device/readings` | device | v2 readings batch |
| POST | `/device/status` | device | Status |
| POST | `/device/events` | device | Device event |
| POST | `/device/commands/poll` | device | Fetch pending, unexpired commands |
| POST | `/device/commands/{seq}/ack` | device | Delivery result |
| POST | `/device/telemetry` | device (v1) | Reference-compatible payload (adapter) |

## Health

`GET /health` (public): `{ok, db, mqtt}` — no farm data.

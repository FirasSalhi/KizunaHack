# Data Model: FARMLINK Platform

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Decision**: research.md D3
(PostgreSQL 16 + TimescaleDB)

Conventions: primary keys are UUIDv7 (`id uuid`) unless stated; all times are `timestamptz` UTC;
every table has `created_at` (default `now()`); units are in column names. "→" marks a foreign key.
"Farm-scoped" tables carry `farm_id` and are only accessible through `require_farm_role`.

## Mapping from the reference repository

| Reference (`backend/app/db.py`) | FARMLINK | Change |
|---|---|---|
| `users(email, name, role, salt, pw_hash)` | `User` + `Membership` | Role moves to per-farm membership; PBKDF2 → Argon2id (rehash on next login) |
| — | `Farm`, `Field`, `Device`, `Channel` | New: multi-farm, multi-device, declared channels |
| `telemetry(ts, soil, temp, hum, light, mood, confidence, pump, water_today, mode)` | `Reading` (soil/temp/hum/light as channels) + `DeviceStatus` (mood, confidence, pump, water_today, mode) | Split values from computed state; add `device_id` |
| `settings(key, value)` global | `IrrigationSettings` per device + `HardLimitProfile` | Typed columns, DB check constraints |
| in-memory command counter + deque | `Command` | Persisted sequence and delivery state |
| `events(ts, type, message, data)` | `Event` | Add `farm_id`, `device_id`, `actor_user_id` |
| `plant_scans(..., result)` + files on disk | `PlantScan` | Add `farm_id`, `client_request_id`, `corrected_result`; photos in object storage |

---

## Identity and tenancy

### User
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| email | citext | required, unique, valid email, max 254 |
| name | text | required, 1–80 chars |
| password_hash | text | required, Argon2id encoded |
| locale | text | enum `en`, `fr`, `ar`; default `en` |
| disabled_at | timestamptz | nullable |

### Session
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | → User | required, cascade delete |
| refresh_token_hash | text | required, unique (SHA-256 of token) |
| expires_at | timestamptz | required; created_at + 30 days |
| revoked_at | timestamptz | nullable |
| replaced_by | → Session | nullable (rotation chain; reuse of a rotated token revokes the chain) |
| user_agent | text | max 300 |

### Farm
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| name | text | required, 1–80 |
| region | text | required, one of Tunisia's governorates (reference list) |

### Membership
| Field | Type | Constraints |
|---|---|---|
| farm_id | → Farm | PK part |
| user_id | → User | PK part |
| role | enum | `owner`, `operator`, `viewer`; ordered viewer < operator < owner |

Rule: each farm has ≥1 `owner` at all times (enforced in service + deferred constraint trigger).

### Invitation
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| farm_id | → Farm | required |
| email | citext | required |
| role | enum | `operator`, `viewer`, `owner` |
| token_hash | text | required, unique |
| expires_at | timestamptz | required; created + 7 days |
| accepted_at | timestamptz | nullable |
| invited_by | → User | required |

States: `pending → accepted` or `pending → expired` (by time) or `pending → revoked`.

---

## Farm structure and devices

### Field (farm-scoped)
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| farm_id | → Farm | required |
| name | text | required, 1–80, unique per farm |
| area_m2 | numeric | > 0, nullable |
| soil_type | enum | `sandy`, `loamy`, `clay`, `silty`, `calcareous`, `unknown` |
| latitude / longitude | numeric(9,6) | nullable; −90..90 / −180..180; both or neither |
| crop_profile_id | → CropProfile | nullable |

### HardLimitProfile (platform reference data, not editable by farm users)
| Field | Type | Constraints |
|---|---|---|
| code | text | PK, e.g. `greenhouse_v1`, `rootloop_v1`, `energy_v1`, `storage_v1` |
| max_per_run_ml | int | > 0; `greenhouse_v1` = 150 |
| max_per_day_ml | int | ≥ max_per_run_ml; `greenhouse_v1` = 600 |
| min_battery_v | numeric | nullable |

### Device (farm-scoped)
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK; also the public device id used in topics |
| farm_id | → Farm | required |
| field_id | → Field | nullable |
| storage_unit_id | → StorageUnit | nullable; at most one of field_id / storage_unit_id |
| name | text | required, 1–80 |
| hardware_profile | → HardLimitProfile.code | required |
| key_ciphertext | bytea | required; AES-GCM with server key |
| key_version | int | ≥ 1; increments on rotation |
| status | enum | `active`, `revoked` |
| report_interval_s | int | 1–3600; default 5 |
| last_seen_at | timestamptz | nullable |
| next_command_seq | bigint | ≥ 1; incremented atomically (`UPDATE … RETURNING`) |
| protocol_version | int | `1` (reference payload) or `2` |

Derived: `online = last_seen_at > now() − 2 × report_interval_s`.

### Channel
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| device_id | → Device | required |
| key | text | required, `^[a-z][a-z0-9_]{0,31}$`, unique per device (name in payload) |
| kind | enum | see Channel kinds |
| unit | text | determined by kind |
| valid_min / valid_max | double | physical range; readings outside are rejected |
| target_min / target_max | double | nullable; target_min < target_max |

**Channel kinds** (unit, valid range): `soil_moisture` (% 0–100), `soil_temp` (°C −20–80),
`air_temp` (°C −20–80), `air_humidity` (% 0–100), `light` (lux 0–200000), `tank_level`
(% 0–100), `water_ph` (pH 0–14), `water_ec` (µS/cm 0–20000), `water_turbidity` (NTU 0–4000),
`water_temp` (°C 0–60), `flow` (L/min 0–500), `pressure` (kPa 0–1000), `leak` (0/1),
`battery` (V 0–60), `solar_power` (W 0–100000), `load_power` (W 0–100000), `storage_temp`
(°C −30–60), `storage_humidity` (% 0–100). The four reference values map to `soil_moisture`,
`air_temp`, `air_humidity`, `light`.

---

## Time series (TimescaleDB hypertables)

### Reading
| Field | Type | Constraints |
|---|---|---|
| time | timestamptz | required; measurement time; accepted window now − 24 h .. now + 60 s, else server time |
| channel_id | → Channel | required |
| value | double precision | required; within Channel.valid_min..valid_max |
| received_at | timestamptz | default now() |

PK `(channel_id, time)`; hypertable on `time` (1-day chunks); retention 30 days raw;
continuous aggregates `reading_5m` and `reading_1h` (avg/min/max) kept 2 years (FR-011).

### DeviceStatus
| Field | Type | Constraints |
|---|---|---|
| time | timestamptz | required |
| device_id | → Device | required |
| mood | enum | `happy`, `thirsty`, `drowning`, `too_hot`, `sick` (reference `MOODS`) |
| mood_confidence | real | 0–1 |
| pump_on | boolean | required |
| mode | enum | `auto`, `manual` |
| water_today_ml | real | ≥ 0 |

Status change detection (mood change, pump start/stop) creates `Event` rows, as in the reference
`ingest()`.

---

## Control

### IrrigationSettings (one per device)
| Field | Type | Constraints |
|---|---|---|
| device_id | → Device | PK |
| mode | enum | `auto`, `manual` |
| max_per_run_ml | int | 10 ≤ value ≤ HardLimitProfile.max_per_run_ml |
| max_per_day_ml | int | 50 ≤ value ≤ HardLimitProfile.max_per_day_ml; ≥ max_per_run_ml |
| soil_dry_pct | int | 5–90; < soil_wet_pct |
| soil_wet_pct | int | 10–100 |
| temp_min_c | real | 0–30; < temp_max_c |
| temp_max_c | real | 15–50 |
| plant_profile | text | max 40 |
| version | int | optimistic concurrency; increments on update |
| updated_by | → User | |
| updated_at | timestamptz | |

Ranges are taken from the reference `SettingsIn`. Exceeding values → HTTP 422, never clamped.

### Command
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| device_id | → Device | required |
| seq | bigint | required; unique per device; from Device.next_command_seq |
| type | enum | `water_now`, `set_mode`, `settings` |
| value | jsonb | `set_mode`: `"auto"`/`"manual"`; `settings`: IrrigationSettings snapshot; `water_now`: null |
| issued_by | → User | required |
| issued_at | timestamptz | required |
| expires_at | timestamptz | issued_at + 5 s (reference `COMMAND_MAX_AGE_S`) for live; + 60 s for poll delivery |
| status | enum | `pending → delivered`, `pending → expired`, `delivered → acknowledged` / `rejected` |
| device_reason | text | nullable (e.g. "soil wet") |

---

## Events, alerts, audit

### Event (farm-scoped)
`id`, `farm_id`, `device_id?`, `actor_user_id?`, `type` (enum: `mood`, `pump`, `command`,
`settings`, `auth`, `device`, `plant_scan`, `alert`, `security`), `message` (max 200),
`data` jsonb, `created_at`. Index `(farm_id, created_at desc)`.

### AlertRule
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| channel_id | → Channel | required |
| min_value / max_value | double | at least one set; min < max |
| min_duration_s | int | 0–86400; default 60 |
| severity | enum | `info`, `warning`, `critical` |
| hold_irrigation | boolean | default false |
| enabled | boolean | default true |

### Alert (farm-scoped)
`id`, `farm_id`, `rule_id`, `started_at`, `ended_at?`, `peak_value`, `acknowledged_by?`,
`acknowledged_at?`. State: `open → resolved` (ended_at set); acknowledgement is independent.
At most one open alert per rule (partial unique index on `rule_id where ended_at is null`).

### PushSubscription (user-scoped, FR-037)
`id`, `user_id` → User, `endpoint` (text, unique), `p256dh` (text), `auth` (text),
`user_agent` (text, max 200)?, `created_at`, `last_success_at?`. Deleted when the push service
answers 404/410, when the user turns notifications off on that device, or on logout from it.

### AuditEntry
`id`, `actor_type` (`user`, `device`, `system`), `actor_id?`, `farm_id?`, `action` (text, max 60),
`target` (text, max 120), `ip` inet?, `data` jsonb, `created_at`. Append-only.

---

## Crop health

### PlantScan (farm-scoped)
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| farm_id | → Farm | required |
| field_id | → Field | nullable |
| author_id | → User | required |
| client_request_id | uuid | required, unique per author (idempotent offline retry, FR-035) |
| photo_key / thumb_key | text | object-storage keys; photo ≤ 10 MB upload, stored ≤1280 px, thumb 360 px |
| engine | text | e.g. "Pl@ntNet API", "BioCLIP 2" |
| common_name / scientific_name | text | max 120 |
| confidence | real | 0–1 |
| sure | boolean | confidence ≥ engine threshold |
| ai_result | jsonb | full original result (schema: `PlantIdResult` in contracts) — never modified |
| corrected_result | jsonb | nullable; set on correction |
| corrected_by | → User | nullable |

---

## Decision support

### CropProfile (reference data)
`id`, `scientific_name` (unique), `common_names` jsonb (per locale), `water_min_mm`,
`water_max_mm`, `temp_min_c`, `temp_opt_min_c`, `temp_opt_max_c`, `temp_max_c`, `ph_min`,
`ph_max`, `root_depth` enum (`shallow`, `medium`, `deep`), `light` enum (`full_sun`,
`partial_shade`, `shade`), `storage_temp_min_c`, `storage_temp_max_c`,
`storage_humidity_min_pct`, `storage_humidity_max_pct`, `source` (e.g. "FAO EcoCrop"),
`source_version`. Imported via the reference `build_catalog.py`.

### CropCompatibility (reference data)
`crop_a_id`, `crop_b_id` (→ CropProfile; a < b), `relation` enum (`good`, `neutral`, `avoid`),
`reasons` jsonb (list of `water`, `roots`, `light`, `pests`), `source`.

### MarketPrice (reference data)
`crop_profile_id`, `market` (text), `date`, `price_min`, `price_max`, `unit` (e.g. `TND/kg`),
`source`, `is_sample` boolean (true for placeholder data; UI must label it).

### RecommendationRun (farm-scoped)
`id`, `farm_id`, `field_id?`, `inputs` jsonb (location, soil_type, area_m2, water_available_m3,
budget_tnd), `results` jsonb (ranked list with per-factor scores), `data_versions` jsonb
(source and date per input dataset), `created_by`, `created_at`. Immutable.

### StorageUnit (farm-scoped)
`id`, `farm_id`, `name` (1–80), `kind` enum (`storage`, `drying`), `stored_crop_profile_id?`,
`stored_since?`. Sensors are Devices with `storage_unit_id` set; target ranges default from
CropProfile storage fields into AlertRules.

---

## Marketplace

### MarketProfile
`user_id` (PK → User), `kinds` (set of `farmer`, `buyer`, `supplier`), `display_name` (1–80),
`region`, `phone?` (visible only after accepted contact), `bio?` (max 500).

### Listing
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| kind | enum | `produce`, `request`, `supply` |
| owner_user_id | → User | required |
| farm_id | → Farm | required when kind = `produce` |
| title | text | 3–120 |
| crop_profile_id | → CropProfile | required for `produce`/`request` |
| category | enum | for `supply`: `seeds`, `fertilizer`, `equipment`, `service`, `other` |
| quantity / unit | numeric / enum | quantity > 0; unit `kg`, `t`, `crate`, `unit` |
| region | text | governorate list |
| available_from / available_to | date | from ≤ to |
| status | enum | `draft → active → sold` / `expired` / `removed` |

### ContactRequest
`id`, `listing_id`, `from_user_id`, `message` (1–1000), `status` enum
(`pending → accepted` / `declined`), `created_at`. Contact details are revealed only when
`accepted` (spec US10 scenario 2).

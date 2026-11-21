# Contract: Real-time Channel v1 (WebSocket)

**Endpoint**: `wss://<app-origin>/ws/v1` — same origin as the web app (research.md D4/D6).

## Authentication

- Browser/PWA: the `fl_access` session cookie sent with the upgrade request. No token in the URL
  (replaces the reference `/ws?token=…`).
- Native shell (only if D2 becomes Capacitor): first client message `{"type":"auth","token":"…"}`
  within 5 s, else close `4401`.
- Expired session → close `4401`; client refreshes via `POST /api/v1/auth/refresh` and reconnects.

## Client → server

```json
{"type": "subscribe",   "farm_id": "uuid"}
{"type": "unsubscribe", "farm_id": "uuid"}
{"type": "ping"}
```

Server checks membership on every `subscribe`; failure → `{"type":"error","code":"forbidden"}`
(no detail). One socket may subscribe to several farms.

## Server → client

All messages: `{"type": "...", "farm_id": "uuid", "data": {...}, "sent_at": "ISO-8601"}`.

| type | data | Trigger |
|---|---|---|
| `snapshot` | same shape as `GET /farms/{id}/overview` | Right after `subscribe` |
| `reading` | `{device_id, time, values: {channel_key: number}}` | New readings batch ingested |
| `device_status` | `{device_id, time, mood, mood_confidence, pump_on, mode, water_today_ml, online}` | Status ingested or online state changed |
| `event` | `Event` | Event created |
| `alert` | `Alert` + `{rule, channel_key}` | Alert opened, resolved or acknowledged |
| `command` | `{command_id, device_id, seq, type, status, device_reason?}` | Command status change |
| `membership_revoked` | `{}` | Caller removed from farm → server unsubscribes |
| `pong` | `{}` | Reply to ping |
| `error` | `{code}` | Bad message or forbidden |

## Client behavior (ported from reference `live_feed.dart`)

- On connect: subscribe to the selected farm; apply `snapshot`.
- While disconnected: poll `GET /farms/{id}/overview` every 4 s; show "live updates paused".
- Reconnect with exponential backoff 1 s → 30 s, with jitter.
- Ping every 25 s; consider the socket dead after 2 missed pongs.
- Messages update the TanStack Query cache (no separate store).

## Server fan-out

Ingest → DB commit → `NOTIFY farmlink_farm, '<farm_id>:<message-json>'` (payload ≤ 8 KB; larger
messages send an id and clients refetch) → every API instance `LISTEN`s and forwards to local
subscribers of that farm.

## Versioning

Message schemas live in `packages/contracts/src/realtime.ts` (zod) and are contract-tested
against the Python Pydantic models in `services/api/app/realtime/messages.py`.

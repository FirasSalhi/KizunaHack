# KizunaHack

FARMLINK is a smart-farm platform for Tunisia, with ROOTLOOP, its water-recovery and underground
irrigation subsystem. One Next.js app is both the web dashboard and the installable mobile PWA,
backed by a FastAPI API and PostgreSQL + TimescaleDB.

## Status

**Phase 1 (setup) is done** — tooling, local infrastructure and CI are in place; no product
features yet. The web app shows a placeholder page and the API exposes only
`GET /api/v1/health`. Next is Phase 2 (data layer, auth, ingest, realtime). See
[tasks.md](specs/001-farmlink-platform/tasks.md).

What exists today:

- **Planning (spec-kit)**: [constitution](.specify/memory/constitution.md),
  [spec](specs/001-farmlink-platform/spec.md), [plan](specs/001-farmlink-platform/plan.md),
  [research](specs/001-farmlink-platform/research.md),
  [data model](specs/001-farmlink-platform/data-model.md),
  [contracts](specs/001-farmlink-platform/contracts/) and 333 tasks.
- **`apps/web`**: Next.js 15, React 19, TypeScript strict, Tailwind CSS 4, shadcn/ui config,
  ESLint (with jsx-a11y), Prettier, Vitest, Playwright (desktop and 360×800 phone projects).
- **`services/api`**: Python 3.12 with uv, FastAPI, ruff, mypy, pytest (`contract`, `security`,
  `integration` markers).
- **`packages/contracts`**: `@farmlink/contracts`, the TypeScript client generated from the API's
  OpenAPI schema (generation is wired in Phase 2).
- **`tools/`**: simulator and plant-catalog scripts ported from the is9ini reference.
- **`infra/`**: Docker Compose (TimescaleDB, Mosquitto, SeaweedFS S3, Caddy) and a same-origin
  proxy at `https://farmlink.localhost`.
- **CI**: GitHub Actions running lint, typecheck and tests for web and API.

Decisions so far: interface in French, Tunisian Derja and English; alerts via web push to the
installed PWA; is9ini code is the team's own. Open questions are listed in
[research.md](specs/001-farmlink-platform/research.md#open-questions-consolidated).

## Run it locally

Needs Node 22 + pnpm 9, uv, and Docker.

```bash
pnpm install
uv sync --project services/api
docker compose -f infra/docker-compose.yml up -d db s3 proxy
(cd services/api && uv run uvicorn app.main:app --reload --port 8001)   # terminal 1
pnpm --filter web dev                                                    # terminal 2
```

Open `https://farmlink.localhost` (or `http://localhost:3000`). Ports: web 3000, API 8001,
Postgres 5433, S3 8333. MQTT needs certificates first: see `infra/mosquitto/certs/README.md`.

Tests: `pnpm --filter web test`, `pnpm --filter web e2e`, and `uv run pytest` in `services/api`.

## Repository layout

- `apps/web`: Next.js — dashboard + PWA (the only UI)
- `services/api`: FastAPI backend
- `packages/contracts`: generated OpenAPI types + realtime schemas
- `tools/simulator`, `tools/catalog`: device simulator and plant catalog tools
- `infra/`: Docker Compose, Caddyfile, Mosquitto configuration
- `specs/`, `.specify/`: spec-kit planning documents
- `.claude/skills/`: Claude Code skills used on this project

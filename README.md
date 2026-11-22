# KizunaHack — FARMLINK Smart Farm & ROOTLOOP Platform

FARMLINK is an intelligent precision-agriculture platform designed for Tunisian climates and soil types, featuring ROOTLOOP — an underground water-recovery and closed-loop irrigation subsystem.

The architecture comprises a Next.js web application (dashboard & PWA) and a high-performance FastAPI backend with PostgreSQL + TimescaleDB, Alembic migrations, Redis-backed Celery job processing, and AI vision inference pipelines.

---

## Technology Stack & Architecture

| Component | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 15 (React 19, TypeScript) | User interface (Landing, Auth, Real-time Dashboard) |
| **Backend** | FastAPI | REST API & asynchronous business logic |
| **Language** | Python 3.12+ | Backend services and AI inference |
| **Validation** | Pydantic v2 | Request and response schema validation |
| **ORM** | SQLAlchemy 2.0 (Async) | Asynchronous database operations |
| **Migrations** | Alembic | Database schema migrations and versioning |
| **Database** | PostgreSQL 16 + TimescaleDB | Persistent and hypertable time-series storage |
| **Queue** | Celery | Background worker for asynchronous jobs |
| **Broker** | Redis 7 | Message broker and task distribution |
| **AI** | PyTorch / Transformers / ONNX | Leaf disease and crop health inference |
| **HTTP Client** | HTTPX | Asynchronous external and internal API calls |
| **Authentication** | JWT + Argon2id | Secure user authentication and token rotation |
| **Documentation** | Swagger / OpenAPI | Interactive API documentation (`/api/docs`) |
| **Deployment** | Docker Compose | Containerized local and production environments |

---

## Project Structure

```text
KizunaHack/
├── apps/
│   └── web/                               # Next.js Frontend
│       ├── src/
│       │   ├── app/                       # App Router
│       │   │   ├── (auth)/
│       │   │   │   ├── login/page.tsx     # Sign-in page
│       │   │   │   └── signup/page.tsx    # Sign-up page
│       │   │   ├── (dashboard)/
│       │   │   │   └── dashboard/page.tsx # Main application dashboard
│       │   │   ├── layout.tsx             # Root layout with AuthProvider
│       │   │   ├── page.tsx               # High-fidelity Landing Page
│       │   │   └── providers.tsx          # Client-side providers
│       │   ├── components/
│       │   │   ├── auth/                  # LoginForm, SignupForm, AuthLayout
│       │   │   ├── dashboard/             # DashboardLayout, DashboardOverview
│       │   │   └── landing/               # LandingPage, rootSystem, plateData
│       │   ├── hooks/                     # useAuth hook
│       │   ├── services/                  # apiClient, authService
│       │   └── types/                     # auth and user type contracts
│       ├── tests/                         # Vitest unit tests & Playwright e2e
│       └── Dockerfile                     # Frontend Docker build
├── services/
│   └── api/                               # FastAPI Backend
│       ├── app/
│       │   ├── main.py                    # Application entry point & lifespan
│       │   ├── api/                       # REST endpoints & dependencies
│       │   │   ├── deps.py                # Database and JWT user dependencies
│       │   │   └── v1/
│       │   │       ├── api.py             # Router aggregator
│       │   │       └── endpoints/         # auth, users, health
│       │   ├── core/                      # Configuration, security, logging, database
│       │   │   ├── config.py              # Pydantic BaseSettings
│       │   │   ├── security.py            # Argon2id hashing & PyJWT tokens
│       │   │   ├── database.py            # Async SQLAlchemy engine & session factory
│       │   │   └── logging.py             # Structured logging setup
│       │   ├── models/                    # SQLAlchemy 2.0 models (User, Farm, Membership, Session)
│       │   ├── schemas/                   # Pydantic validation schemas (auth, user, common)
│       │   ├── repositories/              # Repository pattern data access layer
│       │   ├── services/                  # Business logic (AuthService, UserService)
│       │   ├── workers/                   # Celery background job queue & tasks
│       │   ├── ai/                        # AI vision inference & diagnostics pipeline
│       ├── migrations/                    # Alembic migration scripts
│       ├── tests/                         # Pytest unit & security tests
│       └── Dockerfile                     # Backend Docker build
├── infra/                                 # Infrastructure orchestration
│   ├── docker-compose.yml                 # TimescaleDB, Redis, MQTT, S3, Caddy, API
│   ├── Caddyfile                          # Reverse proxy configuration
│   └── mosquitto/                         # Mosquitto MQTT configuration
├── .env.example                           # Global environment template
└── README.md
```

---

## Authentication Flow

1. **Sign Up (`/signup` & `POST /api/v1/auth/signup`)**:
   - Accepts `name`, `email`, `password` (Argon2id hashed), `farm_name`, and `locale`.
   - Provisions the user account and initializes the default `Farm` with the user as `owner`.
   - Issues a signed JWT access token and rotates a high-entropy refresh token.
   - Sets secure HTTP cookies (`fl_access`, `fl_refresh`) and returns token response.
   - Redirects user to `/dashboard`.

2. **Login (`/login` & `POST /api/v1/auth/login`)**:
   - Verifies email and Argon2id password hash.
   - Generates access & refresh tokens and stores active session in the database.
   - Sets secure cookies and redirects user to `/dashboard`.

3. **Main Application (`/dashboard`)**:
   - Protected dashboard presenting active farm zones (Parcels A, B, C).
   - Real-time ROOTLOOP underground water-recovery status and triggers.
   - Live sensor telemetry (VWC soil moisture, temperature, solar voltage, flow rates).
   - AI crop health overview.

---

## Running Locally

### 1. Requirements
- Node.js 22 + pnpm 9
- Python 3.12+ with `uv`
- Docker & Docker Compose

### 2. Environment Configuration
```bash
cp .env.example .env
cp services/api/.env.example services/api/.env
```

### 3. Start Local Infrastructure
```bash
docker compose -f infra/docker-compose.yml up -d db redis s3 proxy
```

### 4. Run Backend (Terminal 1)
```bash
cd services/api
uv sync
uv run uvicorn app.main:app --reload --port 8001
```
Interactive Swagger API documentation: `http://localhost:8001/api/docs`

### 5. Run Frontend (Terminal 2)
```bash
pnpm install
pnpm --filter web dev
```
Open `http://localhost:3000` (or `https://farmlink.localhost` via Caddy).

### 6. Run the crop planner (Terminal 3, optional)
Dashboard → **Crop Planning** shows the MIZU KIZUNA planner (`mizu-kizuna/`), which runs as its own server:
```bash
cd mizu-kizuna
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt   # first time only
.venv/bin/python -m uvicorn main:app --port 8010
```
Port 8010 is the default; set `NEXT_PUBLIC_MIZU_URL` in `apps/web/.env.local` to use another address.

### 7. Plant scanner models (once)
Dashboard → **Plant Scanner** identifies a plant from a photo, checks its health and shows its care sheet
(ported from [is9ini](https://github.com/RaziSnihaa/is9ini)). It runs inside the API and needs its models:
```bash
cd services/api
uv sync --extra bioclip                     # adds PyTorch for the offline BioCLIP 2 engine
uv run python -m app.plants.catalog         # ~2 GB download + catalogue build (GPU helps, CPU works)
# or, without BioCLIP 2:  uv run python -m app.plants.catalog --small   (~35 MB)
```
Engines are tried in order: **Pl@ntNet** (online, best; add a free key from my.plantnet.org as
`PLANTNET_API_KEY` in `services/api/.env`), **BioCLIP 2** (offline), **verdant** (offline, houseplants).
Anyone can scan; scans from signed-in users are saved to their history (table `plant_scans`, photos in
`services/api/data/plant_scans/`). Plant names and care sheets come from English databases.

---

## Running Tests

### Backend Unit Tests (Pytest)
```bash
cd services/api && uv run pytest
```

### Frontend Unit Tests (Vitest)
```bash
cd apps/web && pnpm test
```

### Frontend Typecheck (TypeScript)
```bash
cd apps/web && pnpm typecheck
```

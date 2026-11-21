# Quickstart & Validation Guide: FARMLINK Platform

Runnable scenarios proving each user story works end to end. Paths follow [plan.md](./plan.md).
Endpoint and message details: [contracts/](./contracts/). Entities: [data-model.md](./data-model.md).

## Prerequisites

- Docker with Compose, Node.js 22 LTS + pnpm 9, Python 3.12 + uv.
- Optional: an Android phone and an iPhone on the same network for PWA checks.

## Setup

```bash
pnpm install
uv sync --project services/api
docker compose -f infra/docker-compose.yml up -d db mqtt proxy
uv run --project services/api alembic upgrade head
uv run --project services/api python -m app.seed --demo   # demo farm, owner/operator/viewer, 1 device
pnpm --filter web dev                                     # served behind the proxy at https://farmlink.localhost
uv run --project services/api uvicorn app.main:app --reload --port 8001
```

The seed prints the demo device id and secret (development values only) and writes them to
`tools/simulator/.env.local` (git-ignored).

## Scenario checks

| # | Story | Steps | Expected |
|---|---|---|---|
| Q1 | US1 | `uv run tools/simulator/sim.py --profile greenhouse`; sign in as the seeded viewer; open overview on desktop and at 360×800 | Values change within 3 s; mood card matches simulator; no horizontal scroll |
| Q2 | US1 | Stop the simulator | Device shows "offline · last seen …" after 2× report interval |
| Q3 | US1 | Sign in as a user of a second seeded farm and request the demo farm's overview URL directly | `404`, nothing revealed |
| Q4 | US2 | As operator: set `max_per_run_ml` above the hard limit | `422`, no command in the simulator log |
| Q5 | US2 | As operator: "Water now" | Simulator logs a verified command with increasing `seq`; event log shows actor |
| Q6 | US2 | Replay the same command message to the simulator (`sim.py --replay-last`) | Simulator refuses (`seq` not increasing) |
| Q7 | US2 | As viewer: `curl` the commands endpoint with the viewer cookie | `403` |
| Q8 | US3 | As a new user: create farm → field → register device; start simulator with the new secret | First reading visible in < 10 min total |
| Q9 | US3 | Revoke that device | Simulator's next post → `401`; security event logged |
| Q10 | US4 | `sim.py --profile rootloop --spike turbidity` | One `warning` alert opens, then resolves after the spike |
| Q11 | US5 | Upload each reference test photo on the scan screen | Result with engine, confidence; low confidence labeled "uncertain" |
| Q12 | US5 | Submit the same scan twice with the same `Idempotency-Key` | One scan in history |
| Q19 | US6 | Install the PWA, turn on alerts, close the app; run `sim.py --profile rootloop --spike turbidity` | Phone shows a notification with the alert title only; tapping it opens the alert |
| Q13 | US6 | Install the PWA; load overview; enable airplane mode; reopen | Last data shown with age; controls disabled; scan photo queued |
| Q14 | US6 | Disable airplane mode | Queued scan processed once |
| Q15 | US7 | `sim.py --profile energy --battery-low` then "Water now" | Low-battery warning |
| Q16 | US8 | Request recommendations for the seeded field; halve available water | Ranking changes; water-hungry crops flagged; data sources and dates shown |
| Q17 | US9 | `sim.py --profile storage --humid` with stored crop set | Alert with crop guidance |
| Q18 | US10 | Farmer posts listing; buyer searches by crop/region, sends contact; farmer accepts | Contact details visible to both only after acceptance |

## Automated suites

```bash
uv run --project services/api pytest -m "contract or security"   # required before merge (Principle VI)
uv run --project services/api pytest
pnpm --filter web test
pnpm --filter web e2e        # Playwright: desktop + 360x800 projects, simulator auto-started
pnpm contracts:check         # regenerated client must equal committed client
```

# Inbound Carrier Sales Agent

A voice AI agent that handles inbound calls from freight carriers: verifies them against the FMCSA registry, matches them to available loads, negotiates a rate, and logs the full call for a metrics dashboard.

Built on the HappyRobot platform (voice agent + orchestration) with a FastAPI backend and a Next.js dashboard.

## Live endpoints

| Service | URL |
|---|---|
| API | `https://happyrobot-take-home-production-4ef6.up.railway.app` |
| Dashboard | `https://happyrobot-take-home.vercel.app` |
| Repo | `https://github.com/smmusta1/happyrobot-take-home` |

## Architecture

```
 ┌──────────────────────────┐
 │   Carrier (web call)     │
 └────────────┬─────────────┘
              │ voice
 ┌────────────▼─────────────┐
 │   HappyRobot workflow    │
 │   (voice agent + tools)  │
 └────────────┬─────────────┘
              │ HTTPS / Bearer
 ┌────────────▼─────────────┐      ┌──────────────────┐
 │   FastAPI  (Railway)     │◀─────┤  FMCSA QCMobile  │
 │                          │      └──────────────────┘
 │  /api/v1/carriers/find   │
 │  /api/v1/loads           │      ┌──────────────────┐
 │  /api/v1/loads/{ref}     │◀────▶│  SQLite  (vol.)  │
 │  /api/v1/offers/log      │      └──────────────────┘
 │  /api/v1/negotiate       │
 │  /api/v1/calls/log       │
 │  /api/v1/metrics/summary │
 │  /api/v1/calls[/{id}]    │
 └────────────▲─────────────┘
              │ HTTPS / Bearer (server-side fetch)
 ┌────────────┴─────────────┐
 │   Next.js  (Vercel)      │
 │   Metrics dashboard      │
 └──────────────────────────┘
```

## Features

- **FMCSA-backed carrier verification** — live FMCSA QCMobile lookups with a local cache
- **Bridge-spec load search** — filter-based + single-lookup endpoints
- **Deterministic negotiation** — server-side 3-round policy (anchor at posted rate, cap at hidden `max_buy`, quick-accept at +3%)
- **Auto round reset** — offers scoped by `call_id` + 30-minute window, so every new call starts at round 1
- **Post-call ingestion** — HappyRobot sends classification (outcome + sentiment) and extracted fields at end of call
- **Metrics dashboard** — KPIs, outcome/sentiment breakdown, 14-day trend, call detail with negotiation timeline
- **Bearer auth on every `/api/v1/*` route** (public `/health` only)

## Repo layout

```
api/          FastAPI backend (src, alembic, tests, Dockerfile)
dashboard/    Next.js 14 dashboard (app router, Tailwind, shadcn-style)
```

## Local development

### Prerequisites
- Python 3.12 + `uv`
- Node 22+
- An FMCSA developer webKey (free at fmcsa.dot.gov/developers)

### API

```bash
cd api
cp .env.example .env              # then fill API_KEY + FMCSA_WEB_KEY
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_loads
uv run uvicorn happyrobot_api.main:app --reload
```

API listens on `http://127.0.0.1:8000`. Smoke test:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://127.0.0.1:8000/api/v1/loads?equipment_type=Reefer"
```

### Dashboard

```bash
cd dashboard
npm install
API_BASE_URL=http://127.0.0.1:8000 API_KEY=<your-key> npm run dev
```

Dashboard listens on `http://localhost:3000` and fetches from the API server-side (the API key never reaches the browser).

### Tests

```bash
cd api
uv run pytest                      # 104 tests
uv run pytest -m live              # hits real FMCSA (requires FMCSA_WEB_KEY)
uv run ruff check src tests scripts
```

## Environment variables

| Variable | Service | Description |
|---|---|---|
| `API_KEY` | API, Dashboard | Bearer token required on all `/api/v1/*` routes |
| `FMCSA_WEB_KEY` | API | FMCSA QCMobile developer key (carrier verification) |
| `DATABASE_URL` | API | SQLAlchemy URL; defaults to `sqlite:///./dev.db` |
| `API_BASE_URL` | Dashboard | URL of the deployed API (server-side fetch) |

## Deployment

### API → Railway

1. Connect the repo. Set **Root Directory** to `api`.
2. Environment: set `API_KEY` (strong random), `FMCSA_WEB_KEY`, and (optionally) `DATABASE_URL`.
3. Generate a public domain. The Dockerfile at `api/Dockerfile` runs `alembic upgrade head` + `seed_loads` on startup, so each deploy comes up with 10 seed loads and an empty Call history.
4. Optional: attach a persistent volume at `/data` and set `DATABASE_URL=sqlite:////data/app.db` for persistence across redeploys.

### Dashboard → Vercel

1. Import the repo. Set **Root Directory** to `dashboard`.
2. Environment: `API_BASE_URL` (Railway API URL), `API_KEY` (same value as the API).
3. Deploy. Vercel auto-redeploys on push.

## HappyRobot workflow

The voice agent lives in HappyRobot and hits our API through 4 tool calls during the conversation + 1 POST webhook at end of call.

Topology:

```
[Web Call trigger]
    → [Agent]  (voice persona + prompt)
       inside the agent block:
         [Prompt] → [verify_carrier Tool → Webhook → GET /api/v1/carriers/find]
                  → [find_available_loads Tool → Webhook → GET /api/v1/loads]
                  → [get_load_by_reference Tool → Webhook → GET /api/v1/loads/{ref}]
                  → [negotiate Tool → Webhook → POST /api/v1/negotiate]
    → [AI Classify]   (outcome)
    → [AI Classify]   (sentiment)
    → [AI Extract]    (mc_number, carrier_name, load_id, final_rate, rounds_used, agreement_reached)
    → [Webhook POST]  → /api/v1/calls/log
```

All webhooks use the same API Bearer token. The voice agent's prompt enforces TTS-friendly number speech, a carrier-qualification-first flow, and server-authoritative negotiation (never invent counter-offers).

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness (public, no auth) |
| GET | `/api/v1/carriers/find?mc={mc}` | FMCSA MC verification (cached) |
| GET | `/api/v1/loads` | Search by `origin_state`, `destination_state`, `equipment_type`, `pickup_date` — max 3 results |
| GET | `/api/v1/loads/{reference_number}` | Single load lookup |
| POST | `/api/v1/offers/log` | Bridge-spec offer logging (dedup, 409 on identical repeat) |
| POST | `/api/v1/negotiate` | Evaluate a carrier offer → `accept` / `counter` / `decline` with `agent_counter` and round state |
| POST | `/api/v1/calls/log` | End-of-call webhook — creates a `Call` row and links offers by `(mc, load_id)` |
| GET | `/api/v1/metrics/summary` | Dashboard KPIs |
| GET | `/api/v1/calls` | Paginated call list |
| GET | `/api/v1/calls/{id}` | Call detail (transcript, extracted fields, offer timeline) |
| DELETE | `/api/v1/calls/{id}` | Admin cleanup (cascades to offers) |

### Response envelopes
- GET endpoints use `{statusCode, body: {...}}` (Bridge spec)
- `POST /offers/log` and `POST /calls/log` use flat `{status, ...}` (Bridge spec for write endpoints)
- `POST /negotiate` uses the nested GET shape for its error envelope

## Tech stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, httpx, uv
- **Frontend**: Next.js 14 (app router), TypeScript, Tailwind CSS, Recharts, lucide-react
- **Storage**: SQLite (via SQLAlchemy)
- **Deployment**: Railway (API, Docker), Vercel (dashboard)
- **Testing**: pytest, FastAPI TestClient, 104 tests (including FMCSA live-integration tests)

## Seed data

`api/scripts/seed_loads.py` inserts 10 loads across 5 equipment types (Dry Van, Reefer, Flatbed, Step Deck, Power Only) and 10 US lanes. The script is idempotent and runs automatically on every container start.

The `Carrier` table is populated on demand — first time a new MC is looked up via `verify_carrier`, the FMCSA response is cached locally so subsequent lookups are fast.

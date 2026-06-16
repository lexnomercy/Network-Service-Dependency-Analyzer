# Network Service Dependency Analyzer

Network Service Dependency Analyzer is a monitoring and diagnostics platform for business-critical network services.

The first supported service pack is Zoom. The product is intentionally designed as a generic dependency analyzer so that later service packs can support Microsoft Teams, Webex, Google Meet, Miro, Jira, GitHub, and internal corporate services without changing the core architecture.

## Goal

Show service availability from multiple network locations, explain the full connection and dependency chain, and produce a diagnostic conclusion with evidence, confidence, impact, and recommended actions.

## Core Concepts

- Monitoring agents run checks from different network locations.
- Service packs describe endpoints, dependencies, synthetic journeys, checks, thresholds, and troubleshooting guidance.
- The backend stores raw results, network fingerprints, status history, incidents, and diagnostic conclusions.
- The dashboard shows a status matrix, dependency chain, incident timeline, evidence, and drill-down diagnostics.
- Metrics are exported in a Prometheus-compatible format.

## Initial MVP Scope

- Python backend with FastAPI.
- Python monitoring agent.
- React + TypeScript dashboard.
- YAML service pack configuration.
- SQLite for local MVP, with PostgreSQL-compatible data modeling.
- Zoom service pack as the first implementation.

See [docs/architecture.md](docs/architecture.md) and [docs/mvp-roadmap.md](docs/mvp-roadmap.md).

API contracts are documented in [docs/api-contracts.md](docs/api-contracts.md).

## Local Development

## Quick Start On macOS

Requirements:

- macOS.
- Python 3.11 or newer.
- Node.js 20 or newer.

Prepare the application:

```bash
./setup.command
```

Start the production-like local server:

```bash
./run.command
```

Open:

```text
http://127.0.0.1:8010/
```

Run monitoring checks from the Zoom service pack and submit results to the local backend:

```bash
BACKEND_URL=http://127.0.0.1:8010 .venv/bin/python -m agent.main run-service-pack --pack zoom --submit
```

The monitored Zoom endpoints are configured in [service-packs/zoom/zoom.yaml](service-packs/zoom/zoom.yaml).

### Backend

```bash
cd "Network Service Dependency Analyzer"
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Service packs:

```bash
curl http://127.0.0.1:8000/api/v1/service-packs
curl http://127.0.0.1:8000/api/v1/service-packs/zoom
```

Status overview:

```bash
curl http://127.0.0.1:8000/api/v1/status/overview
```

### Agent

```bash
cd "Network Service Dependency Analyzer"
python3 -m agent.main fingerprint
```

Run a local HTTPS diagnostic sequence and print backend ingestion JSON:

```bash
python3 -m agent.main check --target zoom.us --port 443 --path / --service zoom_meeting_signaling
```

Run all supported HTTPS checks declared in the Zoom service pack:

```bash
python3 -m agent.main run-service-pack --pack zoom
```

The MVP sequence currently runs:

- DNS resolve.
- TCP connect.
- TLS handshake.
- HTTP HEAD.

If an upstream step fails, downstream checks are emitted as `skipped` with `unknown` severity.

Submit the generated batch to a running backend:

```bash
BACKEND_URL=http://127.0.0.1:8000 python3 -m agent.main run-service-pack --pack zoom --submit
```

### Frontend

```bash
cd "Network Service Dependency Analyzer/frontend"
npm install
npm run dev
```

The dashboard expects the backend at `http://127.0.0.1:8000`.
If that port is busy, point Vite to another backend port:

```bash
BACKEND_URL=http://127.0.0.1:8010 npm run dev
```

Current dashboard MVP includes a static mock view for:

- service/location status matrix.
- connection chain.
- diagnostic conclusion.
- evidence.
- recommended actions.

The dashboard reads live data from `/api/v1/status/overview` and falls back to mock data when no backend data is available.

### Current Local Flow

If port `8000` is busy, run backend on `8010`:

```bash
cd "Network Service Dependency Analyzer"
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

Run frontend against that backend:

```bash
cd "Network Service Dependency Analyzer/frontend"
BACKEND_URL=http://127.0.0.1:8010 npm run dev
```

Submit Zoom service pack checks:

```bash
cd "Network Service Dependency Analyzer"
BACKEND_URL=http://127.0.0.1:8010 .venv/bin/python -m agent.main run-service-pack --pack zoom --submit
```

### Production-Like Local Run

Build the dashboard and serve it from the backend:

```bash
cd "Network Service Dependency Analyzer/frontend"
npm run build

cd ..
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010/
```

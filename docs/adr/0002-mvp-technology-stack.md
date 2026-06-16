# ADR 0002: MVP Technology Stack

## Status

Accepted

## Context

The MVP needs to validate the product model quickly:

- distributed checks.
- backend ingestion.
- dependency-aware status.
- diagnostic conclusions with evidence and confidence.
- dashboard visualization.

The long-term production agent may be better in Go, but speed of iteration matters for the MVP.

## Decision

Use the following MVP stack:

- Backend: Python + FastAPI.
- Agent: Python CLI.
- Frontend: React + TypeScript + Vite.
- Local storage: SQLite.
- Production-compatible modeling target: PostgreSQL.
- Configuration: YAML service packs.
- Deployment target: Docker Compose.

## Consequences

- Python allows faster iteration for check logic and diagnostic rules.
- The agent can later be rewritten in Go without changing backend contracts.
- SQLite keeps local development light.
- Schema and query design should avoid SQLite-only assumptions where practical.

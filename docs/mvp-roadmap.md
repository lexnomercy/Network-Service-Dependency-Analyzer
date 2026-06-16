# MVP Roadmap

## MVP Principle

Build the smallest useful diagnostic product, not a full enterprise observability platform on day one.

The MVP must already demonstrate the core idea:

```text
raw network checks -> dependency status -> diagnostic conclusion with evidence
```

## Phase 1: Project Skeleton and Architecture

- repository structure.
- architecture document.
- ADRs.
- initial Zoom service pack YAML.

Exit criteria:

- project has a clear structure and documented technical direction.

## Phase 2: Backend Scaffold

- FastAPI application.
- health endpoint.
- config loader for service packs.
- initial API schemas.
- local SQLite database setup.
- React dashboard shell.
- Python agent CLI shell.

Exit criteria:

- backend starts locally.
- service pack can be loaded and returned through API.
- agent can print a network fingerprint stub.
- dashboard can show backend health.

## Phase 3: Agent Scaffold

- Python CLI agent.
- local config fetch.
- DNS check.
- TCP connect check.
- TLS handshake check.
- HTTP check.
- result batch submission.

Exit criteria:

- agent can run checks from the local machine and submit results.

Current MVP implementation:

- DNS, TCP, TLS, and HTTP checks are implemented with the Python standard library.
- The agent prints backend-compatible batch JSON.
- Optional `--submit` posts the batch to `/api/v1/check-results/bulk`.

## Phase 4: Data Model and Diagnostic Conclusion

- agents.
- locations.
- services.
- endpoint groups.
- endpoints.
- endpoint DNS history.
- check results.
- network fingerprints.
- incidents.
- diagnostic conclusions.

Exit criteria:

- backend stores raw results and creates a basic diagnostic conclusion for common failure cases.

Current MVP shortcut:

- use Pydantic schemas for API contracts.
- use an in-memory repository before adding persistent storage.

## Phase 5: Dashboard MVP

- status overview.
- service/location matrix.
- dependency chain view.
- incident list.
- diagnostic conclusion drill-down.

Exit criteria:

- user can see where a Zoom service path failed and why the system thinks so.

Current MVP shortcut:

- render a static mock dashboard first.
- wire live API data after dependency installation and local backend launch.

## Phase 6: Prometheus and Alerting

- `/metrics` endpoint.
- webhook alert channel.
- Telegram alert channel.
- basic deduplication.

Exit criteria:

- status can be consumed by Grafana/Prometheus.
- critical incidents can notify an operator.

## Deferred Enterprise Features

- dynamic baseline engine.
- topology versioning.
- synthetic user journeys using real authenticated or controlled scenarios.
- multi-tenant RBAC.
- SSO/SAML/OIDC.
- Kafka/NATS event pipeline.
- high availability.
- advanced route comparison.
- AI-assisted diagnostic conclusions.

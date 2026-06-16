# Target Architecture

## Product Positioning

This project is not only a Zoom monitor. It is a Network Service Dependency Analyzer where Zoom is the first supported service pack.

The core platform should remain service-agnostic. Service-specific behavior belongs in service packs: endpoint groups, dependency graph, synthetic user journeys, thresholds, expected responses, and diagnostic recommendations.

## High-Level Architecture

```text
Monitoring Agents
  -> Ingestion API
  -> Raw Result Storage
  -> Correlation Engine
  -> Diagnostic Conclusion Engine
  -> Incident Engine
  -> Backend API
  -> Dashboard / Alerts / Prometheus Export
```

## Diagnostic Chain

```text
Local Agent
  -> LAN
  -> DNS
  -> Proxy / Firewall / NAT
  -> Internet Route
  -> Service Edge
  -> Core Service
  -> Dependent Service
  -> Synthetic User Journey
```

The chain is used for visual diagnosis. When a step fails, downstream checks can be marked as blocked or unknown instead of incorrectly shown as healthy.

## Main Components

### Agent

Runs from a specific location and performs:

- DNS resolution.
- TCP connect.
- TLS handshake.
- HTTP/API checks.
- UDP/media reachability checks.
- traceroute/MTR-style route diagnostics.
- latency, packet loss, jitter, timeout, reset/refused, and certificate validation.
- network fingerprint capture.

The agent should buffer results when the backend is unreachable.

### Backend

Responsible for:

- agent registration and heartbeats.
- receiving check results.
- loading service pack configuration.
- calculating service and dependency status.
- generating diagnostic conclusions.
- managing incidents and alerts.
- exposing dashboard APIs and Prometheus metrics.

### Service Pack Registry

Service packs are declarative YAML files. The first service pack is Zoom.

Each service pack can define:

- services.
- endpoint groups.
- endpoints.
- dependency graph.
- synthetic journeys.
- checks.
- thresholds.
- troubleshooting recommendations.

### Correlation Engine

Converts raw technical signals into service status and root-cause hypotheses.

Inputs:

- check results.
- network fingerprints.
- endpoint DNS history.
- topology history.
- service dependencies.
- synthetic journey results.

Outputs:

- service status.
- incident candidates.
- evidence.
- confidence score.
- impact assessment.

### Diagnostic Conclusion Engine

Produces the final interpreted conclusion for an incident:

```json
{
  "root_cause": "Corporate firewall",
  "root_cause_confidence": 0.94,
  "confidence_level": "high",
  "failed_step": "proxy_firewall_nat",
  "affected_services": ["zoom_meeting", "zoom_chat"],
  "evidence": [
    "TCP/443 timed out from agents behind the same firewall profile",
    "DNS resolution succeeded",
    "Cloud agent outside corporate network succeeded"
  ],
  "recommended_actions": [
    "Check outbound TCP/443 firewall policy",
    "Verify proxy authentication and bypass rules"
  ]
}
```

## Data Flow

```text
1. Admin configures service packs.
2. Backend exposes effective configuration to agents.
3. Agents execute scheduled checks.
4. Agents send result batches to ingestion API.
5. Backend stores raw check results and metrics.
6. Correlation engine updates status and incident candidates.
7. Diagnostic conclusion engine creates or updates conclusions.
8. Incident engine sends notifications.
9. Dashboard and Prometheus exporter expose current and historical state.
```

## Severity

- `info`: healthy or informational.
- `warning`: degraded but not fully unavailable.
- `critical`: unavailable or a critical dependency failed.
- `unknown`: insufficient data, skipped check, or offline agent.

## Impact

Severity and impact are separate.

Severity answers: how technically bad is the failure?

Impact answers: how important is it for the business?

Impact fields:

- affected users estimate.
- affected locations.
- affected services.
- affected VIP locations.
- business impact: low, medium, high, critical.

## Storage Areas

MVP can use SQLite for simple local execution, but schemas should remain compatible with PostgreSQL.

Enterprise storage split:

- PostgreSQL: configuration, agents, incidents, conclusions, users.
- TimescaleDB or ClickHouse: check history and metrics.
- Redis: current state cache and background coordination.
- Object storage: raw route dumps and diagnostic bundles.

## Dashboard Requirements

The dashboard must include:

- service status matrix.
- location by service view.
- dependency chain map.
- incident timeline.
- diagnostic conclusion panel.
- evidence panel.
- network fingerprint details.
- check result drill-down.
- metrics charts for latency, packet loss, jitter, DNS time, TCP connect time, TLS handshake time, and HTTP response time.

## Alerting

Supported channels:

- email.
- webhook.
- Telegram.
- Microsoft Teams.

Alerting must support:

- deduplication.
- grouping.
- suppression.
- maintenance windows.
- flapping protection.
- renotification intervals.

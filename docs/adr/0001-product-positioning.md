# ADR 0001: Product Positioning

## Status

Accepted

## Context

The first use case is monitoring Zoom availability from multiple corporate network locations. However, the underlying diagnostic model is not specific to Zoom. The same ideas apply to Microsoft Teams, Webex, Google Meet, Miro, Jira, GitHub, and internal services.

If the application is designed as a Zoom-only monitor, future service expansion will require major architectural changes.

## Decision

The product will be positioned and structured as a Network Service Dependency Analyzer.

Zoom will be implemented as the first service pack.

## Consequences

- Core entities must be service-agnostic.
- Zoom-specific endpoints, dependencies, checks, and recommendations live in `service-packs/zoom/`.
- Backend APIs should use generic terms such as service, endpoint group, dependency, journey, and diagnostic conclusion.
- The frontend may show Zoom-specific labels when the Zoom service pack is active, but should not hard-code Zoom as the only possible service.

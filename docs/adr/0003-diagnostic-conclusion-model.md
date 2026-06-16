# ADR 0003: Diagnostic Conclusion Model

## Status

Accepted

## Context

Raw check results and incidents are not enough for NOC users. Operators need an explicit answer:

- what is the likely root cause?
- how confident is the system?
- what evidence supports the conclusion?
- what services and users are affected?
- what should be checked next?

Without a first-class diagnostic conclusion, this information becomes scattered across incidents, check results, and UI-specific logic.

## Decision

Create `diagnostic_conclusion` as a first-class entity.

It should include:

- incident id.
- root cause.
- root cause confidence as a numeric value.
- confidence level: low, medium, high, confirmed.
- failed chain step.
- affected services.
- affected dependencies.
- affected locations.
- affected users estimate.
- business impact.
- evidence list.
- recommended actions.
- engine version.
- generated timestamp.

## Consequences

- The dashboard can show an explainable diagnostic summary.
- Alerts can include useful context instead of only technical failure messages.
- Future AI correlation can generate or enrich diagnostic conclusions without changing the incident model.

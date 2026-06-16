from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from backend.schemas import (
    Agent,
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    CheckResult,
    CheckResultBatch,
    DiagnosticConclusion,
    Evidence,
    Incident,
    Severity,
    StatusOverview,
)
from backend.service_packs import list_service_packs


class InMemoryRepository:
    def __init__(self) -> None:
        self.agents: dict[str, Agent] = {}
        self.check_results: deque[CheckResult] = deque(maxlen=500)
        self.incidents: dict[str, Incident] = {}
        self.diagnostic_conclusions: dict[str, DiagnosticConclusion] = {}

    def register_agent(self, request: AgentRegistrationRequest) -> Agent:
        existing = self.agents.get(request.id)
        if existing:
            updated = existing.model_copy(
                update={
                    "name": request.name,
                    "location_id": request.location_id,
                    "version": request.version,
                    "hostname": request.hostname,
                }
            )
            self.agents[request.id] = updated
            return updated

        agent = Agent(
            id=request.id,
            name=request.name,
            location_id=request.location_id,
            version=request.version,
            hostname=request.hostname,
        )
        self.agents[agent.id] = agent
        return agent

    def heartbeat(self, agent_id: str, request: AgentHeartbeatRequest) -> Agent:
        agent = self.agents.get(agent_id)
        if not agent:
            agent = Agent(id=agent_id, name=agent_id, location_id="unknown")

        updated = agent.model_copy(
            update={
                "status": request.status,
                "version": request.version or agent.version,
                "last_seen_at": request.reported_at,
            }
        )
        self.agents[agent_id] = updated
        return updated

    def ingest_check_batch(self, batch: CheckResultBatch) -> dict[str, int]:
        ingested = 0
        incidents_created = 0

        for result in batch.results:
            stored = result.model_copy(update={"id": result.id or str(uuid4())})
            self.check_results.appendleft(stored)
            ingested += 1

            if stored.severity == Severity.critical:
                incident, created = self._upsert_incident(stored)
                if created:
                    incidents_created += 1
                self._upsert_diagnostic_conclusion(incident, stored)

        return {"ingested": ingested, "incidents_created": incidents_created}

    def status_overview(self) -> StatusOverview:
        packs = list_service_packs()
        open_incidents = [
            incident for incident in self.incidents.values() if incident.status == "open"
        ]

        return StatusOverview(
            services_total=len(packs),
            agents_total=len(self.agents),
            open_incidents=len(open_incidents),
            latest_results=list(self.check_results)[:20],
            incidents=list(open_incidents)[:20],
            diagnostic_conclusions=list(self.diagnostic_conclusions.values())[:20],
        )

    def _upsert_incident(self, result: CheckResult) -> tuple[Incident, bool]:
        fingerprint = self._incident_fingerprint(result)
        existing = self.incidents.get(fingerprint)
        now = datetime.now(timezone.utc)
        title = f"{result.service_id} {result.error_type or result.check_type} from {result.location_id}"

        if existing:
            updated = existing.model_copy(
                update={
                    "severity": result.severity,
                    "updated_at": now,
                    "summary": result.technical_description,
                }
            )
            self.incidents[fingerprint] = updated
            return updated, False

        incident = Incident(
            id=str(uuid4()),
            title=title,
            service_id=result.service_id,
            location_id=result.location_id,
            agent_id=result.agent_id,
            severity=result.severity,
            root_step=self._failed_step(result),
            error_type=result.error_type,
            fingerprint=fingerprint,
            summary=result.technical_description,
        )
        self.incidents[fingerprint] = incident
        return incident, True

    def _upsert_diagnostic_conclusion(self, incident: Incident, result: CheckResult) -> None:
        evidence = list(result.evidence)
        if result.technical_description:
            evidence.append(
                Evidence(
                    type="check_result",
                    message=result.technical_description,
                    source="ingestion",
                    weight=0.4,
                )
            )

        if not evidence:
            evidence.append(
                Evidence(
                    type="status",
                    message=f"{result.check_type} reported {result.status}",
                    source="ingestion",
                    weight=0.2,
                )
            )

        confidence = min(0.35 + sum(item.weight for item in evidence), 0.95)
        level = "low"
        if confidence >= 0.85:
            level = "high"
        elif confidence >= 0.6:
            level = "medium"

        conclusion = DiagnosticConclusion(
            id=str(uuid4()),
            incident_id=incident.id,
            root_cause=result.probable_cause or self._default_root_cause(result),
            root_cause_confidence=confidence,
            confidence_level=level,
            failed_step=incident.root_step,
            affected_services=[result.service_id],
            affected_locations=[result.location_id],
            business_impact="high" if result.severity == Severity.critical else "medium",
            evidence=evidence,
            recommended_actions=result.recommended_actions,
        )
        self.diagnostic_conclusions[incident.id] = conclusion

    @staticmethod
    def _incident_fingerprint(result: CheckResult) -> str:
        return ":".join(
            [
                result.location_id,
                result.service_id,
                result.endpoint_group_id or "service",
                result.error_type or result.check_type,
            ]
        )

    @staticmethod
    def _failed_step(result: CheckResult) -> str | None:
        for step in result.chain:
            if step.severity == Severity.critical or step.status in {"failed", "timeout"}:
                return step.step
        return None

    @staticmethod
    def _default_root_cause(result: CheckResult) -> str:
        if result.error_type:
            return result.error_type.replace("_", " ")
        return f"{result.check_type} failure"


repository = InMemoryRepository()

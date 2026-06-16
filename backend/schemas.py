from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Severity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"
    unknown = "unknown"


class CheckStatus(StrEnum):
    success = "success"
    failed = "failed"
    timeout = "timeout"
    skipped = "skipped"
    unknown = "unknown"


class IncidentStatus(StrEnum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"
    suppressed = "suppressed"


class ConfidenceLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    confirmed = "confirmed"


class BusinessImpact(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AgentRegistrationRequest(BaseModel):
    id: str
    name: str
    location_id: str
    version: str | None = None
    hostname: str | None = None


class AgentHeartbeatRequest(BaseModel):
    status: Literal["online", "degraded", "offline"] = "online"
    version: str | None = None
    network_fingerprint: "NetworkFingerprint | None" = None
    reported_at: datetime = Field(default_factory=utc_now)


class Agent(BaseModel):
    id: str
    name: str
    location_id: str
    version: str | None = None
    hostname: str | None = None
    status: Literal["online", "degraded", "offline", "unknown"] = "unknown"
    last_seen_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class NetworkFingerprint(BaseModel):
    agent_id: str
    location_id: str
    hostname: str | None = None
    os: str | None = None
    public_ip: str | None = None
    asn: int | None = None
    provider: str | None = None
    resolver: str | None = None
    proxy_enabled: bool = False
    nat_type: str | None = None
    firewall_profile: str | None = None
    captured_at: datetime = Field(default_factory=utc_now)


class CheckMetricSet(BaseModel):
    latency_ms: float | None = None
    packet_loss_ratio: float | None = None
    jitter_ms: float | None = None
    dns_time_ms: float | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    http_time_ms: float | None = None
    hop_count: int | None = None


class ChainStepResult(BaseModel):
    step: str
    status: CheckStatus
    severity: Severity = Severity.unknown
    node_address: str | None = None
    description: str | None = None
    error_type: str | None = None


class Evidence(BaseModel):
    type: str
    message: str
    source: str
    weight: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckResult(BaseModel):
    id: str | None = None
    agent_id: str
    location_id: str
    service_id: str
    endpoint_group_id: str | None = None
    endpoint_id: str | None = None
    endpoint_host: str | None = None
    endpoint_port: int | None = None
    endpoint_path: str | None = None
    check_type: str
    status: CheckStatus
    severity: Severity
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: float | None = None
    error_type: str | None = None
    error_code: str | None = None
    technical_description: str | None = None
    probable_cause: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    metrics: CheckMetricSet = Field(default_factory=CheckMetricSet)
    chain: list[ChainStepResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class CheckResultBatch(BaseModel):
    agent_id: str
    location_id: str
    results: list[CheckResult]
    network_fingerprint: NetworkFingerprint | None = None
    submitted_at: datetime = Field(default_factory=utc_now)


class Incident(BaseModel):
    id: str
    title: str
    service_id: str
    location_id: str
    agent_id: str | None = None
    severity: Severity
    status: IncidentStatus = IncidentStatus.open
    root_step: str | None = None
    error_type: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None
    fingerprint: str
    summary: str | None = None


class DiagnosticConclusion(BaseModel):
    id: str
    incident_id: str
    root_cause: str
    root_cause_confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    failed_step: str | None = None
    affected_services: list[str] = Field(default_factory=list)
    affected_dependencies: list[str] = Field(default_factory=list)
    affected_locations: list[str] = Field(default_factory=list)
    affected_users_estimate: int | None = None
    business_impact: BusinessImpact = BusinessImpact.low
    evidence: list[Evidence] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    engine_version: str = "mvp-rule-engine-0.1"


class StatusOverview(BaseModel):
    services_total: int
    agents_total: int
    open_incidents: int
    latest_results: list[CheckResult]
    incidents: list[Incident]
    diagnostic_conclusions: list[DiagnosticConclusion]

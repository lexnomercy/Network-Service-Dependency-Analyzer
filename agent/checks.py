from __future__ import annotations

import http.client
import socket
import ssl
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CheckContext:
    agent_id: str
    location_id: str
    service_id: str
    endpoint_group_id: str | None
    target: str
    port: int
    path: str
    timeout: float


@dataclass
class CheckResultBuilder:
    context: CheckContext
    check_type: str
    started_at: str = field(default_factory=utc_now_iso)
    status: str = "unknown"
    severity: str = "unknown"
    finished_at: str | None = None
    duration_ms: float | None = None
    error_type: str | None = None
    error_code: str | None = None
    technical_description: str | None = None
    probable_cause: str | None = None
    recommended_actions: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    chain: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def node_address(self) -> str:
        return f"{self.context.target}:{self.context.port}"

    def finish(self, status: str, severity: str) -> dict[str, Any]:
        self.status = status
        self.severity = severity
        self.finished_at = utc_now_iso()
        started = datetime.fromisoformat(self.started_at)
        finished = datetime.fromisoformat(self.finished_at)
        self.duration_ms = round((finished - started).total_seconds() * 1000, 2)
        return self.to_result()

    def fail(
        self,
        *,
        status: str,
        error_type: str,
        description: str,
        probable_cause: str,
        actions: list[str],
        chain_step: str,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        self.error_type = error_type
        self.error_code = error_code
        self.technical_description = description
        self.probable_cause = probable_cause
        self.recommended_actions = actions
        self.chain.append(
            {
                "step": chain_step,
                "status": status,
                "severity": "critical",
                "node_address": self.node_address,
                "description": description,
                "error_type": error_type,
            }
        )
        self.evidence.append(
            {
                "type": "check_result",
                "message": description,
                "source": "agent",
                "weight": 0.5,
            }
        )
        return self.finish(status, "critical")

    def to_result(self) -> dict[str, Any]:
        return {
            "agent_id": self.context.agent_id,
            "location_id": self.context.location_id,
            "service_id": self.context.service_id,
            "endpoint_group_id": self.context.endpoint_group_id,
            "endpoint_host": self.context.target,
            "endpoint_port": self.context.port,
            "endpoint_path": self.context.path,
            "check_type": self.check_type,
            "status": self.status,
            "severity": self.severity,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "error_code": self.error_code,
            "technical_description": self.technical_description,
            "probable_cause": self.probable_cause,
            "recommended_actions": self.recommended_actions,
            "metrics": self.metrics,
            "chain": self.chain,
            "evidence": self.evidence,
            "raw_payload": {
                "endpoint": {
                    "host": self.context.target,
                    "port": self.context.port,
                    "path": self.context.path,
                },
                **self.raw_payload,
            },
        }


def run_dns_check(context: CheckContext) -> tuple[dict[str, Any], list[str]]:
    builder = CheckResultBuilder(context=context, check_type="dns")
    started = time.monotonic()
    try:
        records = socket.getaddrinfo(context.target, context.port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return (
            builder.fail(
                status="failed",
                error_type="dns_resolve_failed",
                error_code=str(exc.errno),
                description=f"DNS resolution failed for {context.target}: {exc}",
                probable_cause="DNS resolver, split DNS, or hostname issue",
                actions=[
                    "Compare resolution from another resolver.",
                    "Check corporate DNS forwarding rules.",
                    "Validate resolver reachability from the affected agent.",
                ],
                chain_step="dns",
            ),
            [],
        )
    except TimeoutError as exc:
        return (
            builder.fail(
                status="timeout",
                error_type="dns_timeout",
                error_code=type(exc).__name__,
                description=f"DNS resolution timed out for {context.target}",
                probable_cause="DNS resolver timeout or local network issue",
                actions=[
                    "Check resolver availability from the affected network.",
                    "Compare with a secondary resolver.",
                ],
                chain_step="dns",
            ),
            [],
        )

    duration = round((time.monotonic() - started) * 1000, 2)
    ips = sorted({record[4][0] for record in records})
    builder.metrics["dns_time_ms"] = duration
    builder.raw_payload["resolved_ips"] = ips
    builder.chain.append(
        {
            "step": "dns",
            "status": "success",
            "severity": "info",
            "node_address": builder.node_address,
            "description": f"{context.target} resolved to {', '.join(ips[:5])}",
        }
    )
    builder.evidence.append(
        {
            "type": "dns",
            "message": f"Resolved {context.target} to {', '.join(ips[:5])}",
            "source": "agent",
            "weight": 0.2,
            "metadata": {"resolved_ips": ips},
        }
    )
    return builder.finish("success", "info"), ips


def run_tcp_check(context: CheckContext) -> dict[str, Any]:
    builder = CheckResultBuilder(context=context, check_type="tcp")
    started = time.monotonic()
    try:
        with socket.create_connection((context.target, context.port), timeout=context.timeout):
            pass
    except TimeoutError as exc:
        return builder.fail(
            status="timeout",
            error_type="tcp_timeout",
            error_code=type(exc).__name__,
            description=f"TCP connect to {context.target}:{context.port} timed out after {context.timeout} seconds",
            probable_cause="Firewall, proxy, NAT, or routing issue",
            actions=[
                "Check outbound firewall policy for the destination host and port.",
                "Compare with an agent outside the corporate network.",
                "Run route diagnostics to the same endpoint.",
            ],
            chain_step="proxy_firewall_nat",
        )
    except ConnectionRefusedError as exc:
        return builder.fail(
            status="failed",
            error_type="tcp_refused",
            error_code=type(exc).__name__,
            description=f"TCP connect to {context.target}:{context.port} was refused",
            probable_cause="Remote service refused the connection or an intermediate device rejected it",
            actions=[
                "Validate the expected destination port.",
                "Check whether a proxy or firewall is actively rejecting the connection.",
            ],
            chain_step="service_edge",
        )
    except OSError as exc:
        return builder.fail(
            status="failed",
            error_type="tcp_connect_failed",
            error_code=type(exc).__name__,
            description=f"TCP connect to {context.target}:{context.port} failed: {exc}",
            probable_cause="Local network, firewall, NAT, provider route, or remote edge issue",
            actions=[
                "Compare with another agent in the same location.",
                "Check local routing and firewall logs.",
            ],
            chain_step="internet_route",
        )

    duration = round((time.monotonic() - started) * 1000, 2)
    builder.metrics["tcp_connect_ms"] = duration
    builder.chain.extend(
        [
            {
                "step": "proxy_firewall_nat",
                "status": "success",
                "severity": "info",
                "node_address": builder.node_address,
            },
            {
                "step": "internet_route",
                "status": "success",
                "severity": "info",
                "node_address": builder.node_address,
            },
            {
                "step": "service_edge",
                "status": "success",
                "severity": "info",
                "node_address": builder.node_address,
            },
        ]
    )
    builder.evidence.append(
        {
            "type": "tcp",
            "message": f"TCP connect to {context.target}:{context.port} succeeded in {duration} ms",
            "source": "agent",
            "weight": 0.2,
        }
    )
    return builder.finish("success", "info")


def run_tls_check(context: CheckContext) -> dict[str, Any]:
    builder = CheckResultBuilder(context=context, check_type="tls")
    started = time.monotonic()
    try:
        tls_context = ssl.create_default_context()
        with socket.create_connection((context.target, context.port), timeout=context.timeout) as sock:
            with tls_context.wrap_socket(sock, server_hostname=context.target) as tls_sock:
                cert = tls_sock.getpeercert()
                cipher = tls_sock.cipher()
                version = tls_sock.version()
    except ssl.SSLCertVerificationError as exc:
        return builder.fail(
            status="failed",
            error_type="tls_certificate_error",
            error_code=type(exc).__name__,
            description=f"TLS certificate verification failed for {context.target}: {exc}",
            probable_cause="TLS inspection, stale trust store, or endpoint certificate issue",
            actions=[
                "Check corporate TLS inspection policy.",
                "Validate the certificate chain from the affected agent.",
                "Compare the certificate issuer with a known-good network.",
            ],
            chain_step="proxy_firewall_nat",
        )
    except TimeoutError as exc:
        return builder.fail(
            status="timeout",
            error_type="tls_timeout",
            error_code=type(exc).__name__,
            description=f"TLS handshake with {context.target}:{context.port} timed out",
            probable_cause="Firewall, proxy, NAT, route issue, or overloaded service edge",
            actions=[
                "Check whether TCP succeeds while TLS times out.",
                "Inspect proxy/TLS inspection logs.",
            ],
            chain_step="service_edge",
        )
    except ssl.SSLError as exc:
        return builder.fail(
            status="failed",
            error_type="tls_handshake_failed",
            error_code=type(exc).__name__,
            description=f"TLS handshake with {context.target}:{context.port} failed: {exc}",
            probable_cause="TLS inspection, protocol mismatch, or service edge issue",
            actions=[
                "Validate SNI and certificate chain.",
                "Compare TLS handshake from another location.",
            ],
            chain_step="service_edge",
        )
    except OSError as exc:
        return builder.fail(
            status="failed",
            error_type="tls_connect_failed",
            error_code=type(exc).__name__,
            description=f"TLS connection to {context.target}:{context.port} failed: {exc}",
            probable_cause="Network path or service edge issue",
            actions=[
                "Check TCP result for the same endpoint.",
                "Compare with another agent.",
            ],
            chain_step="internet_route",
        )

    duration = round((time.monotonic() - started) * 1000, 2)
    builder.metrics["tls_handshake_ms"] = duration
    builder.raw_payload["tls"] = {
        "version": version,
        "cipher": cipher[0] if cipher else None,
        "not_after": cert.get("notAfter") if cert else None,
        "issuer": cert.get("issuer") if cert else None,
        "subject": cert.get("subject") if cert else None,
    }
    builder.chain.append(
        {
            "step": "service_edge",
            "status": "success",
            "severity": "info",
            "node_address": builder.node_address,
            "description": f"TLS handshake succeeded for {context.target}:{context.port}",
        }
    )
    builder.evidence.append(
        {
            "type": "tls",
            "message": f"TLS handshake with {context.target}:{context.port} succeeded in {duration} ms",
            "source": "agent",
            "weight": 0.2,
        }
    )
    return builder.finish("success", "info")


def run_http_check(context: CheckContext) -> dict[str, Any]:
    builder = CheckResultBuilder(context=context, check_type="http")
    started = time.monotonic()
    try:
        connection = http.client.HTTPSConnection(
            context.target,
            context.port,
            timeout=context.timeout,
        )
        connection.request("HEAD", context.path, headers={"User-Agent": "nsda-agent/0.1"})
        response = connection.getresponse()
        response.read()
        connection.close()
    except TimeoutError as exc:
        return builder.fail(
            status="timeout",
            error_type="http_timeout",
            error_code=type(exc).__name__,
            description=f"HTTP check for https://{context.target}:{context.port}{context.path} timed out",
            probable_cause="Proxy, service edge, or application service timeout",
            actions=[
                "Compare TCP and TLS timings.",
                "Check proxy authentication and allow rules.",
            ],
            chain_step="application_service",
        )
    except OSError as exc:
        return builder.fail(
            status="failed",
            error_type="http_failed",
            error_code=type(exc).__name__,
            description=f"HTTP check for https://{context.target}:{context.port}{context.path} failed: {exc}",
            probable_cause="Proxy, TLS, route, service edge, or application service issue",
            actions=[
                "Check TLS result for the same endpoint.",
                "Compare HTTP result from another location.",
            ],
            chain_step="application_service",
        )

    duration = round((time.monotonic() - started) * 1000, 2)
    status_code = response.status
    severity = "info" if status_code < 500 else "critical"
    status = "success" if status_code < 500 else "failed"
    builder.metrics["http_time_ms"] = duration
    builder.raw_payload["http"] = {"status_code": status_code, "reason": response.reason}
    builder.chain.append(
        {
            "step": "application_service",
            "status": status,
            "severity": severity,
            "node_address": builder.node_address,
            "description": f"HTTP status {status_code} {response.reason}",
            "error_type": None if status == "success" else "http_5xx",
        }
    )
    builder.evidence.append(
        {
            "type": "http",
            "message": f"HTTP HEAD returned {status_code} {response.reason} in {duration} ms",
            "source": "agent",
            "weight": 0.2 if status == "success" else 0.5,
        }
    )
    if status == "failed":
        builder.error_type = "http_5xx"
        builder.technical_description = f"HTTP application check returned {status_code} {response.reason}"
        builder.probable_cause = "Application service or upstream dependency issue"
        builder.recommended_actions = [
            "Compare the same application check from another agent.",
            "Check external service status and proxy logs.",
        ]
    return builder.finish(status, severity)


def run_https_check_sequence(context: CheckContext) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    dns_result, resolved_ips = run_dns_check(context)
    results.append(dns_result)

    if dns_result["status"] != "success":
        results.extend(_blocked_results(context, ["tcp", "tls", "http"], "dns"))
        return _batch(context, results)

    tcp_result = run_tcp_check(context)
    results.append(tcp_result)
    if tcp_result["status"] != "success":
        results.extend(_blocked_results(context, ["tls", "http"], "tcp"))
        return _batch(context, results, resolved_ips)

    tls_result = run_tls_check(context)
    results.append(tls_result)
    if tls_result["status"] != "success":
        results.extend(_blocked_results(context, ["http"], "tls"))
        return _batch(context, results, resolved_ips)

    results.append(run_http_check(context))
    return _batch(context, results, resolved_ips)


def _blocked_results(context: CheckContext, check_types: list[str], blocked_by: str) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for check_type in check_types:
        builder = CheckResultBuilder(context=context, check_type=check_type)
        builder.technical_description = f"{check_type} check skipped because {blocked_by} did not succeed"
        builder.chain.append(
            {
                "step": "application_service",
                "status": "skipped",
                "severity": "unknown",
                "node_address": builder.node_address,
                "description": builder.technical_description,
                "error_type": f"blocked_by_{blocked_by}",
            }
        )
        blocked.append(builder.finish("skipped", "unknown"))
    return blocked


def _batch(
    context: CheckContext,
    results: list[dict[str, Any]],
    resolved_ips: list[str] | None = None,
) -> dict[str, Any]:
    fingerprint = {
        "agent_id": context.agent_id,
        "location_id": context.location_id,
        "hostname": socket.gethostname(),
        "os": None,
        "public_ip": None,
        "resolver": None,
        "proxy_enabled": False,
        "captured_at": utc_now_iso(),
    }
    return {
        "agent_id": context.agent_id,
        "location_id": context.location_id,
        "network_fingerprint": fingerprint,
        "submitted_at": utc_now_iso(),
        "results": results,
        "metadata": {"target": context.target, "port": context.port, "resolved_ips": resolved_ips or []},
    }


def as_pretty_json(data: dict[str, Any]) -> str:
    return json_dumps(data, indent=2)


def json_dumps(data: dict[str, Any], indent: int | None = None) -> str:
    import json

    return json.dumps(data, indent=indent, sort_keys=False)

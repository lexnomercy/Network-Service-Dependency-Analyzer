from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.checks import CheckContext, run_https_check_sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PACKS_DIR = PROJECT_ROOT / "service-packs"


class ServicePackRunError(RuntimeError):
    pass


def load_service_pack(pack_id: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise ServicePackRunError("PyYAML is required. Run setup.command first.") from exc

    path = SERVICE_PACKS_DIR / pack_id / f"{pack_id}.yaml"
    if not path.exists():
        raise ServicePackRunError(f"Service pack not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    if not isinstance(loaded, dict):
        raise ServicePackRunError(f"Service pack must be a YAML object: {path}")

    return loaded


def run_service_pack(
    *,
    pack_id: str,
    agent_id: str,
    location_id: str,
    timeout: float,
) -> dict[str, Any]:
    pack = load_service_pack(pack_id)
    results: list[dict[str, Any]] = []
    endpoint_groups = pack.get("endpoint_groups", [])

    if not isinstance(endpoint_groups, list):
        raise ServicePackRunError("service pack endpoint_groups must be a list")

    for group in endpoint_groups:
        if not isinstance(group, dict):
            continue

        protocol = str(group.get("protocol", "")).lower()
        checks = {str(check) for check in group.get("checks", [])}
        if protocol != "https" or not {"dns", "tcp", "tls", "http"}.intersection(checks):
            continue

        endpoints = group.get("endpoints", [])
        if not isinstance(endpoints, list):
            continue

        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue
            hostname = endpoint.get("hostname")
            if not hostname:
                continue

            context = CheckContext(
                agent_id=agent_id,
                location_id=location_id,
                service_id=str(group.get("service", "unknown_service")),
                endpoint_group_id=str(group.get("id")) if group.get("id") else None,
                target=str(hostname),
                port=int(endpoint.get("port", 443)),
                path=str(endpoint.get("path", "/")),
                timeout=timeout,
            )
            batch = run_https_check_sequence(context)
            results.extend(batch["results"])

    return {
        "agent_id": agent_id,
        "location_id": location_id,
        "results": results,
    }

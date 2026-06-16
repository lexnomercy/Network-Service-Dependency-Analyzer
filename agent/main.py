from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from agent.checks import CheckContext, run_https_check_sequence
from agent.service_pack_runner import run_service_pack


@dataclass(frozen=True)
class NetworkFingerprint:
    agent_id: str
    location_id: str
    hostname: str
    os: str
    public_ip: str | None
    resolver: str | None
    proxy_enabled: bool
    captured_at: str


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def capture_network_fingerprint() -> NetworkFingerprint:
    return NetworkFingerprint(
        agent_id=os.getenv("AGENT_ID", "local-agent"),
        location_id=os.getenv("AGENT_LOCATION_ID", "local"),
        hostname=socket.gethostname(),
        os=f"{platform.system()} {platform.release()}",
        public_ip=os.getenv("AGENT_PUBLIC_IP"),
        resolver=os.getenv("AGENT_RESOLVER"),
        proxy_enabled=_env_bool("AGENT_PROXY_ENABLED"),
        captured_at=datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Network Service Dependency Analyzer agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("fingerprint", help="Print local network fingerprint")

    check_parser = subparsers.add_parser("check", help="Run HTTPS checks and print ingestion batch JSON")
    check_parser.add_argument("--target", required=True, help="Hostname to check")
    check_parser.add_argument("--port", type=int, default=443, help="Target port")
    check_parser.add_argument("--path", default="/", help="HTTP path")
    check_parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds")
    check_parser.add_argument("--service", default="zoom_meeting_signaling", help="Service id")
    check_parser.add_argument(
        "--endpoint-group",
        default="zoom_meeting_signaling_https",
        help="Endpoint group id",
    )
    check_parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit the generated batch to BACKEND_URL/api/v1/check-results/bulk",
    )

    pack_parser = subparsers.add_parser(
        "run-service-pack",
        help="Run checks declared in service-packs/<pack>/<pack>.yaml",
    )
    pack_parser.add_argument("--pack", default="zoom", help="Service pack id")
    pack_parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds")
    pack_parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit the generated batch to BACKEND_URL/api/v1/check-results/bulk",
    )
    args = parser.parse_args()

    if args.command == "fingerprint":
        print(json.dumps(asdict(capture_network_fingerprint()), indent=2))
        return

    if args.command == "check":
        fingerprint = capture_network_fingerprint()
        context = CheckContext(
            agent_id=fingerprint.agent_id,
            location_id=fingerprint.location_id,
            service_id=args.service,
            endpoint_group_id=args.endpoint_group,
            target=args.target,
            port=args.port,
            path=args.path,
            timeout=args.timeout,
        )
        batch = run_https_check_sequence(context)
        batch["network_fingerprint"] = asdict(fingerprint)
        payload = json.dumps(batch, indent=2)
        print(payload)

        if args.submit:
            submit_batch(batch)
        return

    if args.command == "run-service-pack":
        fingerprint = capture_network_fingerprint()
        batch = run_service_pack(
            pack_id=args.pack,
            agent_id=fingerprint.agent_id,
            location_id=fingerprint.location_id,
            timeout=args.timeout,
        )
        batch["network_fingerprint"] = asdict(fingerprint)
        batch["submitted_at"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(batch, indent=2)
        print(payload)

        if args.submit:
            submit_batch(batch)


def submit_batch(batch: dict) -> None:
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    url = f"{backend_url}/api/v1/check-results/bulk"
    body = json.dumps(batch).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to submit check batch to {url}: {exc}") from exc


if __name__ == "__main__":
    main()

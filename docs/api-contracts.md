# API Contracts

## Health

```http
GET /health
```

## Service Packs

```http
GET /api/v1/service-packs
GET /api/v1/service-packs/{service_pack_id}
```

## Agents

```http
POST /api/v1/agents/register
POST /api/v1/agents/{agent_id}/heartbeat
```

Agent registration:

```json
{
  "id": "office-msk-01",
  "name": "Office MSK Agent 01",
  "location_id": "office-msk",
  "version": "0.1.0",
  "hostname": "monitor-01"
}
```

Heartbeat:

```json
{
  "status": "online",
  "version": "0.1.0",
  "network_fingerprint": {
    "agent_id": "office-msk-01",
    "location_id": "office-msk",
    "hostname": "monitor-01",
    "public_ip": "203.0.113.10",
    "asn": 12389,
    "provider": "Example ISP",
    "resolver": "8.8.8.8",
    "proxy_enabled": true
  }
}
```

## Check Result Ingestion

```http
POST /api/v1/check-results/bulk
```

The MVP agent can generate this payload with:

```bash
python3 -m agent.main check --target zoom.us --port 443 --path /
```

Example:

```json
{
  "agent_id": "office-msk-01",
  "location_id": "office-msk",
  "network_fingerprint": {
    "agent_id": "office-msk-01",
    "location_id": "office-msk",
    "provider": "Example ISP",
    "resolver": "8.8.8.8",
    "proxy_enabled": true
  },
  "results": [
    {
      "agent_id": "office-msk-01",
      "location_id": "office-msk",
      "service_id": "zoom_meeting_signaling",
      "endpoint_group_id": "zoom_meeting_signaling_https",
      "check_type": "tcp",
      "status": "timeout",
      "severity": "critical",
      "started_at": "2026-06-16T09:00:00Z",
      "finished_at": "2026-06-16T09:00:03Z",
      "duration_ms": 3000,
      "error_type": "tcp_timeout",
      "technical_description": "TCP connect to zoom.us:443 timed out after 3000 ms",
      "probable_cause": "Firewall, proxy, NAT, or routing issue",
      "recommended_actions": [
        "Check outbound TCP/443 firewall policy",
        "Compare with an agent outside the corporate network"
      ],
      "chain": [
        {
          "step": "dns",
          "status": "success",
          "severity": "info"
        },
        {
          "step": "proxy_firewall_nat",
          "status": "timeout",
          "severity": "critical",
          "error_type": "tcp_timeout"
        }
      ],
      "evidence": [
        {
          "type": "check_result",
          "message": "DNS succeeded, TCP timed out",
          "source": "agent",
          "weight": 0.5
        }
      ]
    }
  ]
}
```

## Status Overview

```http
GET /api/v1/status/overview
```

Returns current in-memory status:

- service pack count.
- agent count.
- open incident count.
- latest check results.
- open incidents.
- diagnostic conclusions.

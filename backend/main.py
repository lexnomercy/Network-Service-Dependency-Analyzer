from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.repository import repository
from backend.schemas import (
    Agent,
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    CheckResultBatch,
    StatusOverview,
)
from backend.service_packs import ServicePackLoadError, list_service_packs, load_service_pack


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

app = FastAPI(
    title="Network Service Dependency Analyzer API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "network-service-dependency-analyzer"}


@app.get("/api/v1/service-packs")
def get_service_packs() -> dict[str, list[dict[str, str]]]:
    return {"service_packs": list_service_packs()}


@app.get("/api/v1/service-packs/{service_pack_id}")
def get_service_pack(service_pack_id: str) -> dict:
    try:
        return load_service_pack(service_pack_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="service pack not found") from exc
    except ServicePackLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/agents/register", response_model=Agent)
def register_agent(request: AgentRegistrationRequest) -> Agent:
    return repository.register_agent(request)


@app.post("/api/v1/agents/{agent_id}/heartbeat", response_model=Agent)
def agent_heartbeat(agent_id: str, request: AgentHeartbeatRequest) -> Agent:
    return repository.heartbeat(agent_id, request)


@app.post("/api/v1/check-results/bulk")
def ingest_check_results(batch: CheckResultBatch) -> dict[str, int]:
    return repository.ingest_check_batch(batch)


@app.get("/api/v1/status/overview", response_model=StatusOverview)
def status_overview() -> StatusOverview:
    return repository.status_overview()


if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/")
def frontend_index() -> FileResponse:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="frontend build not found")
    return FileResponse(FRONTEND_INDEX)


@app.head("/")
def frontend_index_head() -> Response:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="frontend build not found")
    return Response(status_code=200)


@app.get("/{path:path}")
def frontend_spa_fallback(path: str) -> FileResponse:
    if path.startswith(("api/", "health")):
        raise HTTPException(status_code=404, detail="not found")
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="frontend build not found")
    return FileResponse(FRONTEND_INDEX)

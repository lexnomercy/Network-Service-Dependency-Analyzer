from __future__ import annotations

from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PACKS_DIR = PROJECT_ROOT / "service-packs"


class ServicePackLoadError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise ServicePackLoadError(
            "PyYAML is required to load service packs. Install backend requirements first."
        ) from exc

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    if not isinstance(loaded, dict):
        raise ServicePackLoadError(f"Service pack {path} must contain a YAML object.")

    return loaded


def list_service_packs() -> list[dict[str, str]]:
    packs: list[dict[str, str]] = []
    if not SERVICE_PACKS_DIR.exists():
        return packs

    for path in sorted(SERVICE_PACKS_DIR.glob("*/**/*.yaml")):
        if path.name != f"{path.parent.name}.yaml":
            continue
        pack_id = path.parent.name
        try:
            loaded = _load_yaml(path)
            meta = loaded.get("service_pack", {})
            packs.append(
                {
                    "id": str(meta.get("id", pack_id)),
                    "name": str(meta.get("name", pack_id)),
                    "version": str(meta.get("version", "unknown")),
                }
            )
        except ServicePackLoadError:
            packs.append({"id": pack_id, "name": pack_id, "version": "unavailable"})

    return packs


def load_service_pack(service_pack_id: str) -> dict[str, Any]:
    path = SERVICE_PACKS_DIR / service_pack_id / f"{service_pack_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(path)
    return _load_yaml(path)

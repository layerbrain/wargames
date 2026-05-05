from __future__ import annotations

from pathlib import Path


def resolve_mission_catalog_path(path: str | Path) -> Path:
    catalog_path = Path(path)
    if catalog_path.exists() or catalog_path != Path("scenarios") and catalog_path.is_absolute():
        return catalog_path

    relative = catalog_path
    if catalog_path.parts[:1] == ("scenarios",):
        relative = Path(*catalog_path.parts[1:])

    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / catalog_path, parent / "scenarios" / relative):
            if candidate.exists():
                return candidate
    return catalog_path

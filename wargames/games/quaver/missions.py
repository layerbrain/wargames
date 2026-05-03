from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

QUAVER_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True, kw_only=True)
class QuaverMissionSpec(MissionSpec):
    map_id: int
    mapset_id: int | None
    map_path: str
    archive_path: str | None
    song_title: str
    artist: str
    difficulty_name: str
    mode: str
    key_count: int
    audio_file: str | None
    hit_objects: int
    long_notes: int
    mines: int
    total_judgements: int
    song_length_ms: int
    notes_per_second: float

    def __post_init__(self) -> None:
        if self.key_count <= 0:
            raise ValueError(f"Quaver mission must declare a key count: {self.id}")
        if self.total_judgements <= 0:
            raise ValueError(f"Quaver mission must include scored judgements: {self.id}")


@dataclass(frozen=True)
class _Chart:
    map_id: int
    mapset_id: int | None
    map_path: Path | str
    archive_path: Path | None
    song_title: str
    artist: str
    difficulty_name: str
    mode: str
    key_count: int
    audio_file: str | None
    hit_objects: int
    long_notes: int
    mines: int
    total_judgements: int
    song_length_ms: int
    notes_per_second: float
    root: Path | None


def discover(
    root: str | Path | None = None,
    *,
    default_maps_dir: str | Path | None = None,
    songs_dir: str | Path | None = None,
) -> tuple[QuaverMissionSpec, ...]:
    source_root = _source_root(Path(root).expanduser() if root else None)
    charts = _discover_charts(
        source_root,
        default_maps_dir=Path(default_maps_dir).expanduser() if default_maps_dir else None,
        songs_dir=Path(songs_dir).expanduser() if songs_dir else None,
    )
    missions = [_mission_for_chart(chart) for chart in charts]
    return tuple(sorted(missions, key=lambda mission: (mission.difficulty, mission.id)))


def extract_mission_catalog(
    root: str | Path | None,
    output_dir: str | Path,
    *,
    default_maps_dir: str | Path | None = None,
    songs_dir: str | Path | None = None,
) -> tuple[Path, ...]:
    missions = discover(root, default_maps_dir=default_maps_dir, songs_dir=songs_dir)
    if not missions:
        return ()

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*/*.json"):
        stale.unlink()

    written: list[Path] = []
    for mission in missions:
        path = out / mission.difficulty / f"{mission.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_mission_payload(mission), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[QuaverMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _discover_charts(
    source_root: Path | None,
    *,
    default_maps_dir: Path | None,
    songs_dir: Path | None,
) -> tuple[_Chart, ...]:
    charts: dict[tuple[int, str], _Chart] = {}
    for archive in _default_map_archives(source_root, default_maps_dir):
        with zipfile.ZipFile(archive) as handle:
            for name in sorted(handle.namelist()):
                if name.endswith(".qua"):
                    text = handle.read(name).decode("utf-8-sig")
                    chart = _chart_from_text(text, name, archive, source_root)
                    charts.setdefault(_chart_key(chart), chart)
    for path in _qua_files(source_root, songs_dir):
        chart = _chart_from_text(path.read_text(encoding="utf-8-sig"), path, None, source_root)
        charts.setdefault(_chart_key(chart), chart)
    return tuple(sorted(charts.values(), key=lambda chart: (chart.artist, chart.song_title, chart.map_id)))


def _chart_from_text(
    text: str,
    path: Path | str,
    archive: Path | None,
    source_root: Path | None,
) -> _Chart:
    data = yaml.safe_load(text) or {}
    hit_objects = list(data.get("HitObjects") or [])
    long_notes = sum(1 for obj in hit_objects if _is_long_note(obj) and not _is_mine(obj))
    mines = sum(1 for obj in hit_objects if _is_mine(obj))
    regular_notes = sum(1 for obj in hit_objects if not _is_long_note(obj) and not _is_mine(obj))
    total_judgements = regular_notes + long_notes * 2
    song_length_ms = _song_length_ms(hit_objects)
    notes_per_second = (
        (regular_notes + long_notes) / (song_length_ms / 1000.0) if song_length_ms > 0 else 0.0
    )
    mode = str(data.get("Mode", "Keys4"))
    return _Chart(
        map_id=int(data.get("MapId", -1) or -1),
        mapset_id=_optional_int(data.get("MapSetId")),
        map_path=path,
        archive_path=archive,
        song_title=str(data.get("Title", "Untitled")),
        artist=str(data.get("Artist", "Unknown Artist")),
        difficulty_name=str(data.get("DifficultyName", "Unknown")),
        mode=mode,
        key_count=_key_count(mode),
        audio_file=None if data.get("AudioFile") is None else str(data["AudioFile"]),
        hit_objects=len(hit_objects),
        long_notes=long_notes,
        mines=mines,
        total_judgements=total_judgements,
        song_length_ms=song_length_ms,
        notes_per_second=notes_per_second,
        root=source_root,
    )


def _mission_for_chart(chart: _Chart) -> QuaverMissionSpec:
    difficulty = _difficulty_for_chart(chart)
    slug = _slug(f"{chart.artist} {chart.song_title} {chart.difficulty_name}")
    stable_id = str(chart.map_id) if chart.map_id >= 0 else _stable_path_hash(chart.map_path)
    return QuaverMissionSpec(
        id=f"quaver.chart.{slug}.{stable_id}.{difficulty}",
        title=f"{chart.artist} - {chart.song_title} [{chart.difficulty_name}]",
        game="quaver",
        source="builtin",
        difficulty=difficulty,
        native_difficulty=chart.difficulty_name,
        tags=("rhythm", "timing", chart.mode.lower(), f"{chart.key_count}k"),
        time_limit_ticks=_time_limit_ticks(chart.song_length_ms),
        estimated_duration_ticks=max(1, int(chart.song_length_ms / 1000 * 60)),
        map_id=chart.map_id,
        mapset_id=chart.mapset_id,
        map_path=_map_path_text(chart),
        archive_path=_path_text(chart.archive_path, chart.root) if chart.archive_path else None,
        song_title=chart.song_title,
        artist=chart.artist,
        difficulty_name=chart.difficulty_name,
        mode=chart.mode,
        key_count=chart.key_count,
        audio_file=chart.audio_file,
        hit_objects=chart.hit_objects,
        long_notes=chart.long_notes,
        mines=chart.mines,
        total_judgements=chart.total_judgements,
        song_length_ms=chart.song_length_ms,
        notes_per_second=round(chart.notes_per_second, 3),
    )


def _mission_payload(mission: QuaverMissionSpec) -> dict[str, object]:
    return {
        "archive_path": mission.archive_path,
        "artist": mission.artist,
        "audio_file": mission.audio_file,
        "difficulty": mission.difficulty,
        "difficulty_name": mission.difficulty_name,
        "estimated_duration_ticks": mission.estimated_duration_ticks,
        "game": mission.game,
        "hit_objects": mission.hit_objects,
        "id": mission.id,
        "key_count": mission.key_count,
        "long_notes": mission.long_notes,
        "map_id": mission.map_id,
        "map_path": mission.map_path,
        "mapset_id": mission.mapset_id,
        "mines": mission.mines,
        "mode": mission.mode,
        "native_difficulty": mission.native_difficulty,
        "notes_per_second": mission.notes_per_second,
        "song_length_ms": mission.song_length_ms,
        "song_title": mission.song_title,
        "source": mission.source,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "title": mission.title,
        "total_judgements": mission.total_judgements,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> QuaverMissionSpec:
    return QuaverMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data.get("game", "quaver")),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("difficulty_name", "normal"))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
        estimated_duration_ticks=int(data.get("estimated_duration_ticks", 0)),
        map_id=int(data["map_id"]),
        mapset_id=_optional_int(data.get("mapset_id")),
        map_path=str(data["map_path"]),
        archive_path=None if data.get("archive_path") is None else str(data["archive_path"]),
        song_title=str(data["song_title"]),
        artist=str(data["artist"]),
        difficulty_name=str(data["difficulty_name"]),
        mode=str(data["mode"]),
        key_count=int(data["key_count"]),
        audio_file=None if data.get("audio_file") is None else str(data["audio_file"]),
        hit_objects=int(data["hit_objects"]),
        long_notes=int(data["long_notes"]),
        mines=int(data.get("mines", 0)),
        total_judgements=int(data["total_judgements"]),
        song_length_ms=int(data["song_length_ms"]),
        notes_per_second=float(data.get("notes_per_second", 0.0)),
    )


def _source_root(root: Path | None) -> Path | None:
    if root is None:
        return None
    if (root / "Quaver" / "Quaver.csproj").exists():
        return root
    if (root / "Quaver.csproj").exists() and root.name == "Quaver":
        return root.parent
    return root


def _qua_files(source_root: Path | None, songs_dir: Path | None) -> Iterable[Path]:
    candidates = [
        songs_dir,
        source_root / "Quaver" / "bin" / "Release" / "net6.0" / "Songs" if source_root else None,
        source_root / "Quaver" / "bin" / "Debug" / "net6.0" / "Songs" if source_root else None,
        source_root / "Songs" if source_root else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            yield from sorted(candidate.rglob("*.qua"))


def _default_map_archives(source_root: Path | None, default_maps_dir: Path | None) -> Iterable[Path]:
    candidates = [
        default_maps_dir,
        source_root / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps" if source_root else None,
        _cache_default_maps_dir(),
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate and candidate.exists():
            for path in sorted(candidate.glob("*.qp")):
                if path not in seen and zipfile.is_zipfile(path):
                    seen.add(path)
                    yield path


def _difficulty_for_chart(chart: _Chart) -> MissionDifficulty:
    if chart.notes_per_second <= 2.5:
        return "easy"
    if chart.notes_per_second <= 5.5:
        return "normal"
    return "hard"


def _time_limit_ticks(song_length_ms: int) -> int:
    return max(1, int(((song_length_ms / 1000.0) + 20.0) * 60))


def _song_length_ms(hit_objects: list[object]) -> int:
    latest = 0
    for obj in hit_objects:
        if not isinstance(obj, Mapping):
            continue
        start = int(obj.get("StartTime", 0) or 0)
        end = int(obj.get("EndTime", start) or start)
        latest = max(latest, start, end)
    return max(latest, 0)


def _key_count(mode: str) -> int:
    match = re.search(r"(\d+)", mode)
    return int(match.group(1)) if match else 4


def _chart_key(chart: _Chart) -> tuple[int, str]:
    if chart.map_id >= 0:
        return chart.map_id, ""
    return chart.map_id, str(chart.map_path)


def _is_long_note(obj: object) -> bool:
    return isinstance(obj, Mapping) and obj.get("EndTime") is not None


def _is_mine(obj: object) -> bool:
    return isinstance(obj, Mapping) and str(obj.get("Type", "")).lower() == "mine"


def _map_path_text(chart: _Chart) -> str:
    if chart.archive_path is None:
        return _path_text(Path(chart.map_path), chart.root)
    return f"{_path_text(chart.archive_path, chart.root)}:{chart.map_path}"


def _path_text(path: Path | None, root: Path | None) -> str | None:
    if path is None:
        return None
    if root is not None:
        try:
            return str(path.relative_to(root))
        except ValueError:
            pass
    return str(path)


def _stable_path_hash(path: Path | str) -> str:
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "chart"


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _cache_default_maps_dir() -> Path | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return (
        Path(cache_dir)
        / "games"
        / "quaver"
        / "quaver"
        / "Quaver.Resources"
        / "Quaver.Resources"
        / "DefaultMaps"
    )

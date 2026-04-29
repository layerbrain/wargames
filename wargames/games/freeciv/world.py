from __future__ import annotations

import bz2
import csv
import gzip
import lzma
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wargames.games.freeciv.missions import FreeCivMissionSpec


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class GameState:
    turn: int
    year: int | None
    server_state: str
    ruleset: str
    max_turns: int


@dataclass(frozen=True)
class UnitState:
    id: int
    type: str
    x: int | None = None
    y: int | None = None
    hp: int | None = None
    moves: int | None = None
    activity: str | None = None
    done_moving: bool | None = None


@dataclass(frozen=True)
class CityState:
    id: int
    name: str
    x: int | None = None
    y: int | None = None
    size: int | None = None


@dataclass(frozen=True)
class PlayerState:
    id: int
    name: str
    username: str
    nation: str
    government: str
    is_alive: bool
    ai: bool
    gold: int
    tax_rate: int
    science_rate: int
    luxury_rate: int
    city_count: int
    unit_count: int
    known_tiles: int
    units: tuple[UnitState, ...]
    cities: tuple[CityState, ...]


@dataclass(frozen=True)
class FreeCivWorld:
    tick: int
    mission: MissionState
    game: GameState
    players: tuple[PlayerState, ...]
    us: PlayerState | None
    enemies: tuple[PlayerState, ...]


def world_from_save(
    path: str | Path, mission: FreeCivMissionSpec, *, player_name: str | None = None
) -> FreeCivWorld:
    text = _read_save(path)
    return world_from_save_text(text, mission, player_name=player_name)


def world_from_save_text(
    text: str, mission: FreeCivMissionSpec, *, player_name: str | None = None
) -> FreeCivWorld:
    save = parse_freeciv_save(text)
    game_raw = save.get("game", {})
    turn = _int(game_raw.get("turn"), default=0)
    game = GameState(
        turn=turn,
        year=_optional_int(game_raw.get("year")),
        server_state=str(game_raw.get("server_state", "")),
        ruleset=str(game_raw.get("rulesetdir", mission.ruleset)),
        max_turns=mission.time_limit_ticks,
    )
    players = tuple(
        _player(index, section)
        for index, section in _player_sections(save)
        if section.get("name") not in {None, ""}
    )
    expected_name = player_name or mission.player_name
    us = _find_player(players, expected_name)
    enemies = tuple(player for player in players if player is not us and player.is_alive)
    failed = us is None or not us.is_alive
    finished = bool(us and enemies and all(not player.is_alive for player in enemies))
    return FreeCivWorld(
        tick=turn,
        mission=MissionState(finished=finished, failed=failed),
        game=game,
        players=players,
        us=us,
        enemies=enemies,
    )


def parse_freeciv_save(text: str) -> dict[str, dict[str, object]]:
    sections: dict[str, dict[str, object]] = {}
    current: dict[str, object] | None = None
    lines = iter(text.splitlines())
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
            continue
        if current is None or "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        value = raw_value.strip()
        if value.startswith("{"):
            current[key] = _parse_table(value, lines)
        else:
            current[key] = _parse_value(value)
    return sections


def _parse_table(first_value: str, lines: object) -> tuple[dict[str, object], ...]:
    table_lines: list[str] = []
    value = first_value[1:].strip()
    if value:
        table_lines.append(value)
    for raw_line in lines:  # type: ignore[assignment]
        line = str(raw_line).strip()
        if line == "}":
            break
        if line.endswith("}"):
            table_lines.append(line[:-1].strip())
            break
        table_lines.append(line)
    rows: list[list[str]] = []
    for line in table_lines:
        if not line:
            continue
        rows.extend(csv.reader([line]))
    if not rows:
        return ()
    headers = [str(item) for item in rows[0]]
    return tuple(
        {header: _parse_value(value) for header, value in zip(headers, row, strict=False)}
        for row in rows[1:]
    )


def _parse_value(value: str) -> object:
    stripped = value.strip().rstrip(",")
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        return stripped[1:-1].replace('\\"', '"')
    upper = stripped.upper()
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _player_sections(save: Mapping[str, Mapping[str, object]]) -> tuple[tuple[int, Mapping[str, object]], ...]:
    found: list[tuple[int, Mapping[str, object]]] = []
    for section, values in save.items():
        if not section.startswith("player"):
            continue
        suffix = section.removeprefix("player")
        if not suffix.isdigit():
            continue
        found.append((int(suffix), values))
    return tuple(sorted(found, key=lambda item: item[0]))


def _player(id: int, section: Mapping[str, object]) -> PlayerState:
    units = tuple(_unit(item) for item in _table(section.get("u")))
    cities = tuple(_city(item) for item in _table(section.get("c")))
    flags = str(section.get("flags", ""))
    return PlayerState(
        id=id,
        name=str(section.get("name", "")),
        username=str(section.get("username", "")),
        nation=str(section.get("nation", "")),
        government=str(section.get("government_name", "")),
        is_alive=_bool(section.get("is_alive"), default=True),
        ai="ai" in flags.casefold() or str(section.get("username", "")).casefold() == "unassigned",
        gold=_int(section.get("gold"), default=0),
        tax_rate=_int(section.get("rates.tax"), default=0),
        science_rate=_int(section.get("rates.science"), default=0),
        luxury_rate=_int(section.get("rates.luxury"), default=0),
        city_count=_int(section.get("ncities"), default=len(cities)),
        unit_count=_int(section.get("nunits"), default=len(units)),
        known_tiles=_known_tiles(section),
        units=units,
        cities=cities,
    )


def _unit(row: Mapping[str, object]) -> UnitState:
    return UnitState(
        id=_int(row.get("id"), default=0),
        type=str(row.get("type_by_name", row.get("type", ""))),
        x=_optional_int(row.get("x")),
        y=_optional_int(row.get("y")),
        hp=_optional_int(row.get("hp")),
        moves=_optional_int(row.get("moves")),
        activity=_optional_str(row.get("activity")),
        done_moving=_optional_bool(row.get("done_moving")),
    )


def _city(row: Mapping[str, object]) -> CityState:
    return CityState(
        id=_int(row.get("id"), default=0),
        name=str(row.get("name", "")),
        x=_optional_int(row.get("x")),
        y=_optional_int(row.get("y")),
        size=_optional_int(row.get("size")),
    )


def _find_player(players: tuple[PlayerState, ...], player_name: str) -> PlayerState | None:
    for player in players:
        if player.username == player_name:
            return player
    for player in players:
        if player.name == player_name:
            return player
    return players[0] if players else None


def _known_tiles(section: Mapping[str, object]) -> int:
    total = 0
    for key, value in section.items():
        if not key.startswith("map_t"):
            continue
        if isinstance(value, str):
            total += sum(1 for char in value if char != "u")
    return total


def _read_save(path: str | Path) -> str:
    file = Path(path)
    if file.suffix == ".xz":
        return lzma.decompress(file.read_bytes()).decode("utf-8", errors="replace")
    if file.suffix == ".gz":
        return gzip.decompress(file.read_bytes()).decode("utf-8", errors="replace")
    if file.suffix == ".bz2":
        return bz2.decompress(file.read_bytes()).decode("utf-8", errors="replace")
    return file.read_text(encoding="utf-8", errors="replace")


def _table(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.upper() == "TRUE"
    return bool(value)


def _int(value: object, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_bool(value: object) -> bool | None:
    return None if value is None else _bool(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else _int(value, default=0)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)

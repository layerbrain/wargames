from __future__ import annotations

from wargames.core.errors import MissionNotFound
from wargames.core.missions.spec import MissionSpec


class MissionRegistry:
    def __init__(self, missions: tuple[MissionSpec, ...] = ()) -> None:
        self._missions: dict[str, MissionSpec] = {}
        for mission in missions:
            self.add(mission)

    def add(self, mission: MissionSpec) -> None:
        if mission.id in self._missions:
            raise ValueError(f"duplicate mission id: {mission.id}")
        self._missions[mission.id] = mission

    def get(self, id: str) -> MissionSpec:
        try:
            return self._missions[id]
        except KeyError as exc:
            raise MissionNotFound(id) from exc

    def all(self) -> tuple[MissionSpec, ...]:
        return tuple(self._missions.values())

    def __contains__(self, id: str) -> bool:
        return id in self._missions

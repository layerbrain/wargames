from __future__ import annotations

from dataclasses import dataclass

from wargames.core.missions.rubric import RewardBreakdown, Rubric, RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


@dataclass(frozen=True)
class RewardProfile:
    id: str
    game: str
    rubric: Rubric
    per_step_entries: tuple[str, ...]
    terminal_entries: tuple[str, ...]
    step_reward_min: float | None = None
    step_reward_max: float | None = None
    terminal_reward_weight: float = 1.0
    dense_reward_weight: float = 1.0
    train_only: bool = False
    description: str = ""

    async def score_step(self, prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> RewardBreakdown:
        breakdown = await Rubric(self._entries(self.per_step_entries)).score(prev, curr)
        entries = {key: value * self.dense_reward_weight for key, value in breakdown.entries.items()}
        total = sum(entries.values())
        if self.step_reward_min is not None:
            total = max(self.step_reward_min, total)
        if self.step_reward_max is not None:
            total = min(self.step_reward_max, total)
        return RewardBreakdown(total=total, entries=entries)

    async def score_terminal(self, prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> RewardBreakdown:
        breakdown = await Rubric(self._entries(self.terminal_entries)).score(prev, curr)
        entries = {key: value * self.terminal_reward_weight for key, value in breakdown.entries.items()}
        return RewardBreakdown(total=sum(entries.values()), entries=entries)

    def _entries(self, ids: tuple[str, ...]) -> tuple[RubricEntry, ...]:
        wanted = set(ids)
        entries = tuple(entry for entry in self.rubric.entries if entry.id in wanted)
        missing = wanted - {entry.id for entry in entries}
        if missing:
            raise ValueError(f"profile {self.id} references missing rubric entries: {', '.join(sorted(missing))}")
        return entries


class ProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[tuple[str, str], RewardProfile] = {}

    def register(self, profile: RewardProfile, *, replace: bool = False) -> None:
        key = (profile.game, profile.id)
        if key in self._profiles and not replace:
            raise ValueError(f"duplicate reward profile: {profile.game}/{profile.id}")
        self._profiles[key] = profile

    def get(self, game: str, id: str) -> RewardProfile:
        try:
            return self._profiles[(game, id)]
        except KeyError as exc:
            raise KeyError(f"unknown reward profile: {game}/{id}") from exc

    def list(self, game: str | None = None) -> list[RewardProfile]:
        profiles = self._profiles.values()
        if game is not None:
            profiles = [profile for profile in profiles if profile.game == game]
        return sorted(profiles, key=lambda profile: (profile.game, profile.id))


profile_registry = ProfileRegistry()

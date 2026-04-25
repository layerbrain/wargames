from __future__ import annotations

from wargames.core.missions.rubric import RewardBreakdown
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.evaluation.profile import RewardProfile

ZERO_BREAKDOWN = RewardBreakdown(total=0.0, entries={})


class RewardEvaluator:
    def __init__(self, profile: RewardProfile) -> None:
        self.profile = profile

    async def score_step(
        self,
        prev: HiddenStateSnapshot | None,
        curr: HiddenStateSnapshot | None,
    ) -> RewardBreakdown:
        if prev is None or curr is None:
            return ZERO_BREAKDOWN
        return await self.profile.score_step(prev, curr)

    async def score_terminal(
        self,
        prev: HiddenStateSnapshot | None,
        curr: HiddenStateSnapshot | None,
    ) -> RewardBreakdown:
        if curr is None:
            return ZERO_BREAKDOWN
        return await self.profile.score_terminal(prev or curr, curr)

from __future__ import annotations

from wargames.core.missions.catalog import MissionSuite

SUITES: tuple[MissionSuite, ...] = (
    MissionSuite(
        id="redalert.campaign.easy",
        title="Red Alert Campaign - Easy",
        game="redalert",
        split="curriculum",
        missions=(),
        difficulty_filter=("easy",),
    ),
    MissionSuite(
        id="redalert.campaign.normal",
        title="Red Alert Campaign - Normal",
        game="redalert",
        split="train",
        missions=(),
        difficulty_filter=("normal",),
    ),
    MissionSuite(
        id="redalert.campaign.hard",
        title="Red Alert Campaign - Hard",
        game="redalert",
        split="eval",
        missions=(),
        difficulty_filter=("hard",),
    ),
)

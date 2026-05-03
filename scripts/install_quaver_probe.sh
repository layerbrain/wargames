#!/usr/bin/env bash
set -euo pipefail

source_root="${1:?usage: install_quaver_probe.sh /path/to/quaver}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$source_root/Quaver/Quaver.csproj" || ! -f "$source_root/Quaver.Shared/Quaver.Shared.csproj" ]]; then
  echo "Quaver source checkout not found: $source_root" >&2
  exit 1
fi

mkdir -p "$source_root/Quaver.Shared/Wargames"
cp "$repo_root/wargames/games/quaver/quaver/WargamesStateExporter.cs" \
  "$source_root/Quaver.Shared/Wargames/WargamesStateExporter.cs"

python3 - "$source_root" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def require(path: Path, needle: str) -> None:
    if needle not in read(path):
        raise SystemExit(f"{path} did not contain expected source text: {needle[:80]}")


def insert_after(text: str, anchor: str, block: str) -> str:
    if block.strip() in text:
        return text
    if anchor not in text:
        raise SystemExit(f"missing patch anchor: {anchor[:80]}")
    return text.replace(anchor, anchor + block, 1)


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"missing patch anchor: {old[:80]}")
    return text.replace(old, new, 1)


def replace_optional(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old in text:
        return text.replace(old, new, 1)
    return text


steam = root / "Quaver.Shared" / "Online" / "SteamManager.cs"
text = read(steam)
if 'Environment.GetEnvironmentVariable("WARGAMES_QUAVER_DISABLE_STEAM")' not in text:
    old_probe = '''            if (Environment.GetEnvironmentVariable("QUAVER_DISABLE_STEAM") == "1")
            {
                IsInitialized = false;
                UserAvatars = new ConcurrentDictionary<ulong, Texture2D>();
                UserAvatarsLarge = new ConcurrentDictionary<ulong, Texture2D>();
                Logger.Important("Steam initialization skipped for headless runtime probe.", LogType.Runtime);
                return;
            }
'''
    new_block = '''            if (Environment.GetEnvironmentVariable("WARGAMES_QUAVER_DISABLE_STEAM") == "1")
            {
                IsInitialized = false;
                UserAvatars = new ConcurrentDictionary<ulong, Texture2D>();
                UserAvatarsLarge = new ConcurrentDictionary<ulong, Texture2D>();
                Logger.Important("Steam initialization skipped for WarGames runtime.", LogType.Runtime);
                return;
            }
'''
    if old_probe in text:
        text = text.replace(old_probe, new_block, 1)
    else:
        text = insert_after(text, "            }\n", new_block)
text = insert_after(
    text,
    "        public static bool SetRichPresence(string pchKey, string pchValue)\n        {\n",
    "            if (!IsInitialized)\n                return false;\n\n",
)
text = insert_after(
    text,
    "        public static void ClearRichPresence()\n        {\n",
    "            if (!IsInitialized)\n                return;\n\n",
)
write(steam, text)


initialization = root / "Quaver.Shared" / "Screens" / "Initialization" / "InitializationScreen.cs"
text = read(initialization)
if "using System.Collections.Generic;" not in text:
    text = text.replace("using System;\n", "using System;\nusing System.Collections.Generic;\n", 1)
if "using Quaver.Shared.Screens.Loading;" not in text:
    text = text.replace(
        "using Quaver.Shared.Screens.Main;\n",
        "using Quaver.Shared.Screens.Loading;\nusing Quaver.Shared.Screens.Main;\n",
        1,
    )
text = replace_once(
    text,
    "            SteamManager.SendAvatarRetrievalRequest(SteamUser.GetSteamID().m_SteamID);\n",
    "            if (SteamManager.IsInitialized)\n                SteamManager.SendAvatarRetrievalRequest(SteamUser.GetSteamID().m_SteamID);\n",
)
if 'Environment.GetEnvironmentVariable("WARGAMES_QUAVER_AUTOPLAY")' not in text:
    old_probe = '''            if (Environment.GetEnvironmentVariable("QUAVER_AUTOPLAY_GAMEPLAY") == "1")
            {
                if (MapManager.Selected.Value == null)
                    MapManager.Selected.Value = MapManager.Mapsets.SelectMany(x => x.Maps).FirstOrDefault();

                QuaverScreenManager.ScheduleScreenChange(() => new MapLoadingScreen(new List<Database.Scores.Score>()));
                return;
            }
'''
    new_block = '''            if (Environment.GetEnvironmentVariable("WARGAMES_QUAVER_AUTOPLAY") == "1")
            {
                var mapId = Environment.GetEnvironmentVariable("WARGAMES_QUAVER_MAP_ID");
                var mapPath = Environment.GetEnvironmentVariable("WARGAMES_QUAVER_MAP_PATH");
                var maps = MapManager.Mapsets.SelectMany(x => x.Maps).ToList();
                Map selected = null;

                if (int.TryParse(mapId, out var parsedMapId))
                    selected = maps.FirstOrDefault(x => x.MapId == parsedMapId);

                if (selected == null && !string.IsNullOrWhiteSpace(mapPath))
                    selected = maps.FirstOrDefault(x =>
                        string.Equals(Path.GetFileName(x.Path), Path.GetFileName(mapPath), StringComparison.OrdinalIgnoreCase));

                MapManager.Selected.Value = selected ?? maps.FirstOrDefault();
                QuaverScreenManager.ScheduleScreenChange(() => new MapLoadingScreen(new List<Database.Scores.Score>()));
                return;
            }
'''
    if old_probe in text:
        text = text.replace(old_probe, new_block, 1)
    else:
        text = text.replace(
            "            QuaverScreenManager.ScheduleScreenChange(() => new MainMenuScreen());\n",
            new_block + "            QuaverScreenManager.ScheduleScreenChange(() => new MainMenuScreen());\n",
            1,
        )
write(initialization, text)


ruleset = root / "Quaver.Shared" / "Screens" / "Gameplay" / "Rulesets" / "Keys" / "GameplayRulesetKeys.cs"
text = read(ruleset)
text = replace_once(
    text,
    "            processor.SteamId = SteamUser.GetSteamID().m_SteamID;\n",
    "            processor.SteamId = SteamManager.IsInitialized ? SteamUser.GetSteamID().m_SteamID : 0;\n",
)
write(ruleset, text)


view = root / "Quaver.Shared" / "Screens" / "Gameplay" / "GameplayScreenView.cs"
text = read(view)
text = replace_once(
    text,
    "            var selfAvatar = ConfigManager.Username.Value == scoreboardName\n                ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                : UserInterface.UnknownAvatar;\n",
    "            var selfAvatar = ConfigManager.Username.Value == scoreboardName && SteamManager.IsInitialized\n                ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                : UserInterface.UnknownAvatar;\n",
)
write(view, text)


scoreboard = root / "Quaver.Shared" / "Screens" / "Gameplay" / "UI" / "Scoreboard" / "ScoreboardUser.cs"
text = read(scoreboard)
text = replace_once(
    text,
    "                    if (SteamManager.UserAvatars.ContainsKey((ulong)LocalScore.SteamId))\n",
    "                    if (SteamManager.IsInitialized && SteamManager.UserAvatars.ContainsKey((ulong)LocalScore.SteamId))\n",
)
text = replace_optional(
    text,
    "                    ConfigManager.Username.Value == Name\n                        ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                        : UserInterface.UnknownAvatar;\n",
    "                    ConfigManager.Username.Value == Name && SteamManager.IsInitialized\n                        ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                        : UserInterface.UnknownAvatar;\n",
)
text = replace_optional(
    text,
    "                    Avatar.Image = ConfigManager.Username?.Value == UsernameRaw\n                        ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                        : UserInterface.UnknownAvatar;\n",
    "                    Avatar.Image = ConfigManager.Username?.Value == UsernameRaw && SteamManager.IsInitialized\n                        ? SteamManager.GetAvatarOrUnknown(SteamUser.GetSteamID().m_SteamID)\n                        : UserInterface.UnknownAvatar;\n",
)
write(scoreboard, text)


profile_banner = root / "Quaver.Shared" / "Screens" / "Selection" / "UI" / "Profile" / "LocalProfileBanner.cs"
text = read(profile_banner)
text = replace_once(
    text,
    "            if (SteamManager.UserAvatars != null)\n",
    "            if (SteamManager.IsInitialized && SteamManager.UserAvatars != null)\n",
)
write(profile_banner, text)


gameplay = root / "Quaver.Shared" / "Screens" / "Gameplay" / "GameplayScreen.cs"
text = read(gameplay)
if "using Quaver.Shared.Wargames;" not in text:
    text = text.replace(
        "using Quaver.Shared.Screens.Tournament.Gameplay;\n",
        "using Quaver.Shared.Screens.Tournament.Gameplay;\nusing Quaver.Shared.Wargames;\n",
        1,
    )
if "WargamesStateExporter.Write(this);" not in text:
    text = text.replace(
        "            base.Update(gameTime);\n",
        "            base.Update(gameTime);\n            WargamesStateExporter.Write(this);\n",
        1,
    )
write(gameplay, text)

for path, needle in {
    root / "Quaver.Shared" / "Wargames" / "WargamesStateExporter.cs": "WARGAMES_QUAVER_STATE_PATH",
    steam: "WARGAMES_QUAVER_DISABLE_STEAM",
    initialization: "WARGAMES_QUAVER_AUTOPLAY",
    gameplay: "WargamesStateExporter.Write(this);",
}.items():
    require(path, needle)
PY

dotnet restore "$source_root/Quaver/Quaver.csproj"
dotnet build "$source_root/Quaver/Quaver.csproj" -c Release --no-restore -v:minimal

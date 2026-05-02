package com.layerbrain.wargames.mindustry;

import arc.Events;
import arc.util.Timer;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import mindustry.Vars;
import mindustry.game.EventType;
import mindustry.game.Gamemode;
import mindustry.game.Rules;
import mindustry.game.Team;
import mindustry.game.Teams;
import mindustry.gen.Building;
import mindustry.maps.Map;
import mindustry.mod.Plugin;
import mindustry.world.blocks.storage.CoreBlock;

public class WargamesStatePlugin extends Plugin {
    private PrintWriter writer;
    private int intervalTicks = 30;
    private int tick = 0;
    private boolean missionStarted = false;

    @Override
    public void init() {
        String path = System.getenv("WARGAMES_MINDUSTRY_STATE_PATH");
        if (path == null || path.isBlank()) {
            return;
        }
        String interval = System.getenv("WARGAMES_MINDUSTRY_STATE_INTERVAL_TICKS");
        if (interval != null && !interval.isBlank()) {
            try {
                intervalTicks = Math.max(1, Integer.parseInt(interval));
            } catch (NumberFormatException ignored) {
                intervalTicks = 30;
            }
        }
        try {
            writer = new PrintWriter(new FileWriter(path, true), true);
        } catch (IOException e) {
            throw new RuntimeException("Failed to open WarGames state path: " + path, e);
        }
        Events.on(EventType.ClientLoadEvent.class, event -> scheduleMissionStart());
        Events.run(EventType.Trigger.update, this::writeTick);
        Timer.schedule(this::writeTick, 1f, 1f);
    }

    private void scheduleMissionStart() {
        String mapName = System.getenv("WARGAMES_MINDUSTRY_AUTO_MAP");
        if (mapName == null || mapName.isBlank()) {
            return;
        }
        Timer.schedule(this::startMission, 0.5f, 0.5f, 20);
    }

    private void startMission() {
        if (missionStarted || Vars.control == null || Vars.maps == null) {
            return;
        }
        String mapName = System.getenv("WARGAMES_MINDUSTRY_AUTO_MAP");
        if (mapName == null || mapName.isBlank()) {
            return;
        }
        Map map = Vars.maps.byName(mapName);
        if (map == null) {
            return;
        }
        Gamemode mode = gamemode(System.getenv("WARGAMES_MINDUSTRY_AUTO_MODE"));
        Rules rules = map.applyRules(mode);
        rules.winWave = intEnv("WARGAMES_MINDUSTRY_WIN_WAVE", rules.winWave);
        rules.waves = true;
        rules.waveTimer = true;
        rules.canGameOver = true;
        Vars.control.playMap(map, rules);
        missionStarted = true;
    }

    private void writeTick() {
        if (writer == null || Vars.state == null || Vars.state.map == null) {
            return;
        }
        tick++;
        if (tick % intervalTicks != 0) {
            return;
        }
        boolean shardedHasCore = Team.sharded.core() != null;
        boolean finished = Vars.state.won || (Vars.state.rules.winWave > 0 && Vars.state.wave >= Vars.state.rules.winWave);
        boolean failed = Vars.state.gameOver || !shardedHasCore;
        writer.print("{\"v\":1,\"tick\":");
        writer.print(tick);
        writer.print(",\"mission\":{\"finished\":");
        writer.print(finished);
        writer.print(",\"failed\":");
        writer.print(failed);
        writer.print("},\"game\":{\"map\":");
        writeString(Vars.state.map.name());
        writer.print(",\"wave\":");
        writer.print(Vars.state.wave);
        writer.print(",\"enemies\":");
        writer.print(Vars.state.enemies);
        writer.print(",\"tick\":");
        writer.print((int)Vars.state.tick);
        writer.print(",\"won\":");
        writer.print(Vars.state.won);
        writer.print(",\"game_over\":");
        writer.print(Vars.state.gameOver);
        writer.print("},\"teams\":[");
        boolean first = true;
        for (Teams.TeamData data : Vars.state.teams.active) {
            if (!first) {
                writer.print(",");
            }
            first = false;
            writeTeam(data);
        }
        writer.println("]}");
    }

    private void writeTeam(Teams.TeamData data) {
        float coreHealth = 0f;
        for (CoreBlock.CoreBuild core : data.cores) {
            coreHealth += core.health;
        }
        writer.print("{\"id\":");
        writer.print(data.team.id);
        writer.print(",\"name\":");
        writeString(data.team.name);
        writer.print(",\"cores\":");
        writer.print(data.cores.size);
        writer.print(",\"units\":");
        writer.print(data.units.size);
        writer.print(",\"buildings\":");
        writer.print(data.buildings.size);
        writer.print(",\"items\":");
        writer.print(data.team.items().total());
        writer.print(",\"core_health\":");
        writer.print(coreHealth);
        writer.print("}");
    }

    private void writeString(String value) {
        writer.print("\"");
        String text = value == null ? "" : value;
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            switch (ch) {
                case '\\':
                    writer.print("\\\\");
                    break;
                case '"':
                    writer.print("\\\"");
                    break;
                case '\n':
                    writer.print("\\n");
                    break;
                case '\r':
                    writer.print("\\r");
                    break;
                case '\t':
                    writer.print("\\t");
                    break;
                default:
                    writer.print(ch);
                    break;
            }
        }
        writer.print("\"");
    }

    private Gamemode gamemode(String raw) {
        if (raw == null || raw.isBlank()) {
            return Gamemode.survival;
        }
        try {
            return Gamemode.valueOf(raw);
        } catch (IllegalArgumentException e) {
            return Gamemode.survival;
        }
    }

    private int intEnv(String name, int fallback) {
        String raw = System.getenv(name);
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }
}

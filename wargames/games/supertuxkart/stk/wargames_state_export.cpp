#include "wargames/wargames_state_export.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <string>

#include "items/powerup.hpp"
#include "items/powerup_manager.hpp"
#include "karts/abstract_kart.hpp"
#include "karts/controller/controller.hpp"
#include "karts/controller/kart_control.hpp"
#include "modes/linear_world.hpp"
#include "modes/world.hpp"
#include "modes/world_with_rank.hpp"
#include "race/race_manager.hpp"
#include "tracks/track.hpp"

namespace
{
const char* boolText(bool value)
{
    return value ? "true" : "false";
}

int readInterval()
{
    const char* raw = std::getenv("WARGAMES_STK_STATE_INTERVAL_TICKS");
    if (!raw || !*raw)
        return 2;
    const int value = std::atoi(raw);
    return std::max(1, value);
}

void writeJsonString(FILE* file, const std::string& value)
{
    std::fputc('"', file);
    for (char ch : value)
    {
        switch (ch)
        {
        case '\\':
            std::fputs("\\\\", file);
            break;
        case '"':
            std::fputs("\\\"", file);
            break;
        case '\n':
            std::fputs("\\n", file);
            break;
        case '\r':
            std::fputs("\\r", file);
            break;
        case '\t':
            std::fputs("\\t", file);
            break;
        default:
            std::fputc(ch, file);
            break;
        }
    }
    std::fputc('"', file);
}

void writeNullableFloat(FILE* file, float value, bool has_value)
{
    if (has_value)
        std::fprintf(file, "%.6f", value);
    else
        std::fputs("null", file);
}

void writeNullableInt(FILE* file, int value, bool has_value)
{
    if (has_value)
        std::fprintf(file, "%d", value);
    else
        std::fputs("null", file);
}

const char* powerupName(PowerupManager::PowerupType type)
{
    switch (type)
    {
    case PowerupManager::POWERUP_BUBBLEGUM:
        return "bubblegum";
    case PowerupManager::POWERUP_CAKE:
        return "cake";
    case PowerupManager::POWERUP_BOWLING:
        return "bowling";
    case PowerupManager::POWERUP_ZIPPER:
        return "zipper";
    case PowerupManager::POWERUP_PLUNGER:
        return "plunger";
    case PowerupManager::POWERUP_SWITCH:
        return "switch";
    case PowerupManager::POWERUP_SWATTER:
        return "swatter";
    case PowerupManager::POWERUP_RUBBERBALL:
        return "rubberball";
    case PowerupManager::POWERUP_PARACHUTE:
        return "parachute";
    case PowerupManager::POWERUP_ANVIL:
        return "anvil";
    case PowerupManager::POWERUP_NOTHING:
    default:
        return "none";
    }
}

const char* phaseName(WorldStatus::Phase phase)
{
    switch (phase)
    {
    case WorldStatus::TRACK_INTRO_PHASE:
        return "track_intro";
    case WorldStatus::SETUP_PHASE:
        return "setup";
    case WorldStatus::WAIT_FOR_SERVER_PHASE:
        return "wait_for_server";
    case WorldStatus::SERVER_READY_PHASE:
        return "server_ready";
    case WorldStatus::READY_PHASE:
        return "ready";
    case WorldStatus::SET_PHASE:
        return "set";
    case WorldStatus::GO_PHASE:
        return "go";
    case WorldStatus::MUSIC_PHASE:
        return "music";
    case WorldStatus::RACE_PHASE:
        return "race";
    case WorldStatus::DELAY_FINISH_PHASE:
        return "delay_finish";
    case WorldStatus::RESULT_DISPLAY_PHASE:
        return "result_display";
    case WorldStatus::FINISH_PHASE:
        return "finish";
    case WorldStatus::IN_GAME_MENU_PHASE:
        return "in_game_menu";
    case WorldStatus::UNDEFINED_PHASE:
    default:
        return "undefined";
    }
}
}

WarGamesStateExport::WarGamesStateExport() :
    m_file(nullptr),
    m_interval_ticks(readInterval()),
    m_last_tick(-1)
{
    const char* path = std::getenv("WARGAMES_STK_STATE_PATH");
    if (path && *path)
    {
        m_file = std::fopen(path, "a");
        if (m_file)
            std::setvbuf(m_file, nullptr, _IOLBF, 0);
    }
}

WarGamesStateExport::~WarGamesStateExport()
{
    if (m_file)
        std::fclose(m_file);
}

WarGamesStateExport& WarGamesStateExport::get()
{
    static WarGamesStateExport exporter;
    return exporter;
}

void WarGamesStateExport::tick()
{
    if (!m_file)
        return;
    World* world = World::getWorld();
    if (!world)
        return;
    const int tick = world->getTicksSinceStart();
    if (m_last_tick >= 0 && tick - m_last_tick < m_interval_ticks)
        return;
    m_last_tick = tick;
    writeWorld(world);
    std::fputc('\n', m_file);
}

void WarGamesStateExport::writeWorld(World* world)
{
    Track* track = Track::getCurrentTrack();
    const std::string track_id = track ? track->getIdent() : "";
    const float track_length = track ? track->getTrackLength() : 0.0f;
    const int laps = RaceManager::get()->getNumLaps();
    const unsigned int num_karts = world->getNumKarts();
    int player_kart_id = -1;
    bool player_finished = false;
    bool player_failed = false;

    for (unsigned int i = 0; i < num_karts; i++)
    {
        AbstractKart* kart = world->getKart((int)i);
        const Controller* controller = kart ? kart->getController() : nullptr;
        if (controller && controller->isLocalPlayerController())
        {
            player_kart_id = (int)i;
            player_finished = kart->hasFinishedRace();
            player_failed = kart->isEliminated();
            break;
        }
    }

    std::fprintf(m_file, "{\"v\":1,\"tick\":%d,\"player_kart_id\":%d,", world->getTicksSinceStart(),
                 player_kart_id);
    std::fputs("\"mission\":{\"finished\":", m_file);
    std::fputs(boolText(player_finished), m_file);
    std::fputs(",\"failed\":", m_file);
    std::fputs(boolText(player_failed), m_file);
    std::fputs("},\"race\":{\"track\":", m_file);
    writeJsonString(m_file, track_id);
    std::fprintf(m_file, ",\"laps\":%d,\"num_karts\":%u,\"elapsed_ticks\":%d,"
                         "\"elapsed_seconds\":%.6f,\"phase\":",
                 laps, num_karts, world->getTimeTicks(), world->getTime());
    writeJsonString(m_file, phaseName(world->getPhase()));
    std::fputs("},\"karts\":[", m_file);
    for (unsigned int i = 0; i < num_karts; i++)
    {
        if (i > 0)
            std::fputc(',', m_file);
        writeKart(world, world->getKart((int)i), i, track_length, laps);
    }
    std::fputs("]}", m_file);
}

void WarGamesStateExport::writeKart(World* world, AbstractKart* kart, unsigned int index,
                                    float track_length, int laps)
{
    LinearWorld* linear_world = dynamic_cast<LinearWorld*>(world);
    WorldWithRank* ranked_world = dynamic_cast<WorldWithRank*>(world);
    const Controller* controller = kart ? kart->getController() : nullptr;
    const KartControl& controls = kart->getControls();
    const Vec3& xyz = kart->getXYZ();
    const btVector3& velocity = kart->getVelocity();
    const bool has_linear = linear_world != nullptr;
    const float distance = has_linear ? linear_world->getOverallDistance(index) : 0.0f;
    const float distance_down_track =
        has_linear ? linear_world->getDistanceDownTrackForKart((int)index, true) : 0.0f;
    const float full_distance = track_length > 0.0f && laps > 0 ? track_length * laps : 0.0f;
    const float progress =
        full_distance > 0.0f ? std::max(0.0f, std::min(1.0f, distance / full_distance)) : 0.0f;
    const Powerup* powerup = kart->getPowerup();
    const bool has_ranked = ranked_world != nullptr;

    std::fputs("{\"id\":", m_file);
    std::fprintf(m_file, "%u,\"kart\":", index);
    writeJsonString(m_file, kart->getIdent());
    std::fputs(",\"local_player\":", m_file);
    std::fputs(boolText(controller && controller->isLocalPlayerController()), m_file);
    std::fputs(",\"rank\":", m_file);
    writeNullableInt(m_file, kart->getPosition(), true);
    std::fputs(",\"lap\":", m_file);
    writeNullableInt(m_file, has_linear ? linear_world->getLapForKart((int)index) : 0, has_linear);
    std::fputs(",\"distance\":", m_file);
    writeNullableFloat(m_file, distance, has_linear);
    std::fputs(",\"distance_down_track\":", m_file);
    writeNullableFloat(m_file, distance_down_track, has_linear);
    std::fputs(",\"progress\":", m_file);
    writeNullableFloat(m_file, progress, full_distance > 0.0f);
    std::fprintf(m_file, ",\"x\":%.6f,\"y\":%.6f,\"z\":%.6f", xyz.getX(), xyz.getY(),
                 xyz.getZ());
    std::fprintf(m_file, ",\"velocity_x\":%.6f,\"velocity_y\":%.6f,\"velocity_z\":%.6f",
                 velocity.getX(), velocity.getY(), velocity.getZ());
    std::fprintf(m_file, ",\"speed\":%.6f,\"heading\":%.6f,\"pitch\":%.6f,\"roll\":%.6f",
                 kart->getSpeed(), kart->getHeading(), kart->getPitch(), kart->getRoll());
    std::fprintf(m_file, ",\"steering\":%.6f,\"throttle\":%.6f", controls.getSteer(),
                 controls.getAccel());
    std::fputs(",\"braking\":", m_file);
    std::fputs(boolText(controls.getBrake()), m_file);
    std::fputs(",\"nitro\":", m_file);
    std::fputs(boolText(controls.getNitro()), m_file);
    std::fprintf(m_file, ",\"energy\":%.6f,\"powerup\":", kart->getEnergy());
    writeJsonString(m_file, powerupName(powerup ? powerup->getType() : PowerupManager::POWERUP_NOTHING));
    std::fprintf(m_file, ",\"powerup_count\":%d", kart->getNumPowerup());
    std::fputs(",\"on_ground\":", m_file);
    std::fputs(boolText(kart->isOnGround()), m_file);
    std::fputs(",\"on_road\":", m_file);
    if (has_ranked)
        std::fputs(boolText(ranked_world->isOnRoad(index)), m_file);
    else
        std::fputs("null", m_file);
    std::fputs(",\"finished\":", m_file);
    std::fputs(boolText(kart->hasFinishedRace()), m_file);
    std::fputs(",\"eliminated\":", m_file);
    std::fputs(boolText(kart->isEliminated()), m_file);
    std::fputs(",\"rescue\":", m_file);
    std::fputs(boolText(controls.getRescue()), m_file);
    std::fputs("}", m_file);
}

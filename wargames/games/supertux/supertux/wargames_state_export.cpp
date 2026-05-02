#include "wargames/wargames_state_export.hpp"

#include <algorithm>
#include <cstdlib>
#include <string>

#include "object/player.hpp"
#include "supertux/game_session.hpp"
#include "supertux/level.hpp"
#include "supertux/sector.hpp"
#include "supertux/statistics.hpp"

namespace
{
const char* boolText(bool value)
{
    return value ? "true" : "false";
}

int readInterval()
{
    const char* raw = std::getenv("WARGAMES_SUPERTUX_STATE_INTERVAL_TICKS");
    if (!raw || !*raw)
        return 1;
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
}

WarGamesStateExport::WarGamesStateExport() :
    m_file(nullptr),
    m_interval_ticks(readInterval()),
    m_tick(0)
{
    const char* path = std::getenv("WARGAMES_SUPERTUX_STATE_PATH");
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

void WarGamesStateExport::tick(GameSession& session)
{
    if (!m_file)
        return;
    m_tick++;
    if (m_interval_ticks > 1 && m_tick % m_interval_ticks != 0)
        return;
    writeWorld(session);
    std::fputc('\n', m_file);
}

void WarGamesStateExport::writeWorld(GameSession& session)
{
    Level& level = session.get_current_level();
    Sector& sector = session.get_current_sector();
    const auto& players = sector.get_players();
    Player* player = players.empty() ? nullptr : players[0];
    const Statistics& stats = level.m_stats;
    const bool finished = session.has_active_sequence() || (player && player->is_winning());
    const bool failed = player && player->is_dead();

    std::fprintf(m_file, "{\"v\":1,\"tick\":%d,", m_tick);
    std::fputs("\"mission\":{\"finished\":", m_file);
    std::fputs(boolText(finished), m_file);
    std::fputs(",\"failed\":", m_file);
    std::fputs(boolText(failed), m_file);
    std::fputs("},\"level\":{\"file\":", m_file);
    writeJsonString(m_file, session.get_level_file());
    std::fputs(",\"name\":", m_file);
    writeJsonString(m_file, level.get_name());
    std::fputs(",\"set\":", m_file);
    writeJsonString(m_file, "");
    std::fprintf(m_file,
                 ",\"elapsed_ticks\":%d,\"coins\":%d,\"total_coins\":%d,"
                 "\"secrets\":%d,\"total_secrets\":%d,\"target_time_seconds\":",
                 m_tick,
                 stats.get_coins(),
                 stats.m_total_coins,
                 stats.get_secrets(),
                 stats.m_total_secrets);
    if (level.m_target_time > 0.0f)
        std::fprintf(m_file, "%.6f", level.m_target_time);
    else
        std::fputs("null", m_file);
    std::fputs("},\"player\":{", m_file);
    std::fputs("\"x\":", m_file);
    writeNullableFloat(m_file, player ? player->get_pos().x : 0.0f, player != nullptr);
    std::fputs(",\"y\":", m_file);
    writeNullableFloat(m_file, player ? player->get_pos().y : 0.0f, player != nullptr);
    std::fputs(",\"vx\":", m_file);
    writeNullableFloat(m_file, player ? player->get_velocity_x() : 0.0f, player != nullptr);
    std::fputs(",\"vy\":", m_file);
    writeNullableFloat(m_file, player ? player->get_velocity_y() : 0.0f, player != nullptr);
    std::fprintf(m_file,
                 ",\"coins\":%d,\"bonus\":",
                 player ? player->get_coins() : 0);
    writeJsonString(m_file, player ? player->bonus_to_string() : "none");
    std::fputs(",\"alive\":", m_file);
    std::fputs(boolText(player && player->is_alive()), m_file);
    std::fputs(",\"dead\":", m_file);
    std::fputs(boolText(player && player->is_dead()), m_file);
    std::fputs(",\"winning\":", m_file);
    std::fputs(boolText(player && player->is_winning()), m_file);
    std::fputs("}}", m_file);
}

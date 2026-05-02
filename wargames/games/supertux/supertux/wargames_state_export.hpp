#ifndef HEADER_WARGAMES_SUPERTUX_STATE_EXPORT_HPP
#define HEADER_WARGAMES_SUPERTUX_STATE_EXPORT_HPP

#include <cstdio>

class GameSession;

class WarGamesStateExport
{
private:
    FILE* m_file;
    int m_interval_ticks;
    int m_tick;

    WarGamesStateExport();
    ~WarGamesStateExport();

    void writeWorld(GameSession& session);

public:
    static WarGamesStateExport& get();
    void tick(GameSession& session);
};

#endif

#ifndef HEADER_WARGAMES_STATE_EXPORT_HPP
#define HEADER_WARGAMES_STATE_EXPORT_HPP

#include <cstdio>

class World;
class AbstractKart;

class WarGamesStateExport
{
private:
    FILE* m_file;
    int m_interval_ticks;
    int m_last_tick;

    WarGamesStateExport();
    ~WarGamesStateExport();

    void writeWorld(World* world);
    void writeKart(World* world, AbstractKart* kart, unsigned int index, float track_length,
                   int laps);

public:
    static WarGamesStateExport& get();
    void tick();
};

#endif

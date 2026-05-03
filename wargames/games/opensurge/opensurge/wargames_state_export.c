#include "wargames_state_export.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../entities/player.h"
#include "../scenes/level.h"

static int last_tick = -1;

static int export_interval(void)
{
    const char* raw = getenv("WARGAMES_OPENSURGE_STATE_INTERVAL_TICKS");
    if(raw == NULL || raw[0] == '\0')
        return 1;
    int value = atoi(raw);
    return value > 0 ? value : 1;
}

static void json_string(FILE* fp, const char* value)
{
    fputc('"', fp);
    if(value != NULL) {
        for(const unsigned char* p = (const unsigned char*)value; *p != '\0'; p++) {
            if(*p == '"' || *p == '\\')
                fputc('\\', fp);
            if(*p >= 0x20)
                fputc((int)*p, fp);
        }
    }
    fputc('"', fp);
}

void Wargames_StateExport_Tick(void)
{
    const char* path = getenv("WARGAMES_OPENSURGE_STATE_PATH");
    if(path == NULL || path[0] == '\0')
        return;

    const float elapsed_seconds = level_time();
    const int tick = (int)(elapsed_seconds * 60.0f);
    if(tick < last_tick)
        last_tick = -1;
    if(tick == last_tick || tick % export_interval() != 0)
        return;
    last_tick = tick;

    player_t* player = level_player();
    const v2d_t size = level_size();
    const v2d_t position = player != NULL ? player_position(player) : v2d_new(0.0f, 0.0f);

    const int dying = player != NULL && player_is_dying(player);
    const int lives = player_get_lives();
    const int finished = level_has_been_cleared() || (player != NULL && player_is_winning(player));
    const int failed = dying || lives <= 0;

    FILE* fp = fopen(path, "a");
    if(fp == NULL)
        return;

    fprintf(fp, "{\"tick\":%d,", tick);
    fprintf(fp, "\"mission\":{\"finished\":%s,\"failed\":%s},", finished ? "true" : "false", failed ? "true" : "false");
    fprintf(fp, "\"level\":{\"file\":");
    json_string(fp, level_file());
    fprintf(fp, ",\"name\":");
    json_string(fp, level_name());
    fprintf(
        fp,
        ",\"act\":%d,\"elapsed_ticks\":%d,\"elapsed_seconds\":%.4f,\"width\":%.2f,\"height\":%.2f},",
        level_act(),
        tick,
        elapsed_seconds,
        size.x,
        size.y
    );
    fprintf(fp, "\"player\":{");
    if(player == NULL) {
        fprintf(fp, "\"x\":null,\"y\":null,\"xsp\":null,\"ysp\":null,\"gsp\":null,\"speed\":null,");
    }
    else {
        fprintf(
            fp,
            "\"x\":%.4f,\"y\":%.4f,\"xsp\":%.4f,\"ysp\":%.4f,\"gsp\":%.4f,\"speed\":%.4f,",
            position.x,
            position.y,
            player_xsp(player),
            player_ysp(player),
            player_gsp(player),
            player_speed(player)
        );
    }
    fprintf(
        fp,
        "\"rings\":%d,\"score\":%d,\"lives\":%d,\"alive\":%s,\"dying\":%s,\"winning\":%s,\"rolling\":%s,\"jumping\":%s}}\n",
        player_get_collectibles(),
        player_get_score(),
        lives,
        player != NULL && !dying ? "true" : "false",
        dying ? "true" : "false",
        player != NULL && player_is_winning(player) ? "true" : "false",
        player != NULL && player_is_rolling(player) ? "true" : "false",
        player != NULL && player_is_jumping(player) ? "true" : "false"
    );
    fclose(fp);
}

#include <stdlib.h>
#include <stdio.h>

#include "doomdef.h"
#include "doomstat.h"
#include "wargames_state_export.h"

static FILE *state_file = NULL;
static int state_interval = 1;
static int last_damage_taken = 0;

static void Wargames_EnsureStateFile(void)
{
    const char *path;
    const char *interval;

    if (state_file != NULL)
    {
        return;
    }

    path = getenv("WARGAMES_DOOM_STATE_PATH");
    if (path == NULL || path[0] == '\0')
    {
        return;
    }

    interval = getenv("WARGAMES_DOOM_STATE_INTERVAL_TICKS");
    if (interval != NULL && interval[0] != '\0')
    {
        state_interval = atoi(interval);
        if (state_interval <= 0)
        {
            state_interval = 1;
        }
    }

    state_file = fopen(path, "a");
    if (state_file != NULL)
    {
        setvbuf(state_file, NULL, _IOLBF, 0);
    }
}

static void Wargames_WriteBoolArray(const boolean *values, int count)
{
    int i;

    fputc('[', state_file);
    for (i = 0; i < count; ++i)
    {
        if (i > 0)
        {
            fputc(',', state_file);
        }
        fputs(values[i] ? "true" : "false", state_file);
    }
    fputc(']', state_file);
}

static void Wargames_WriteIntBoolArray(const int *values, int count)
{
    int i;

    fputc('[', state_file);
    for (i = 0; i < count; ++i)
    {
        if (i > 0)
        {
            fputc(',', state_file);
        }
        fputs(values[i] ? "true" : "false", state_file);
    }
    fputc(']', state_file);
}

static void Wargames_WriteIntArray(const int *values, int count)
{
    int i;

    fputc('[', state_file);
    for (i = 0; i < count; ++i)
    {
        if (i > 0)
        {
            fputc(',', state_file);
        }
        fprintf(state_file, "%d", values[i]);
    }
    fputc(']', state_file);
}

void Wargames_StateExport_Tick(void)
{
    player_t *player;
    int health;
    int damage_taken;
    int finished;
    int failed;
    int map_number;
    const char *map_prefix;

    Wargames_EnsureStateFile();
    if (state_file == NULL)
    {
        return;
    }
    if (state_interval > 1 && gamestate == GS_LEVEL && leveltime % state_interval != 0)
    {
        return;
    }

    player = &players[consoleplayer];
    health = player->mo != NULL ? player->mo->health : player->health;
    if (health < 0)
    {
        health = 0;
    }
    if (leveltime == 0)
    {
        last_damage_taken = 0;
    }
    damage_taken = last_damage_taken + player->damagecount;
    if (health < player->health)
    {
        damage_taken += player->health - health;
    }
    if (damage_taken > last_damage_taken)
    {
        last_damage_taken = damage_taken;
    }

    finished = gamestate == GS_INTERMISSION || gamestate == GS_FINALE;
    failed = player->playerstate == PST_DEAD || health <= 0;
    map_prefix = gamemode == commercial ? "MAP" : "E";
    map_number = gamemap;

    fprintf(state_file,
            "{\"tick\":%d,"
            "\"mission\":{\"finished\":%s,\"failed\":%s},"
            "\"level\":{"
            "\"map\":\"",
            leveltime,
            finished ? "true" : "false",
            failed ? "true" : "false");
    if (gamemode == commercial)
    {
        fprintf(state_file, "%s%02d", map_prefix, map_number);
    }
    else
    {
        fprintf(state_file, "%s%dM%d", map_prefix, gameepisode, map_number);
    }
    fprintf(state_file,
            "\",\"episode\":");
    if (gamemode == commercial)
    {
        fputs("null", state_file);
    }
    else
    {
        fprintf(state_file, "%d", gameepisode);
    }
    fprintf(state_file,
            ",\"map_number\":%d,"
            "\"skill\":%d,"
            "\"elapsed_ticks\":%d,"
            "\"kills\":%d,"
            "\"total_kills\":%d,"
            "\"items\":%d,"
            "\"total_items\":%d,"
            "\"secrets\":%d,"
            "\"total_secrets\":%d"
            "},"
            "\"player\":{"
            "\"x\":",
            map_number,
            (int) gameskill + 1,
            leveltime,
            player->killcount,
            totalkills,
            player->itemcount,
            totalitems,
            player->secretcount,
            totalsecret);
    if (player->mo != NULL)
    {
        fprintf(state_file,
                "%.2f,\"y\":%.2f,\"angle\":%.2f",
                (double) player->mo->x / FRACUNIT,
                (double) player->mo->y / FRACUNIT,
                (double) player->mo->angle * 360.0 / 4294967296.0);
    }
    else
    {
        fputs("null,\"y\":null,\"angle\":null", state_file);
    }
    fprintf(state_file,
            ",\"health\":%d,"
            "\"armor\":%d,"
            "\"ammo\":",
            health,
            player->armorpoints);
    Wargames_WriteIntArray(player->ammo, NUMAMMO);
    fputs(",\"weapons\":", state_file);
    Wargames_WriteIntBoolArray(player->weaponowned, NUMWEAPONS);
    fputs(",\"keys\":", state_file);
    Wargames_WriteBoolArray(player->cards, NUMCARDS);
    fprintf(state_file,
            ",\"damage_taken\":%d,"
            "\"dead\":%s"
            "}}\n",
            last_damage_taken,
            failed ? "true" : "false");
}

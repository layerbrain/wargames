using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Quaver.API.Enums;
using Quaver.Shared.Screens.Gameplay;

namespace Quaver.Shared.Wargames
{
    public static class WargamesStateExporter
    {
        private static readonly object Lock = new object();
        private static long Tick;
        private static string StatePath;
        private static int? Interval;

        public static void Write(GameplayScreen screen)
        {
            var path = GetStatePath();
            if (string.IsNullOrWhiteSpace(path) || screen?.Ruleset?.ScoreProcessor == null)
                return;

            var tick = ++Tick;
            var interval = GetInterval();
            if (interval > 1 && tick % interval != 0)
                return;

            var processor = screen.Ruleset.ScoreProcessor;
            var map = screen.Map;
            var judgements = processor.CurrentJudgements.ToDictionary(
                item => item.Key.ToString().ToLowerInvariant(),
                item => item.Value
            );
            var totalJudgements = map.HitObjects.Sum(hitObject => hitObject.JudgementCount);
            var longNotes = map.HitObjects.Count(hitObject => hitObject.IsLongNote && hitObject.Type != HitObjectType.Mine);
            var mines = map.HitObjects.Count(hitObject => hitObject.Type == HitObjectType.Mine);

            var payload = new
            {
                tick,
                mission = new
                {
                    finished = screen.IsPlayComplete,
                    failed = screen.Failed || processor.Failed,
                },
                chart = new
                {
                    map_id = map.MapId,
                    mapset_id = map.MapSetId,
                    title = map.Title,
                    artist = map.Artist,
                    difficulty_name = map.DifficultyName,
                    mode = map.Mode.ToString(),
                    key_count = map.GetKeyCount(),
                    song_length_ms = map.Length,
                    hit_objects = map.HitObjects.Count,
                    long_notes = longNotes,
                    mines,
                    total_judgements = totalJudgements,
                },
                gameplay = new
                {
                    song_time_ms = screen.Timing.Time,
                    started = screen.HasStarted,
                    paused = screen.IsPaused,
                    completed = screen.IsPlayComplete,
                    failed = screen.Failed || processor.Failed,
                    health = processor.Health,
                    score = processor.Score,
                    accuracy = processor.Accuracy,
                    combo = processor.Combo,
                    max_combo = processor.MaxCombo,
                    total_judgement_count = processor.TotalJudgementCount,
                    stats_count = processor.Stats.Count,
                },
                judgements,
            };

            var line = JsonSerializer.Serialize(payload);
            lock (Lock)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
                File.AppendAllText(path, line + Environment.NewLine);
            }
        }

        private static string GetStatePath()
        {
            if (StatePath == null)
                StatePath = Environment.GetEnvironmentVariable("WARGAMES_QUAVER_STATE_PATH");
            return StatePath;
        }

        private static int GetInterval()
        {
            if (Interval.HasValue)
                return Interval.Value;
            var raw = Environment.GetEnvironmentVariable("WARGAMES_QUAVER_STATE_INTERVAL_TICKS");
            if (!int.TryParse(raw, out var value) || value < 1)
                value = 1;
            Interval = value;
            return value;
        }
    }
}

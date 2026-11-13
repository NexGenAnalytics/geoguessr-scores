// Pure data helpers for the dashboard: CSV parsing and stat crunching (no DOM).

export const PERFECT_ROUND = 5000;
export const ROUNDS_PER_GAME = 5;
export const BLUNDER_ROUND = 1000;
export const EARTH_CIRCUMFERENCE_KM = 40075;

export const sum = (values) => values.reduce((total, v) => total + v, 0);
export const mean = (values) => (values.length ? sum(values) / values.length : null);

export function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function stdev(values) {
  if (values.length < 2) return 0;
  const avg = mean(values);
  return Math.sqrt(mean(values.map((v) => (v - avg) ** 2)));
}

export function quantile(sortedValues, q) {
  const pos = (sortedValues.length - 1) * q;
  const lower = Math.floor(pos);
  const upper = Math.ceil(pos);
  return sortedValues[lower] + (sortedValues[upper] - sortedValues[lower]) * (pos - lower);
}

export function groupBy(items, keyOf) {
  const groups = new Map();
  for (const item of items) {
    const key = keyOf(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

/** RFC 4180-style CSV parsing into one object per row, keyed by the header. */
export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else field += ch;
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [header = [], ...body] = rows;
  return body
    .filter((r) => r.some(Boolean))
    .map((r) => Object.fromEntries(header.map((name, i) => [name, r[i] ?? ""])));
}

const optionalNumber = (value) => (value === "" || value == null ? null : Number(value));

/** Normalize CSV records into typed games. Distances become kilometers. */
export function toGames(records) {
  return records.map((r) => {
    const rounds = r.round_scores ? r.round_scores.split(";").map(Number) : null;
    const meters = optionalNumber(r.total_distance);
    return {
      date: r.challenge_date,
      playerId: r.player_id,
      playerName: r.player_name,
      scrapedAt: r.scraped_at,
      score: Number(r.total_score),
      timeSeconds: optionalNumber(r.total_time_seconds),
      distanceKm: meters == null ? null : meters / 1000,
      rounds: rounds && rounds.length === ROUNDS_PER_GAME ? rounds : null,
    };
  });
}

/** Players in order of first appearance, so a new player never repaints existing ones. */
export function listPlayers(games) {
  const ordered = [...games].sort(
    (a, b) => a.date.localeCompare(b.date) || a.playerId.localeCompare(b.playerId),
  );
  const byId = new Map();
  for (const g of ordered) {
    const player = byId.get(g.playerId);
    if (!player) byId.set(g.playerId, { id: g.playerId, name: g.playerName, nameAt: g.scrapedAt });
    else if (g.scrapedAt >= player.nameAt) Object.assign(player, { name: g.playerName, nameAt: g.scrapedAt });
  }
  return [...byId.values()].map(({ id, name }, index) => ({ id, name, index }));
}

/** Monday is 0, Sunday is 6. */
export function weekday(date) {
  return (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7;
}

export function shiftDate(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Apply the dashboard filters. fairFight keeps only days every remaining player played. */
export function filterGames(games, { from = null, to = null, includeWeekends = true, playerIds = null, fairFight = false } = {}) {
  const kept = games.filter(
    (g) =>
      (!from || g.date >= from) &&
      (!to || g.date <= to) &&
      (includeWeekends || weekday(g.date) < 5) &&
      (!playerIds || playerIds.has(g.playerId)),
  );
  if (!fairFight) return kept;
  const playerCount = new Set(kept.map((g) => g.playerId)).size;
  const byDate = groupBy(kept, (g) => g.date);
  return kept.filter((g) => byDate.get(g.date).length === playerCount);
}

/** One entry per date, oldest first, with that day's games ranked best first. */
export function dailyResults(games) {
  return [...groupBy(games, (g) => g.date)]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, dayGames]) => {
      const ranked = [...dayGames].sort((a, b) => b.score - a.score);
      const top = ranked[0].score;
      const contested = ranked.length > 1;
      return {
        date,
        ranked,
        contested,
        winners: contested ? ranked.filter((g) => g.score === top).map((g) => g.playerId) : [],
        margin: contested ? top - ranked[1].score : null,
      };
    });
}

export function gamesByPlayer(games) {
  const grouped = groupBy(games, (g) => g.playerId);
  for (const playerGames of grouped.values()) playerGames.sort((a, b) => a.date.localeCompare(b.date));
  return grouped;
}

/** Longest and current run of contested days won; days a player sat out don't break a run. */
export function winStreaks(daily) {
  const runs = new Map();
  for (const day of daily.filter((d) => d.contested)) {
    for (const g of day.ranked) {
      const run = runs.get(g.playerId) ?? { current: 0, longest: 0, longestEnd: null };
      if (day.winners.includes(g.playerId)) {
        run.current += 1;
        if (run.current > run.longest) Object.assign(run, { longest: run.current, longestEnd: day.date });
      } else run.current = 0;
      runs.set(g.playerId, run);
    }
  }
  return runs;
}

/** Summary row per player, best average first. Wins only count days with company. */
export function playerStats(games, daily = dailyResults(games)) {
  const streaks = winStreaks(daily);
  return [...gamesByPlayer(games)]
    .map(([playerId, playerGames]) => {
      const scores = playerGames.map((g) => g.score);
      const rounds = playerGames.flatMap((g) => g.rounds ?? []);
      const kms = playerGames.filter((g) => g.distanceKm != null).map((g) => g.distanceKm);
      const contestedDays = daily.filter((d) => d.contested && d.ranked.some((g) => g.playerId === playerId));
      const wins = contestedDays.filter((d) => d.winners.includes(playerId)).length;
      const fiveKs = rounds.filter((s) => s === PERFECT_ROUND).length;
      return {
        playerId,
        games: playerGames.length,
        average: mean(scores),
        median: median(scores),
        best: Math.max(...scores),
        worst: Math.min(...scores),
        stdev: stdev(scores),
        wins,
        contested: contestedDays.length,
        winRate: contestedDays.length ? wins / contestedDays.length : 0,
        roundsTracked: rounds.length,
        fiveKs,
        fiveKRate: rounds.length ? fiveKs / rounds.length : 0,
        totalKm: sum(kms),
        kmPerRound: kms.length ? sum(kms) / (kms.length * ROUNDS_PER_GAME) : null,
        streak: streaks.get(playerId) ?? { current: 0, longest: 0, longestEnd: null },
        recent: scores.slice(-20),
      };
    })
    .sort((a, b) => b.average - a.average);
}

/** Trailing mean; early points average over however many values exist so far. */
export function rollingMean(values, window) {
  return values.map((_, i) => mean(values.slice(Math.max(0, i - window + 1), i + 1)));
}

/** Each player's average score per weekday (index 0 = Monday), null where unplayed. */
export function averageByWeekday(games) {
  const result = new Map();
  for (const [playerId, playerGames] of groupBy(games, (g) => g.playerId)) {
    const byDay = groupBy(playerGames, (g) => weekday(g.date));
    result.set(playerId, Array.from({ length: 7 }, (_, d) => mean((byDay.get(d) ?? []).map((g) => g.score))));
  }
  return result;
}

const ROUND_METRICS = {
  average: (scores) => mean(scores),
  fiveKRate: (scores) => (100 * scores.filter((s) => s === PERFECT_ROUND).length) / scores.length,
  blunderRate: (scores) => (100 * scores.filter((s) => s < BLUNDER_ROUND).length) / scores.length,
};

/** Per player, a metric for round 1 through 5 from games with round data. */
export function byRound(games, metric = "average") {
  const result = new Map();
  for (const [playerId, playerGames] of groupBy(games, (g) => g.playerId)) {
    const tracked = playerGames.filter((g) => g.rounds);
    if (!tracked.length) continue;
    result.set(
      playerId,
      Array.from({ length: ROUNDS_PER_GAME }, (_, i) => ROUND_METRICS[metric](tracked.map((g) => g.rounds[i]))),
    );
  }
  return result;
}

export const ROUND_BUCKETS = [
  { label: "<1k", min: 0, max: 999 },
  { label: "1–2k", min: 1000, max: 1999 },
  { label: "2–3k", min: 2000, max: 2999 },
  { label: "3–4k", min: 3000, max: 3999 },
  { label: "4–4.5k", min: 4000, max: 4499 },
  { label: "4.5–4.9k", min: 4500, max: 4899 },
  { label: "4.9k+", min: 4900, max: 4999 },
  { label: "5K", min: 5000, max: 5000 },
];

/** Share (percent) of each player's tracked rounds landing in each ROUND_BUCKETS bucket. */
export function roundHistogram(games) {
  const result = new Map();
  for (const [playerId, playerGames] of groupBy(games, (g) => g.playerId)) {
    const rounds = playerGames.flatMap((g) => g.rounds ?? []);
    if (!rounds.length) continue;
    result.set(
      playerId,
      ROUND_BUCKETS.map((b) => (100 * rounds.filter((s) => s >= b.min && s <= b.max).length) / rounds.length),
    );
  }
  return result;
}

/** Keyed "a|b": how often a beat, lost to, and tied b on days both played. */
export function headToHead(daily) {
  const records = new Map();
  for (const day of daily) {
    for (const a of day.ranked) {
      for (const b of day.ranked) {
        if (a === b) continue;
        const key = `${a.playerId}|${b.playerId}`;
        const rec = records.get(key) ?? { wins: 0, losses: 0, ties: 0, shared: 0 };
        rec.shared += 1;
        if (a.score > b.score) rec.wins += 1;
        else if (a.score < b.score) rec.losses += 1;
        else rec.ties += 1;
        records.set(key, rec);
      }
    }
  }
  return records;
}

/** Multiplayer Elo: each contested day is a round robin of pairwise results, applied at once. */
export function eloHistory(daily, k = 32, start = 1500) {
  const ratings = new Map();
  const history = new Map();
  for (const day of daily.filter((d) => d.contested)) {
    for (const g of day.ranked) if (!ratings.has(g.playerId)) ratings.set(g.playerId, start);
    const scale = k / (day.ranked.length - 1);
    const deltas = day.ranked.map((a) =>
      sum(
        day.ranked
          .filter((b) => b !== a)
          .map((b) => {
            const expected = 1 / (1 + 10 ** ((ratings.get(b.playerId) - ratings.get(a.playerId)) / 400));
            const actual = a.score > b.score ? 1 : a.score === b.score ? 0.5 : 0;
            return scale * (actual - expected);
          }),
      ),
    );
    day.ranked.forEach((g, i) => {
      ratings.set(g.playerId, ratings.get(g.playerId) + deltas[i]);
      if (!history.has(g.playerId)) history.set(g.playerId, []);
      history.get(g.playerId).push([day.date, ratings.get(g.playerId)]);
    });
  }
  return history;
}

const pickBy = (items, valueOf, better) =>
  items.reduce((best, item) => (best == null || better(valueOf(item), valueOf(best)) ? item : best), null);
const highest = (items, valueOf) => pickBy(items, valueOf, (a, b) => a > b);
const lowest = (items, valueOf) => pickBy(items, valueOf, (a, b) => a < b);

/** Hall of Fame entries; each names a player, a value, and an optional date. */
export function records(games, daily, stats) {
  const contested = daily.filter((d) => d.contested);
  const withRounds = games.filter((g) => g.rounds);
  const rounds = withRounds.flatMap((g) => g.rounds.map((score, i) => ({ ...g, roundScore: score, round: i + 1 })));
  const steady = stats.filter((s) => s.games >= 5);
  const best = highest(games, (g) => g.score);
  const worst = lowest(games, (g) => g.score);
  const blowout = highest(contested, (d) => d.margin);
  const photo = lowest(contested, (d) => d.margin);
  const streak = highest(stats, (s) => s.streak.longest);
  const fiveKGame = highest(withRounds, (g) => g.rounds.filter((s) => s === PERFECT_ROUND).length);
  const disaster = lowest(rounds, (r) => r.roundScore);
  const steadiest = lowest(steady, (s) => s.stdev);
  const wanderer = highest(stats.filter((s) => s.totalKm), (s) => s.totalKm);
  const ironman = highest(stats, (s) => s.games);

  return [
    best && { id: "best", title: "Summit", blurb: "Highest single-day score", value: best.score, playerId: best.playerId, date: best.date },
    worst && { id: "worst", title: "Mariana Trench", blurb: "Lowest single-day score", value: worst.score, playerId: worst.playerId, date: worst.date },
    blowout && { id: "blowout", title: "Landslide", blurb: "Biggest winning margin", value: blowout.margin, playerId: blowout.winners[0], date: blowout.date, prefix: "+" },
    photo && { id: "photo", title: "Photo Finish", blurb: "Narrowest winning margin", value: photo.margin, playerId: photo.winners[0], date: photo.date, prefix: "+" },
    streak?.streak.longest && { id: "streak", title: "Conqueror", blurb: "Longest win streak (days)", value: streak.streak.longest, playerId: streak.playerId, date: streak.streak.longestEnd, datePrefix: "ended" },
    fiveKGame && { id: "fivek", title: "Sharpshooter", blurb: "Most 5ks in one game", value: fiveKGame.rounds.filter((s) => s === PERFECT_ROUND).length, playerId: fiveKGame.playerId, date: fiveKGame.date, suffix: " / 5" },
    disaster && { id: "disaster", title: "Lost at Sea", blurb: `Worst single round (round ${disaster.round})`, value: disaster.roundScore, playerId: disaster.playerId, date: disaster.date },
    steadiest && { id: "steady", title: "Steady Compass", blurb: "Most consistent (lowest spread, 5+ games)", value: Math.round(steadiest.stdev), playerId: steadiest.playerId, prefix: "±" },
    wanderer && { id: "wander", title: "Globetrotter", blurb: `Total km off target · ${(wanderer.totalKm / EARTH_CIRCUMFERENCE_KM).toFixed(1)}× around Earth`, value: Math.round(wanderer.totalKm), playerId: wanderer.playerId, suffix: " km" },
    ironman && { id: "iron", title: "Iron Explorer", blurb: "Most daily challenges played", value: ironman.games, playerId: ironman.playerId },
  ].filter(Boolean);
}

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  byRound,
  dailyResults,
  eloHistory,
  filterGames,
  headToHead,
  listPlayers,
  parseCsv,
  playerStats,
  records,
  rollingMean,
  roundHistogram,
  toGames,
  weekday,
  winStreaks,
} from "../../site/js/stats.js";

const HEADER = "challenge_date,challenge_token,player_id,player_name,total_score,total_time_seconds,total_distance,scraped_at,round_scores";

function csv(...rows) {
  return [HEADER, ...rows].join("\n") + "\n";
}

// Mon 2026-11-02 .. Sun 2026-11-08
const SAMPLE = csv(
  "2026-11-02,t1,a,Ann,20000,900,500000,2026-11-02T10:00:00+00:00,5000;5000;4000;3000;3000",
  "2026-11-02,t1,b,Bob,18000,,,2026-11-02T10:00:00+00:00,",
  "2026-11-03,t2,a,Ann,15000,,,2026-11-03T10:00:00+00:00,",
  "2026-11-03,t2,b,Bob,21000,,,2026-11-03T10:00:00+00:00,",
  "2026-11-04,t3,a,Ann,19000,,,2026-11-04T10:00:00+00:00,",
  "2026-11-04,t3,b,Bob,19000,,,2026-11-04T10:00:00+00:00,",
  "2026-11-05,t4,a,Annie,22000,,,2026-11-05T10:00:00+00:00,",
  "2026-11-07,t5,b,Bob,10000,,,2026-11-07T10:00:00+00:00,500;2000;2500;0;5000",
);

const games = () => toGames(parseCsv(SAMPLE));

test("parseCsv handles quoted fields with commas, quotes, and CRLF", () => {
  const rows = parseCsv('name,score\r\n"Smith, ""Ace""",10\r\nplain,2\r\n');
  assert.deepEqual(rows, [
    { name: 'Smith, "Ace"', score: "10" },
    { name: "plain", score: "2" },
  ]);
});

test("toGames types numbers, converts meters to km, and keeps only full round lists", () => {
  const [first, second] = games();
  assert.equal(first.score, 20000);
  assert.equal(first.distanceKm, 500);
  assert.deepEqual(first.rounds, [5000, 5000, 4000, 3000, 3000]);
  assert.equal(second.timeSeconds, null);
  assert.equal(second.rounds, null);
});

test("listPlayers orders by first appearance and uses the latest nickname", () => {
  assert.deepEqual(listPlayers(games()), [
    { id: "a", name: "Annie", index: 0 },
    { id: "b", name: "Bob", index: 1 },
  ]);
});

test("weekday is Monday-based in UTC", () => {
  assert.equal(weekday("2026-11-02"), 0);
  assert.equal(weekday("2026-11-08"), 6);
});

test("filterGames applies date range, weekends, and players", () => {
  const all = games();
  assert.equal(filterGames(all, { includeWeekends: false }).length, 7);
  assert.equal(filterGames(all, { from: "2026-11-04", to: "2026-11-05" }).length, 3);
  assert.equal(filterGames(all, { playerIds: new Set(["b"]) }).length, 4);
});

test("fairFight keeps only days every remaining player played", () => {
  const dates = new Set(filterGames(games(), { fairFight: true }).map((g) => g.date));
  assert.deepEqual([...dates], ["2026-11-02", "2026-11-03", "2026-11-04"]);
});

test("dailyResults ranks each day, shares ties, and leaves solo days uncontested", () => {
  const daily = dailyResults(games());
  assert.deepEqual(daily.map((d) => d.date), ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-07"]);
  assert.deepEqual(daily[0].winners, ["a"]);
  assert.equal(daily[0].margin, 2000);
  assert.deepEqual(daily[2].winners.sort(), ["a", "b"]);
  assert.equal(daily[2].margin, 0);
  assert.equal(daily[3].contested, false);
  assert.deepEqual(daily[3].winners, []);
});

test("playerStats counts wins only on contested days", () => {
  const [ann, bob] = playerStats(games());
  assert.equal(ann.playerId, "a");
  assert.equal(ann.games, 4);
  assert.equal(ann.average, 19000);
  assert.equal(ann.wins, 2);
  assert.equal(ann.contested, 3);
  assert.equal(ann.fiveKs, 2);
  assert.equal(ann.fiveKRate, 0.4);
  assert.equal(ann.kmPerRound, 100);
  assert.equal(bob.wins, 2);
  assert.equal(bob.worst, 10000);
});

test("winStreaks tracks longest and current runs", () => {
  const streaks = winStreaks(dailyResults(games()));
  assert.deepEqual(streaks.get("b"), { current: 2, longest: 2, longestEnd: "2026-11-04" });
  assert.deepEqual(streaks.get("a"), { current: 1, longest: 1, longestEnd: "2026-11-02" });
});

test("rollingMean averages over a trailing window", () => {
  assert.deepEqual(rollingMean([2, 4, 6, 8], 2), [2, 3, 5, 7]);
});

test("headToHead records wins, losses, and ties for each ordered pair", () => {
  const records = headToHead(dailyResults(games()));
  assert.deepEqual(records.get("a|b"), { wins: 1, losses: 1, ties: 1, shared: 3 });
  assert.deepEqual(records.get("b|a"), { wins: 1, losses: 1, ties: 1, shared: 3 });
});

test("eloHistory is zero-sum and skips solo days", () => {
  const history = eloHistory(dailyResults(games()), 32);
  const finalA = history.get("a").at(-1)[1];
  const finalB = history.get("b").at(-1)[1];
  assert.equal(history.get("a").length, 3);
  assert.ok(Math.abs(finalA + finalB - 3000) < 1e-9);
  assert.ok(history.get("a")[0][1] > 1500);
});

test("byRound and roundHistogram summarize tracked rounds", () => {
  const all = games();
  assert.deepEqual(byRound(all, "average").get("a"), [5000, 5000, 4000, 3000, 3000]);
  assert.deepEqual(byRound(all, "blunderRate").get("b"), [100, 0, 0, 100, 0]);
  const bob = roundHistogram(all).get("b");
  assert.equal(bob[0], 40);
  assert.equal(bob.at(-1), 20);
});

test("records names the standout games", () => {
  const all = games();
  const daily = dailyResults(all);
  const byId = Object.fromEntries(records(all, daily, playerStats(all, daily)).map((r) => [r.id, r]));
  assert.equal(byId.best.value, 22000);
  assert.equal(byId.worst.playerId, "b");
  assert.equal(byId.blowout.value, 6000);
  assert.equal(byId.photo.value, 0);
  assert.equal(byId.disaster.value, 0);
  assert.equal(byId.fivek.value, 2);
});

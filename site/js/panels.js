// HTML (non-chart) views: KPI tiles, the leaderboard table, and the Hall of Fame stamps.

import { eloHistory, records } from "./stats.js";
import { escapeHtml, fmt } from "./charts.js";

const pct = (rate) => `${fmt(rate * 100)}%`;

const pin = (player) =>
  `<span class="pin" style="--pin:${player.color}"></span><span class="who">${escapeHtml(player.name)}</span>`;

const shortDate = (date) =>
  new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

function sparkline(values, color, [lo, hi]) {
  if (values.length < 2) return "";
  const w = 120;
  const h = 28;
  const x = (i) => (i / (values.length - 1)) * w;
  const y = (v) => h - 2 - ((v - lo) / Math.max(1, hi - lo)) * (h - 4);
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = values.length - 1;
  return (
    `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">` +
    `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round"/>` +
    `<circle cx="${x(last)}" cy="${y(values[last])}" r="2.8" fill="${color}"/></svg>`
  );
}

export const LEADERBOARD_COLUMNS = [
  { key: "average", label: "Avg", value: (s) => s.average, render: (s) => fmt(s.average) },
  { key: "median", label: "Median", value: (s) => s.median, render: (s) => fmt(s.median) },
  { key: "best", label: "Best", value: (s) => s.best, render: (s) => fmt(s.best) },
  { key: "worst", label: "Worst", value: (s) => s.worst, render: (s) => fmt(s.worst) },
  { key: "stdev", label: "Spread", value: (s) => -s.stdev, render: (s) => `±${fmt(s.stdev)}`, title: "Standard deviation (lower is steadier)" },
  { key: "wins", label: "Wins", value: (s) => s.wins, render: (s) => `${s.wins}<small>/${s.contested}</small>`, title: "Days won out of days with at least one rival" },
  { key: "winRate", label: "Win %", value: (s) => s.winRate, render: (s) => pct(s.winRate) },
  { key: "fiveKs", label: "5ks", value: (s) => s.fiveKs, render: (s) => (s.roundsTracked ? `${s.fiveKs}<small> · ${pct(s.fiveKRate)}</small>` : "–"), title: "Perfect rounds (only days with round data)" },
  { key: "kmPerRound", label: "km/guess", value: (s) => -(s.kmPerRound ?? Infinity), render: (s) => fmt(s.kmPerRound), title: "Average distance off per guess (tracked games)" },
  { key: "elo", label: "Elo", value: (s) => s.elo ?? 0, render: (s) => fmt(s.elo), title: "Power rating from daily head-to-head results" },
  { key: "games", label: "Games", value: (s) => s.games, render: (s) => s.games },
];

export function leaderboardHtml(ctx, sort) {
  const elo = eloHistory(ctx.daily);
  const rows = ctx.stats.map((s) => ({ ...s, elo: elo.get(s.playerId)?.at(-1)?.[1] ?? null }));
  const column = LEADERBOARD_COLUMNS.find((c) => c.key === sort.key) ?? LEADERBOARD_COLUMNS[0];
  rows.sort((a, b) => sort.dir * (column.value(a) - column.value(b)));
  const recent = rows.flatMap((r) => r.recent);
  const domain = [Math.min(...recent), 25000];
  const medals = ["🥇", "🥈", "🥉"];

  const head = LEADERBOARD_COLUMNS.map(
    (c) =>
      `<th class="num ${c.key === column.key ? "sorted" : ""}" title="${c.title ?? ""}">` +
      `<button data-sort="${c.key}">${c.label}${c.key === column.key ? (sort.dir < 0 ? " ▾" : " ▴") : ""}</button></th>`,
  ).join("");
  const body = rows
    .map((s, i) => {
      const player = ctx.playerById.get(s.playerId);
      return (
        `<tr style="--pin:${player.color}"><td class="rank">${medals[i] ?? i + 1}</td>` +
        `<td class="player">${pin(player)}</td><td>${sparkline(s.recent, player.color, domain)}</td>` +
        LEADERBOARD_COLUMNS.map((c) => `<td class="num ${c.key === column.key ? "sorted" : ""}">${c.render(s)}</td>`).join("") +
        `</tr>`
      );
    })
    .join("");
  return (
    `<div class="table-wrap"><table class="leaderboard"><thead><tr><th></th><th>Explorer</th><th>Form (last 20)</th>${head}</tr></thead>` +
    `<tbody>${body}</tbody></table></div>`
  );
}

export function hallOfFameHtml(ctx) {
  const stamps = records(ctx.games, ctx.daily, ctx.stats).map((r, i) => {
    const player = ctx.playerById.get(r.playerId);
    const date = r.date ? `<div class="stamp-date">${r.datePrefix ?? ""} ${shortDate(r.date)}</div>` : "";
    return (
      `<article class="stamp" style="--pin:${player.color};--tilt:${((i * 37) % 7) - 3}deg">` +
      `<div class="stamp-inner"><div class="stamp-title">${r.title}</div>` +
      `<div class="stamp-value">${r.prefix ?? ""}${fmt(r.value)}<small>${r.suffix ?? ""}</small></div>` +
      `<div class="stamp-blurb">${escapeHtml(r.blurb)}</div>` +
      `<div class="stamp-who">${pin(player)}</div>${date}</div></article>`
    );
  });
  return `<div class="stamps">${stamps.join("")}</div>`;
}

function tile(label, player, value, note) {
  if (!player) return `<div class="kpi"><div class="kpi-label">${label}</div><div class="kpi-value">–</div></div>`;
  return (
    `<div class="kpi" style="--pin:${player.color}"><div class="kpi-label">${label}</div>` +
    `<div class="kpi-value">${value}</div><div class="kpi-who">${pin(player)}<span class="kpi-note">${note}</span></div></div>`
  );
}

export function kpisHtml(ctx) {
  const top = (valueOf, filter = () => true) =>
    ctx.stats.filter(filter).reduce((best, s) => (!best || valueOf(s) > valueOf(best) ? s : best), null);
  const champ = top((s) => s.wins);
  const avg = top((s) => s.average, (s) => s.games >= 3) ?? top((s) => s.average);
  const hot = top((s) => s.streak.current);
  const sniper = top((s) => s.fiveKs);
  const who = (s) => s && ctx.playerById.get(s.playerId);
  return [
    tile("Reigning champ", who(champ), champ?.wins ?? 0, "days won"),
    tile("Top average", who(avg), fmt(avg?.average), `over ${avg?.games ?? 0} games`),
    tile("On fire", hot?.streak.current ? who(hot) : null, hot?.streak.current ?? 0, "wins in a row"),
    tile("5k sniper", sniper?.fiveKs ? who(sniper) : null, sniper?.fiveKs ?? 0, "perfect rounds"),
  ].join("");
}

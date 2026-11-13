// Dashboard wiring: load scores.csv, hold filter state, and render the selected view.

import { dailyResults, filterGames, gamesByPlayer, groupBy, listPlayers, parseCsv, playerStats, shiftDate, toGames } from "./stats.js";
import * as charts from "./charts.js";
import { hallOfFameHtml, kpisHtml, leaderboardHtml } from "./panels.js";
import { ATLAS_THEME, playerColor } from "./theme.js";

const VIEWS = [
  { id: "standings", group: "The Board", icon: "▲", title: "Standings", plain: "Leaderboard", blurb: "Everyone's numbers side by side. Click a column to re-rank the expedition.", panel: leaderboardHtml },
  { id: "fame", group: "The Board", icon: "✦", title: "Hall of Fame", plain: "Records", blurb: "Personal bests, worst disasters, and other moments for the history books.", panel: hallOfFameHtml },
  { id: "trails", group: "Over Time", icon: "〰", title: "Score Trails", plain: "Scores over time", blurb: "Daily totals for each explorer. Slide the smoothing knob to see form instead of noise. Scroll or drag to zoom.", chart: charts.trailsOption, knobs: ["window"] },
  { id: "power", group: "Over Time", icon: "⚡", title: "Power Rankings", plain: "Elo rating", blurb: "A chess-style rating: beat someone rated higher and you climb faster. Every shared day is a round-robin.", chart: charts.powerOption, knobs: ["k"] },
  { id: "calendar", group: "Over Time", icon: "▦", title: "Conquest Map", plain: "Daily winners calendar", blurb: "Who claimed each day. Brighter tiles mean a bigger winning margin.", chart: charts.calendarOption, needsContest: true },
  { id: "margins", group: "Over Time", icon: "⇕", title: "Photo Finish", plain: "Winning margins", blurb: "How far ahead the day's winner finished. Tall bars are blowouts, stubs are nail-biters.", chart: charts.marginsOption, needsContest: true },
  { id: "rivalries", group: "Matchups", icon: "⚔", title: "Border Disputes", plain: "Head-to-head", blurb: "How often each row beat each column on days both played (ties count half).", chart: charts.rivalriesOption, needsContest: true },
  { id: "terrain", group: "Deep Dives", icon: "⛰", title: "Score Terrain", plain: "Score spread", blurb: "Each dot is a game. Boxes span the middle half of a player's scores, the line is their median.", chart: charts.terrainOption },
  { id: "tides", group: "Deep Dives", icon: "☾", title: "Weekly Tides", plain: "By day of week", blurb: "Average score by weekday. Monday brain fog, or Friday focus?", chart: charts.tidesOption },
  { id: "rounds", group: "Deep Dives", icon: "⑤", title: "Round Report", plain: "Rounds 1 to 5", blurb: "Per-round performance from days with round data. Switch the metric to hunt 5ks or blunders.", chart: charts.roundsOption, knobs: ["metric"] },
  { id: "bullseye", group: "Deep Dives", icon: "◎", title: "Bullseye Board", plain: "Round score spread", blurb: "Where every tracked round landed. The gold bucket is perfect 5000s.", chart: charts.bullseyeOption },
];

const KNOBS = {
  window: { label: "Smoothing", type: "range", min: 1, max: 15, show: (v) => (v === 1 ? "raw" : `${v}-game avg`) },
  k: { label: "Volatility (K)", type: "range", min: 8, max: 64, step: 8, show: (v) => `K = ${v}` },
  metric: { label: "Metric", type: "segmented", options: Object.entries(charts.ROUND_METRIC_LABELS).map(([value, m]) => [value, m.label]) },
};

const RANGES = [
  ["7", "7D"],
  ["30", "30D"],
  ["90", "90D"],
  ["all", "All"],
];

const state = {
  view: VIEWS.some((v) => v.id === location.hash.slice(1)) ? location.hash.slice(1) : "standings",
  range: "all",
  includeWeekends: false,
  fairFight: false,
  hidden: new Set(),
  knobs: { window: 3, k: 32, metric: "average" },
  sort: { key: "average", dir: -1 },
};

const $ = (selector) => document.querySelector(selector);
let allGames = [];
let players = [];
let chart = null;

async function loadCsv() {
  // Deployed, scores.csv sits beside index.html; locally the repo root is one level up.
  for (const url of ["scores.csv", "../scores.csv"]) {
    const response = await fetch(url, { cache: "no-cache" });
    if (response.ok) return response.text();
  }
  throw new Error("Couldn't find scores.csv");
}

function buildContext() {
  const latest = allGames.reduce((max, g) => (g.date > max ? g.date : max), "");
  const from = state.range === "all" ? null : shiftDate(latest, 1 - Number(state.range));
  const shown = players.filter((p) => !state.hidden.has(p.id));
  const games = filterGames(allGames, {
    from,
    includeWeekends: state.includeWeekends,
    playerIds: new Set(shown.map((p) => p.id)),
    fairFight: state.fairFight,
  });
  const daily = dailyResults(games);
  const playerById = new Map(players.map((p) => [p.id, p]));
  const byPlayer = gamesByPlayer(games);
  return {
    games,
    daily,
    byPlayer,
    playerById,
    players: shown.filter((p) => byPlayer.has(p.id)),
    stats: playerStats(games, daily),
    includeWeekends: state.includeWeekends,
    colorOf: (id) => playerById.get(id).color,
    nameOf: (id) => playerById.get(id).name,
  };
}

function renderNav() {
  const groups = groupBy(VIEWS, (v) => v.group);
  $("#nav").innerHTML = [...groups]
    .map(
      ([group, views]) =>
        `<div class="nav-group"><div class="nav-heading">${group}</div>` +
        views
          .map(
            (v) =>
              `<button class="nav-item ${v.id === state.view ? "active" : ""}" data-view="${v.id}" aria-current="${v.id === state.view}">` +
              `<span class="nav-icon">${v.icon}</span><span class="nav-text"><b>${v.title}</b><small>${v.plain}</small></span></button>`,
          )
          .join("") +
        `</div>`,
    )
    .join("");
}

function renderFilters(ctx) {
  $("#ranges").innerHTML = RANGES.map(
    ([value, label]) => `<button class="seg ${state.range === value ? "on" : ""}" data-range="${value}">${label}</button>`,
  ).join("");
  $("#weekends").checked = state.includeWeekends;
  $("#fair").checked = state.fairFight;
  $("#players").innerHTML = players
    .map(
      (p) =>
        `<button class="chip ${state.hidden.has(p.id) ? "off" : ""}" data-player="${p.id}" style="--pin:${p.color}" aria-pressed="${!state.hidden.has(p.id)}">` +
        `<span class="pin"></span>${charts.escapeHtml(p.name)}</button>`,
    )
    .join("");
  const days = ctx.daily.length;
  $("#scope").textContent = `${days} day${days === 1 ? "" : "s"} · ${ctx.games.length} games in view`;
}

function renderKnobs(view) {
  $("#knobs").innerHTML = (view.knobs ?? [])
    .map((id) => {
      const knob = KNOBS[id];
      const value = state.knobs[id];
      if (knob.type === "range") {
        return (
          `<label class="knob"><span>${knob.label}</span>` +
          `<input type="range" data-knob="${id}" min="${knob.min}" max="${knob.max}" step="${knob.step ?? 1}" value="${value}">` +
          `<output>${knob.show(value)}</output></label>`
        );
      }
      return (
        `<div class="knob"><span>${knob.label}</span><div class="segmented">` +
        knob.options.map(([v, label]) => `<button class="seg ${v === value ? "on" : ""}" data-knob="${id}" data-value="${v}">${label}</button>`).join("") +
        `</div></div>`
      );
    })
    .join("");
}

function emptyMessage(view, ctx) {
  if (!ctx.games.length) return "No expeditions match these filters. Widen the date range or bring a player back.";
  if (view.needsContest && !ctx.daily.some((d) => d.contested)) return "This one needs at least two explorers on the same day.";
  return null;
}

// keepKnobs skips rebuilding the knob controls so a slider isn't replaced mid-drag.
function render({ keepKnobs = false } = {}) {
  const view = VIEWS.find((v) => v.id === state.view);
  const ctx = buildContext();
  renderNav();
  renderFilters(ctx);
  if (!keepKnobs) renderKnobs(view);
  $("#kpis").innerHTML = kpisHtml(ctx);
  $("#view-icon").textContent = view.icon;
  $("#view-title").textContent = view.title;
  $("#view-plain").textContent = view.plain;
  $("#view-blurb").textContent = view.blurb;

  const empty = emptyMessage(view, ctx);
  const panel = $("#panel");
  const chartEl = $("#chart");
  chartEl.hidden = Boolean(empty || view.panel);
  panel.hidden = !chartEl.hidden;
  if (empty) panel.innerHTML = `<div class="empty"><div class="empty-icon">🧭</div>${empty}</div>`;
  else if (view.panel) panel.innerHTML = view.panel(ctx, state.sort);
  else {
    try {
      chart ??= echarts.init(chartEl, "atlas", { renderer: "canvas" });
      chart.resize();
      const option = view.chart(ctx, state.knobs);
      if (chartEl.clientWidth < 600) charts.compact(option);
      chart.setOption({ animationDuration: 700, animationEasing: "cubicOut", ...option }, { notMerge: true });
    } catch (err) {
      // A broken option can leave ECharts half-initialized; start fresh next time.
      console.error(err);
      chart?.dispose();
      chart = null;
      chartEl.hidden = true;
      panel.hidden = false;
      panel.innerHTML = `<div class="empty"><div class="empty-icon">🌀</div>This chart got lost at sea. Try another view.</div>`;
    }
  }
}

function setView(id) {
  state.view = id;
  history.replaceState(null, "", `#${id}`);
  render();
  $("#canvas").focus({ preventScroll: true });
}

function bindEvents() {
  $("#nav").addEventListener("click", (e) => {
    const button = e.target.closest("[data-view]");
    if (button) setView(button.dataset.view);
  });
  $("#ranges").addEventListener("click", (e) => {
    const button = e.target.closest("[data-range]");
    if (button) (state.range = button.dataset.range), render();
  });
  $("#players").addEventListener("click", (e) => {
    const id = e.target.closest("[data-player]")?.dataset.player;
    if (!id) return;
    state.hidden.has(id) ? state.hidden.delete(id) : state.hidden.add(id);
    render();
  });
  $("#weekends").addEventListener("change", (e) => ((state.includeWeekends = e.target.checked), render()));
  $("#fair").addEventListener("change", (e) => ((state.fairFight = e.target.checked), render()));
  $("#knobs").addEventListener("input", (e) => {
    if (e.target.type !== "range") return;
    const id = e.target.dataset.knob;
    state.knobs[id] = Number(e.target.value);
    e.target.nextElementSibling.textContent = KNOBS[id].show(state.knobs[id]);
    render({ keepKnobs: true });
  });
  $("#knobs").addEventListener("click", (e) => {
    const button = e.target.closest("button[data-knob]");
    if (button) (state.knobs[button.dataset.knob] = button.dataset.value), render();
  });
  $("#panel").addEventListener("click", (e) => {
    const key = e.target.closest("[data-sort]")?.dataset.sort;
    if (!key) return;
    state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : -1 };
    render();
  });
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    // j/k work anywhere; arrow keys only while the sidebar has focus.
    const inNav = Boolean(e.target.closest("#nav"));
    const step = { j: 1, k: -1, ...(inNav && { ArrowDown: 1, ArrowUp: -1 }) }[e.key];
    if (!step) return;
    const index = VIEWS.findIndex((v) => v.id === state.view);
    e.preventDefault();
    setView(VIEWS[(index + step + VIEWS.length) % VIEWS.length].id);
  });
  window.addEventListener("hashchange", () => {
    const id = location.hash.slice(1);
    if (id !== state.view && VIEWS.some((v) => v.id === id)) setView(id);
  });
  new ResizeObserver(() => chart?.resize()).observe($("#chart"));
  // A playful touch: the header reads the pointer as map coordinates.
  document.addEventListener("pointermove", (e) => {
    const lat = 90 - (e.clientY / innerHeight) * 180;
    const lon = (e.clientX / innerWidth) * 360 - 180;
    $("#coords").textContent = `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? "N" : "S"}  ${Math.abs(lon).toFixed(2)}°${lon >= 0 ? "E" : "W"}`;
  });
}

async function main() {
  echarts.registerTheme("atlas", ATLAS_THEME);
  bindEvents();
  try {
    allGames = toGames(parseCsv(await loadCsv()));
  } catch (err) {
    $("#panel").innerHTML = `<div class="empty"><div class="empty-icon">🗺️</div>Couldn't load scores.csv (${charts.escapeHtml(err.message)}).</div>`;
    return;
  }
  players = listPlayers(allGames).map((p) => ({ ...p, color: playerColor(p.index) }));
  const latest = allGames.reduce((max, g) => (g.scrapedAt > max ? g.scrapedAt : max), "");
  $("#updated").textContent = latest ? new Date(latest).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" }) : "–";
  $("#explorers").textContent = players.length;
  document.body.classList.remove("loading");
  render();
}

main();

// ECharts option builders, one per chart view. Each takes the filtered context plus its knobs.

import {
  ROUND_BUCKETS,
  ROUNDS_PER_GAME,
  averageByWeekday,
  byRound,
  eloHistory,
  headToHead,
  quantile,
  rollingMean,
  roundHistogram,
} from "./stats.js";
import { DIVERGING, FONT_DISPLAY, FONT_MONO, INK } from "./theme.js";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const fmt = (n, digits = 0) =>
  n == null ? "–" : Number(n).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const escapeHtml = (text) =>
  String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

const swatch = (color) =>
  `<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${color};margin-right:8px;box-shadow:0 0 8px ${color}"></span>`;

const tipRow = (color, label, value) =>
  `<div style="display:flex;justify-content:space-between;gap:18px">` +
  `<span>${swatch(color)}${escapeHtml(label)}</span><b>${value}</b></div>`;

const tipTitle = (text) => `<div style="color:${INK.brass};margin-bottom:6px;letter-spacing:.06em">${text}</div>`;

const prettyDate = (date) =>
  new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });

// ECharts reads "YYYY-MM-DD" as local midnight, so convert axis values back the same way.
const localIsoDate = (ms) => {
  const d = new Date(ms);
  return [d.getFullYear(), d.getMonth() + 1, d.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
};

// Let ECharts pick nice bounds; fixed min/max made edge labels collide.
const SCORE_AXIS = { type: "value", scale: true };

const GRID = { left: 56, right: 150, top: 64, bottom: 64, containLabel: false };
const LEGEND = { top: 0, left: 0 };

/** Axis tooltip listing the series that have a point on the hovered date, best first. */
function rankedAxisTooltip(valueFormat) {
  return {
    trigger: "axis",
    formatter: (params) => {
      const date = localIsoDate(params[0].axisValue);
      const rows = params
        .filter((p) => p.value?.[0] === date)
        .sort((a, b) => b.value[1] - a.value[1])
        .map((p) => tipRow(p.color, p.seriesName, valueFormat(p.value[1])));
      return tipTitle(prettyDate(date)) + rows.join("");
    },
  };
}

function glowLine(player, data, extra = {}) {
  return {
    name: player.name,
    type: "line",
    data,
    color: player.color,
    symbol: "circle",
    symbolSize: 8,
    lineStyle: { width: 2, shadowColor: player.color, shadowBlur: 10 },
    itemStyle: { borderColor: INK.surface, borderWidth: 2 },
    emphasis: { focus: "series", lineStyle: { width: 3 } },
    endLabel: { show: true, formatter: player.name, color: player.color, fontFamily: FONT_DISPLAY, fontWeight: 600, distance: 8 },
    labelLayout: { moveOverlap: "shiftY" },
    ...extra,
  };
}

const zoom = [{ type: "inside" }, { type: "slider", height: 18, bottom: 14 }];

export function trailsOption(ctx, { window }) {
  const smoothed = window > 1;
  const series = ctx.players.map((p) => {
    const games = ctx.byPlayer.get(p.id) ?? [];
    const values = rollingMean(games.map((g) => g.score), window);
    return glowLine(p, games.map((g, i) => [g.date, Math.round(values[i])]), {
      smooth: smoothed ? 0.35 : false,
      showSymbol: !smoothed,
    });
  });
  return {
    legend: LEGEND,
    grid: GRID,
    tooltip: rankedAxisTooltip(fmt),
    xAxis: { type: "time" },
    yAxis: SCORE_AXIS,
    dataZoom: zoom,
    series,
  };
}

export function powerOption(ctx, { k }) {
  const history = eloHistory(ctx.daily, k);
  const series = ctx.players
    .filter((p) => history.has(p.id))
    .map((p) => glowLine(p, history.get(p.id).map(([d, r]) => [d, Math.round(r)]), { step: false, smooth: 0.2, showSymbol: false }));
  if (series.length) {
    series[0].markLine = {
      silent: true,
      symbol: "none",
      lineStyle: { color: INK.muted, type: "dotted" },
      label: { formatter: "start 1500", color: INK.muted, fontFamily: FONT_MONO, position: "insideStartTop" },
      data: [{ yAxis: 1500 }],
    };
  }
  return {
    legend: LEGEND,
    grid: GRID,
    tooltip: rankedAxisTooltip((v) => fmt(v)),
    xAxis: { type: "time" },
    yAxis: { type: "value", scale: true, name: "rating", nameLocation: "end" },
    dataZoom: zoom,
    series,
  };
}

// Empty line series give a legend entry per player without reserving bar slots.
const legendOnly = (entries, extra = {}) =>
  entries.map(({ name, color }) => ({ name, color, type: "line", data: [], silent: true, ...extra }));

export function calendarOption(ctx) {
  const contested = ctx.daily.filter((d) => d.contested);
  const maxMargin = Math.max(1, ...contested.map((d) => d.margin));
  const byDate = new Map(ctx.daily.map((d) => [d.date, d]));
  const tileColor = (d) =>
    !d.contested ? "#4A5878" : d.winners.length > 1 ? "#FFFFFF" : ctx.colorOf(d.winners[0]);

  // Rounded tile filling each calendar cell; brighter when the margin was bigger.
  const renderTile = (params, api) => {
    const day = ctx.daily[params.dataIndex];
    const [x, y] = api.coord(api.value(0));
    const { cellWidth, cellHeight } = params.coordSys;
    const side = Math.max(4, Math.min(cellWidth, cellHeight) - 6) * (day.contested ? 1 : 0.4);
    const color = tileColor(day);
    return {
      type: "rect",
      shape: { x: x - side / 2, y: y - side / 2, width: side, height: side, r: Math.min(6, side / 4) },
      style: {
        fill: color,
        opacity: day.contested ? 0.4 + 0.6 * Math.sqrt(day.margin / maxMargin) : 1,
        shadowBlur: day.contested ? 10 : 0,
        shadowColor: color,
      },
    };
  };

  return {
    legend: { ...LEGEND, selectedMode: false },
    tooltip: {
      formatter: (p) => {
        const day = byDate.get(p.value[0]);
        if (!day) return "";
        const rows = day.ranked.map((g, i) => tipRow(ctx.colorOf(g.playerId), `${i + 1}. ${ctx.nameOf(g.playerId)}`, fmt(g.score)));
        const note = day.contested ? `margin +${fmt(day.margin)}` : "solo day, no contest";
        return tipTitle(prettyDate(day.date)) + rows.join("") + `<div style="color:${INK.muted};margin-top:6px">${note}</div>`;
      },
    },
    calendar: {
      range: [ctx.daily[0].date, ctx.daily.at(-1).date],
      top: 84,
      bottom: 24,
      left: 48,
      right: 24,
      cellSize: "auto",
      dayLabel: { firstDay: 1, color: INK.muted, fontFamily: FONT_MONO, nameMap: ["S", "M", "T", "W", "T", "F", "S"] },
      monthLabel: { color: INK.text, fontFamily: FONT_DISPLAY, fontSize: 13 },
      yearLabel: { show: false },
      itemStyle: { color: "rgba(255,255,255,0.02)", borderColor: INK.surface, borderWidth: 2 },
      splitLine: { lineStyle: { color: INK.line, width: 1 } },
    },
    series: [
      ...legendOnly([...ctx.players, { name: "Dead heat", color: "#FFFFFF" }, { name: "Solo day", color: "#4A5878" }], {
        type: "scatter",
        coordinateSystem: "calendar",
      }),
      { type: "custom", coordinateSystem: "calendar", renderItem: renderTile, data: ctx.daily.map((d) => [d.date, d.margin ?? 0]) },
    ],
  };
}

export function marginsOption(ctx) {
  const contested = ctx.daily.filter((d) => d.contested);
  const avgMargin = contested.reduce((t, d) => t + d.margin, 0) / Math.max(1, contested.length);
  const byDate = new Map(contested.map((d) => [d.date, d]));
  const bars = contested.map((d) => ({
    value: [d.date, d.margin],
    itemStyle: { color: d.winners.length > 1 ? "#FFFFFF" : ctx.colorOf(d.winners[0]) },
  }));
  return {
    legend: { ...LEGEND, selectedMode: false },
    grid: { ...GRID, right: 32 },
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        const day = byDate.get(p.value[0]);
        const [first, second] = day.ranked;
        return (
          tipTitle(prettyDate(day.date)) +
          tipRow(ctx.colorOf(first.playerId), ctx.nameOf(first.playerId), fmt(first.score)) +
          tipRow(ctx.colorOf(second.playerId), ctx.nameOf(second.playerId), fmt(second.score)) +
          `<div style="color:${INK.muted};margin-top:6px">${day.margin ? `won by +${fmt(day.margin)}` : "dead heat!"}</div>`
        );
      },
    },
    xAxis: { type: "time" },
    yAxis: { type: "value", name: "winning margin", nameLocation: "end" },
    dataZoom: zoom,
    series: [
      ...legendOnly(ctx.players),
      {
        type: "bar",
        data: bars,
        barMaxWidth: 12,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: INK.brass, type: "dashed" },
          label: { formatter: `avg +${fmt(avgMargin)}`, color: INK.brass, fontFamily: FONT_MONO, position: "insideEndTop" },
          data: [{ yAxis: avgMargin }],
        },
      },
    ],
  };
}

export function rivalriesOption(ctx) {
  const records = headToHead(ctx.daily);
  const names = ctx.players.map((p) => p.name);
  const data = [];
  ctx.players.forEach((a, row) =>
    ctx.players.forEach((b, col) => {
      const rec = records.get(`${a.id}|${b.id}`);
      if (a.id !== b.id && rec) data.push({ value: [col, row, (100 * (rec.wins + rec.ties / 2)) / rec.shared], rec });
    }),
  );
  return {
    grid: { left: 140, right: 110, top: 30, bottom: 70 },
    tooltip: {
      formatter: (p) => {
        const { rec } = p.data;
        return (
          tipTitle(`${escapeHtml(names[p.value[1]])} vs ${escapeHtml(names[p.value[0]])}`) +
          `<div>won <b>${rec.wins}</b> · lost <b>${rec.losses}</b>${rec.ties ? ` · tied <b>${rec.ties}</b>` : ""}</div>` +
          `<div style="color:${INK.muted}">${rec.shared} shared days</div>`
        );
      },
    },
    xAxis: { type: "category", data: names, name: "opponent", nameLocation: "middle", nameGap: 40, splitArea: { show: false }, axisLabel: { fontFamily: FONT_DISPLAY, fontSize: 13, color: INK.text } },
    yAxis: { type: "category", data: names, inverse: true, axisLabel: { fontFamily: FONT_DISPLAY, fontSize: 13, color: INK.text } },
    visualMap: {
      min: 0,
      max: 100,
      calculable: false,
      orient: "vertical",
      right: 10,
      top: "middle",
      itemHeight: 200,
      text: ["dominates", "dominated"],
      inRange: { color: DIVERGING },
    },
    series: [
      {
        type: "heatmap",
        data,
        itemStyle: { borderColor: INK.surface, borderWidth: 4, borderRadius: 10 },
        label: {
          show: true,
          color: "#fff",
          fontFamily: FONT_MONO,
          lineHeight: 18,
          formatter: (p) => `{big|${fmt(p.value[2])}%}\n${p.data.rec.wins}–${p.data.rec.losses}`,
          rich: { big: { fontSize: 18, fontWeight: 700, fontFamily: FONT_DISPLAY, color: "#fff" } },
        },
        emphasis: { itemStyle: { borderColor: INK.brass, borderWidth: 2 } },
      },
    ],
  };
}

// Stable pseudo-random jitter so dots don't jump on every re-render.
const jitter = (text) => {
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return ((h >>> 0) / 2 ** 32 - 0.5) * 0.5;
};

export function terrainOption(ctx) {
  const players = ctx.players.filter((p) => ctx.byPlayer.has(p.id));
  const boxes = players.map((p) => {
    const sorted = ctx.byPlayer.get(p.id).map((g) => g.score).sort((a, b) => a - b);
    return {
      value: [sorted[0], ...[0.25, 0.5, 0.75].map((q) => quantile(sorted, q)), sorted.at(-1)],
      itemStyle: { color: `${p.color}22`, borderColor: p.color, borderWidth: 1.5 },
    };
  });
  const dots = players.flatMap((p, i) =>
    ctx.byPlayer.get(p.id).map((g) => ({
      value: [i + jitter(g.date + p.id), g.score],
      date: g.date,
      itemStyle: { color: p.color },
    })),
  );
  return {
    grid: { ...GRID, right: 32, top: 24, bottom: 48 },
    tooltip: {
      formatter: (p) =>
        p.seriesType === "boxplot"
          ? tipTitle(escapeHtml(players[p.dataIndex].name)) +
            ["max", "Q3", "median", "Q1", "min"].map((label, i) => tipRow(players[p.dataIndex].color, label, fmt(p.value[5 - i]))).join("")
          : tipTitle(prettyDate(p.data.date)) + tipRow(p.color, players[Math.round(p.value[0])].name, fmt(p.value[1])),
    },
    xAxis: { type: "category", data: players.map((p) => p.name), axisLabel: { fontFamily: FONT_DISPLAY, fontSize: 13, color: INK.text } },
    yAxis: SCORE_AXIS,
    series: [
      { type: "boxplot", data: boxes, boxWidth: [30, 70] },
      { type: "scatter", data: dots, symbolSize: 7, itemStyle: { opacity: 0.7, borderColor: INK.surface, borderWidth: 1 }, z: 3 },
    ],
  };
}

function groupedBars(ctx, valuesByPlayer, labels, valueFormat) {
  const series = ctx.players
    .filter((p) => valuesByPlayer.has(p.id))
    .map((p) => ({
      name: p.name,
      type: "bar",
      color: p.color,
      barGap: "15%",
      barMaxWidth: 26,
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      emphasis: { focus: "series" },
      data: valuesByPlayer.get(p.id),
    }));
  return {
    legend: LEGEND,
    grid: { ...GRID, right: 32 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(245,192,74,0.06)" } },
      formatter: (params) =>
        tipTitle(params[0].name) +
        params
          .filter((p) => p.value != null)
          .sort((a, b) => b.value - a.value)
          .map((p) => tipRow(p.color, p.seriesName, valueFormat(p.value)))
          .join(""),
    },
    xAxis: { type: "category", data: labels, axisLabel: { fontFamily: FONT_DISPLAY, fontSize: 13, color: INK.text } },
    yAxis: { type: "value" },
    series,
  };
}

export function tidesOption(ctx) {
  const days = ctx.includeWeekends ? 7 : 5;
  const averages = averageByWeekday(ctx.games);
  const trimmed = new Map([...averages].map(([id, values]) => [id, values.slice(0, days).map((v) => (v == null ? null : Math.round(v)))]));
  const option = groupedBars(ctx, trimmed, WEEKDAYS.slice(0, days), fmt);
  option.yAxis = SCORE_AXIS;
  return option;
}

export const ROUND_METRIC_LABELS = {
  average: { label: "Average", axis: "avg points", format: (v) => fmt(v) },
  fiveKRate: { label: "5k rate", axis: "% perfect", format: (v) => `${fmt(v, 1)}%` },
  blunderRate: { label: "Blunders", axis: "% under 1k", format: (v) => `${fmt(v, 1)}%` },
};

export function roundsOption(ctx, { metric }) {
  const { axis, format } = ROUND_METRIC_LABELS[metric];
  const values = byRound(ctx.games, metric);
  const labels = Array.from({ length: ROUNDS_PER_GAME }, (_, i) => `Round ${i + 1}`);
  const series = ctx.players
    .filter((p) => values.has(p.id))
    .map((p) => glowLine(p, values.get(p.id), { symbolSize: 12, showSymbol: true }));
  return {
    legend: LEGEND,
    grid: GRID,
    tooltip: {
      trigger: "axis",
      formatter: (params) =>
        tipTitle(params[0].name) +
        [...params].sort((a, b) => b.value - a.value).map((p) => tipRow(p.color, p.seriesName, format(p.value))).join(""),
    },
    xAxis: { type: "category", data: labels, boundaryGap: false, axisLabel: { fontFamily: FONT_DISPLAY, fontSize: 13, color: INK.text } },
    yAxis: { type: "value", scale: metric === "average", name: axis, nameLocation: "end", axisLabel: { formatter: (v) => format(v) } },
    series,
  };
}

export function bullseyeOption(ctx) {
  const histogram = roundHistogram(ctx.games);
  const rounded = new Map([...histogram].map(([id, values]) => [id, values.map((v) => +v.toFixed(1))]));
  const option = groupedBars(ctx, rounded, ROUND_BUCKETS.map((b) => b.label), (v) => `${fmt(v, 1)}%`);
  option.yAxis = { type: "value", name: "% of rounds", nameLocation: "end", axisLabel: { formatter: "{value}%" } };
  option.xAxis.axisLabel.formatter = (label) => (label === "5K" ? "{bull|◎ 5K}" : label);
  option.xAxis.axisLabel.rich = { bull: { color: INK.brass, fontWeight: 700, fontFamily: FONT_DISPLAY, fontSize: 14 } };
  return option;
}

/** Phone-width tweak: reclaim the right gutter used by end-of-line labels. */
export function compact(option) {
  for (const s of option.series) if (s.endLabel) s.endLabel = { ...s.endLabel, show: false };
  if (option.grid) option.grid = { ...option.grid, left: 52, right: 16 };
  return option;
}

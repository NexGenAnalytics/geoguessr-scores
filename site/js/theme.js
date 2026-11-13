// "Night atlas" palette and the matching ECharts theme.

// Glowing map-pin hues, fixed order (validated for colorblind separation on the dark surface).
export const PLAYER_COLORS = ["#FF7A59", "#3DD6C6", "#F5C04A", "#A98BFF", "#9BE564", "#FF6FB1", "#5AB0FF", "#FFA94D"];

export const INK = {
  surface: "#0B1220",
  panel: "#101A2C",
  line: "#22304A",
  grid: "rgba(140, 170, 220, 0.10)",
  muted: "#7D8AA5",
  text: "#E8ECF4",
  brass: "#F5C04A",
};

// Diverging red ↔ slate ↔ blue for win rates; poles kept apart from the player hues.
export const DIVERGING = ["#E0475B", "#2A3550", "#3B9DFF"];

export const FONT_MONO = '"JetBrains Mono", ui-monospace, monospace';
export const FONT_DISPLAY = '"Bricolage Grotesque", system-ui, sans-serif';

export const playerColor = (index) => PLAYER_COLORS[index % PLAYER_COLORS.length];

const axis = {
  axisLine: { lineStyle: { color: INK.line } },
  axisTick: { show: false },
  axisLabel: { color: INK.muted, fontFamily: FONT_MONO, fontSize: 11 },
  splitLine: { lineStyle: { color: INK.grid, type: [4, 4] } },
  nameTextStyle: { color: INK.muted, fontFamily: FONT_MONO },
};

export const ATLAS_THEME = {
  color: PLAYER_COLORS,
  backgroundColor: "transparent",
  textStyle: { fontFamily: FONT_MONO, color: INK.text },
  legend: {
    textStyle: { color: INK.text, fontFamily: FONT_DISPLAY, fontSize: 13 },
    icon: "roundRect",
    itemWidth: 14,
    itemHeight: 6,
    inactiveColor: "#3A4560",
  },
  tooltip: {
    backgroundColor: "rgba(10, 16, 30, 0.96)",
    borderColor: INK.line,
    borderWidth: 1,
    padding: [10, 12],
    textStyle: { color: INK.text, fontFamily: FONT_MONO, fontSize: 12 },
    extraCssText: "border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.45);",
    axisPointer: { lineStyle: { color: INK.brass, type: "dashed", width: 1 }, crossStyle: { color: INK.brass } },
  },
  categoryAxis: axis,
  valueAxis: axis,
  timeAxis: axis,
  dataZoom: {
    borderColor: INK.line,
    fillerColor: "rgba(245, 192, 74, 0.10)",
    handleStyle: { color: INK.brass, borderColor: INK.brass },
    moveHandleStyle: { color: INK.line },
    textStyle: { color: INK.muted, fontFamily: FONT_MONO },
    dataBackground: { lineStyle: { color: INK.muted }, areaStyle: { color: INK.line } },
  },
  visualMap: { textStyle: { color: INK.muted, fontFamily: FONT_MONO } },
};

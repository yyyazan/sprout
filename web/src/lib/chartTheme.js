// One palette + one base config for every lightweight-charts host.
// The library paints to canvas and can't read CSS vars, so these mirror the
// app.css tokens by hand — when a token changes there, change it here.
import { ColorType, CrosshairMode, LineStyle } from 'lightweight-charts';

export const BRAND = '#0fb39a';

export const CHART_FONT = "'Archivo', 'Helvetica Neue', Arial, system-ui, sans-serif";

export function chartPalette(theme) {
  return theme === 'light'
    ? { INK: '#1a1a1a', GRID: '#e7e1d3', MUTED: '#5a564e', SPY: '#9a9385', GAIN: '#067a3c', LOSS: '#c92a2a' }
    : { INK: '#faf7f0', GRID: '#2a2722', MUTED: '#a8a295', SPY: '#7d776b', GAIN: '#00c060', LOSS: '#ff4d4d' };
}

// the part of the config that follows the theme — passed to applyOptions on a flip
export function themeOptions(pal) {
  return {
    layout: { textColor: pal.MUTED },
    grid: { horzLines: { color: pal.GRID } },
    crosshair: { vertLine: { color: pal.INK }, horzLine: { color: pal.GRID } },
  };
}

// full createChart config; hosts spread it and override scaleMargins / timeScale details
export function baseChartOptions(pal) {
  return {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: 'rgba(0,0,0,0)' },
      textColor: pal.MUTED, fontFamily: CHART_FONT, fontSize: 11, attributionLogo: false,
    },
    grid: { vertLines: { visible: false }, horzLines: { color: pal.GRID } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
    crosshair: {
      mode: CrosshairMode.Magnet,
      vertLine: { color: pal.INK, width: 1, style: LineStyle.Solid, labelVisible: false },
      horzLine: { color: pal.GRID, width: 1, style: LineStyle.Dotted, labelVisible: false },
    },
    handleScroll: false, handleScale: false,
  };
}

// the one area style — portfolio value, portfolio return, stock price: BRAND
// line over a 16% → 0 fill
export function areaStyle(color = BRAND) {
  return {
    lineColor: color, lineWidth: 2, topColor: hexA(color, 0.16), bottomColor: hexA(color, 0),
    priceLineVisible: false, lastValueVisible: false,
  };
}

// No marker room under the series. Series markers add their arrow height to the axis
// in pixels (a ~30px band below the lowest bar), on top of scaleMargins — that is what
// pushed the Return axis well under its low and a tall stock chart under $0. The bottom
// scale margin carries the arrows' room instead, so the axis floor is exactly what it
// says; the room above stays as the library sizes it.
export const dataRange = (original) => {
  const r = original();
  return r && { ...r, margins: { above: r.margins?.above ?? 0, below: 0 } };
};

// Bottom scale margin that keeps a $ axis from running past 0. The axis reaches
// bottom × span below the series' lowest value, so cap `want` where that lands on the
// floor: b ≤ (lo − floor)(1 − top) / (hi − floor). Prices and portfolio value can't
// be negative; a volatile ticker's tall volume band used to pull the axis (and its
// labels) under $0. The floor sits 1% of the range above 0 so the 0.00 tick falls
// outside instead of being half-cut on the plot edge. Only binds when lo is small
// next to hi.
export function bottomMargin(want, top, lo, hi, floor = 0) {
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi <= floor) return 0;
  const edge = floor + 0.01 * (hi - floor);
  const cap = (Math.max(lo, edge) - edge) * (1 - top) / (hi - edge);
  return Math.max(0, Math.min(want, cap));
}

export function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

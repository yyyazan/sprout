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

export function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

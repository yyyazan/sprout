// Chart theme + spec factories. Replaces the old Plotly facade: builders here
// return plain *specs* (tagged by `kind`) that the renderer components consume —
// TimeSeriesChart.svelte (Lightweight Charts) for time-series, and the SVG
// DonutChart/PnlBars for the rest. Charts arrive from the API as raw series
// ({x,y} / {labels,values}); see api/serialize.py.

export const ACCENT = '#e37961';
export const NEUTRAL = '#1c1c1e';
export const MUTED = '#6b6b6f';
export const GRID = '#ececea';
export const GAIN = '#2f9e7d';
export const LOSS = '#c94f4f';
export const PALETTE = [ACCENT, '#2f9e7d', '#5b8def', '#c994e8', '#f0b86b', '#888888'];
const BENCH_COLORS = [MUTED, '#5b8def'];

// {x: ['YYYY-MM-DD'...], y: [num|null...]} -> [{time, value}], dropping nulls.
// Lightweight Charts accepts ISO date strings as `time` directly, and requires
// strictly ascending unique times (the API already emits them sorted).
function toSeries(xy) {
  if (!xy || !xy.x) return [];
  const out = [];
  for (let i = 0; i < xy.x.length; i++) {
    const v = xy.y[i];
    if (v === null || v === undefined) continue;
    out.push({ time: xy.x[i], value: v });
  }
  return out;
}

// Portfolio value over time — area, dollars.
export function equity(xy) {
  return {
    kind: 'timeseries',
    fmt: 'money',
    series: [{ type: 'area', name: 'Portfolio', color: ACCENT, data: toSeries(xy) }]
  };
}

// Time-weighted return vs benchmarks — multi-line, percent, zero baseline.
export function twr(t) {
  const series = [
    { type: 'line', name: 'Portfolio', color: ACCENT, width: 2, data: toSeries(t.portfolio) }
  ];
  let i = 0;
  for (const [label, s] of Object.entries(t.benchmarks ?? {})) {
    series.push({
      type: 'line', name: label, color: BENCH_COLORS[i % BENCH_COLORS.length],
      width: 1.4, dashed: true, data: toSeries(s)
    });
    i++;
  }
  return { kind: 'timeseries', fmt: 'percent', baseline: 0, series };
}

// Drawdown — baseline area hanging below zero, percent.
export function drawdown(xy) {
  return {
    kind: 'timeseries',
    fmt: 'percent',
    baseline: 0,
    series: [{ type: 'baseline', name: 'Drawdown', color: LOSS, data: toSeries(xy) }]
  };
}

// Unrealized P&L by ticker — diverging horizontal bars (SVG).
export function pnl(bars) {
  return { kind: 'bars', tickers: bars.tickers, values: bars.values };
}

// Allocation — donut (SVG).
export function donut(alloc) {
  return { kind: 'donut', labels: alloc.labels, values: alloc.values };
}

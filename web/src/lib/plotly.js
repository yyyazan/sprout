// Plotly.js theme + figure factories, mirroring src/portfolio/viz/figures.py.
// Plotly is browser-only and ~3MB, so it's dynamically imported (see Chart.svelte).

export const ACCENT = '#e37961';
export const NEUTRAL = '#1c1c1e';
export const MUTED = '#6b6b6f';
export const GRID = '#ececea';
export const GAIN = '#2f9e7d';
export const LOSS = '#c94f4f';
export const PALETTE = [ACCENT, '#2f9e7d', '#5b8def', '#c994e8', '#f0b86b', '#888888'];
const BENCH_COLORS = [MUTED, '#5b8def'];

export const CONFIG = { displayModeBar: false, responsive: true };

function baseLayout(extra = {}) {
  return {
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
    font: { family: '-apple-system, system-ui, sans-serif', color: NEUTRAL, size: 12 },
    colorway: PALETTE,
    xaxis: { showgrid: true, gridcolor: GRID, zeroline: false, linecolor: GRID, tickfont: { color: MUTED } },
    yaxis: { showgrid: true, gridcolor: GRID, zeroline: false, linecolor: GRID, tickfont: { color: MUTED } },
    margin: { t: 20, b: 30, l: 50, r: 20 },
    legend: { font: { color: NEUTRAL, size: 11 }, bgcolor: 'rgba(0,0,0,0)' },
    ...extra
  };
}

export function equityCurve(xy) {
  const data = [{
    x: xy.x, y: xy.y, mode: 'lines', name: 'Portfolio',
    line: { color: ACCENT, width: 2 },
    hovertemplate: '<b>Portfolio</b>  %{x|%b %d %Y}<br>$%{y:,.2f}<extra></extra>'
  }];
  return { data, layout: baseLayout(), config: CONFIG };
}

export function allocationDonut(alloc) {
  const data = [{
    type: 'pie', labels: alloc.labels, values: alloc.values, hole: 0.6,
    marker: { colors: PALETTE.concat(PALETTE).slice(0, alloc.labels.length) },
    textinfo: 'label+percent',
    hovertemplate: '<b>%{label}</b><br>$%{value:,.2f}  %{percent}<extra></extra>'
  }];
  return { data, layout: baseLayout({ showlegend: false }), config: CONFIG };
}

export function twrVsBench(twr) {
  const data = [{
    x: twr.portfolio.x, y: twr.portfolio.y, mode: 'lines', name: 'Portfolio',
    line: { color: ACCENT, width: 2 },
    hovertemplate: '<b>Portfolio TWR</b>  %{x|%b %d %Y}<br>%{y:+.2f}%<extra></extra>'
  }];
  let i = 0;
  for (const [label, series] of Object.entries(twr.benchmarks)) {
    data.push({
      x: series.x, y: series.y, mode: 'lines', name: label,
      line: { color: BENCH_COLORS[i % BENCH_COLORS.length], width: 1.4, dash: 'dot' },
      hovertemplate: `<b>${label} TWR</b>  %{x|%b %d %Y}<br>%{y:+.2f}%<extra></extra>`
    });
    i++;
  }
  const layout = baseLayout();
  layout.yaxis = { ...layout.yaxis, ticksuffix: '%' };
  layout.shapes = [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0, line: { color: GRID, dash: 'dot' } }];
  return { data, layout, config: CONFIG };
}

export function drawdownArea(xy) {
  const data = [{
    x: xy.x, y: xy.y, mode: 'lines', name: 'Drawdown',
    line: { color: LOSS, width: 1.4 }, fill: 'tozeroy', fillcolor: 'rgba(201,79,79,0.12)',
    hovertemplate: '<b>Drawdown</b>  %{x|%b %d %Y}<br>%{y:.2f}%<extra></extra>'
  }];
  const layout = baseLayout();
  layout.yaxis = { ...layout.yaxis, ticksuffix: '%' };
  return { data, layout, config: CONFIG };
}

export function pnlBars(bars, label = 'Unrealized P&L') {
  const colors = bars.values.map((v) => (v >= 0 ? GAIN : LOSS));
  const data = [{
    type: 'bar', orientation: 'h', y: bars.tickers, x: bars.values,
    marker: { color: colors },
    text: bars.values.map((v) => `$${v >= 0 ? '+' : ''}${Math.round(v).toLocaleString('en-US')}`),
    textposition: 'outside',
    hovertemplate: `<b>%{y}</b><br>${label}: $%{x:+,.2f}<extra></extra>`,
    showlegend: false
  }];
  return { data, layout: baseLayout(), config: CONFIG };
}

let _plotly = null;
export async function loadPlotly() {
  if (!_plotly) {
    _plotly = (await import('plotly.js-dist-min')).default;
  }
  return _plotly;
}

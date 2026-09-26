// Shared chart behavior for PortfolioChart + StockChart. The look is
// chartTheme.js and the chrome is components/chart/*; this is the part that
// reacts to input: hover, click-drag measure, touch hold-scrub, horizontal
// pan, the measure band, and buy/sell markers.
import { AreaSeries } from 'lightweight-charts';
import { hexA } from './chartTheme.js';

export const RANGE_LABELS = {
  '1D': 'today', '1W': 'past week', '1M': 'past month', '3M': 'past 3 months', '6M': 'past 6 months',
  'YTD': 'year to date', '1Y': 'past year', '2Y': 'past 2 years', '5Y': 'past 5 years', '10Y': 'past 10 years',
  'ALL': 'all-time',
};

// Lookup key for a bar time. Intraday bars are unix seconds, daily bars are
// 'YYYY-MM-DD'; the library can hand daily times back as {year,month,day}.
export const timeKey = (t) => {
  if (t == null) return '';
  if (typeof t === 'object' && t.year) return `${t.year}-${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}`;
  return String(t);
};

// local YYYY-MM-DD of a bar time
export const barDay = (t) => {
  if (typeof t !== 'number') return timeKey(t);
  const d = new Date(t * 1000);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export function fmtTime(t) {
  if (t == null) return '';
  if (typeof t === 'number') {
    const d = new Date(t * 1000);
    return isNaN(d) ? '' : d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  }
  const d = new Date(barDay(t) + 'T00:00:00');
  return isNaN(d) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export const fmtPct = (n) => (n == null || !isFinite(n) ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(1) + '%');
const f2 = (n) => Number(n ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const fmtUsd = (n) => (n == null ? '—' : (n < 0 ? '−$' : '$') + f2(Math.abs(n)));
export const fmtUsdSigned = (n) => (n == null ? '—' : (n >= 0 ? '+$' : '−$') + f2(Math.abs(n)));

// index of each point by timeKey, cached per points array
const idxCache = new WeakMap();
export function indexOf(points, t) {
  if (!points?.length || t == null) return -1;
  let m = idxCache.get(points);
  if (!m) { m = new Map(points.map((p, i) => [timeKey(p.time), i])); idxCache.set(points, m); }
  return m.get(timeKey(t)) ?? -1;
}

// ── pointer input ─────────────────────────────────────────────────────────
// hover  = the bar under the crosshair (mouse, or the touch scrub)
// anchor = where a mouse drag-measure started; cleared on release
// Touch never measures: HOLD then drag scrubs the crosshair, a quick swipe is
// left to the page. A horizontal wheel/two-finger swipe calls pan(bars).
export class ChartPointer {
  hover = $state(null);   // { x, y, time }
  anchor = $state(null);  // { x, time }

  // points(): the main series' [{ time, value }] · series(): its api
  // pan(bars): shift the window back by `bars`; return false if there's nowhere to go
  constructor({ points, series, pan = null, holdMs = 220 }) {
    this.points = points;
    this.series = series;
    this.pan = pan;
    this.holdMs = holdMs;
  }

  // The library re-fires the crosshair event whenever a series gets new data —
  // including the band repaint an effect does off `hover` — so an unchanged
  // point must not write, or that effect loops.
  #setHover(h) {
    const o = this.hover;
    if (h === o || (h && o && h.x === o.x && h.y === o.y && timeKey(h.time) === timeKey(o.time))) return;
    this.hover = h;
  }

  attach(chart, host) {
    const ts = () => chart.timeScale();
    const onMove = (p) => {
      if (!p.time || !p.point || p.point.x < 0) { this.#setHover(null); return; }
      this.#setHover({ x: ts().timeToCoordinate(p.time) ?? p.point.x, y: p.point.y, time: p.time });
    };
    chart.subscribeCrosshairMove(onMove);

    // touch scrub: snap the finger's x to the nearest main-series point
    let holdTimer = null, scrubbing = false, downAt = null;
    const scrubAt = (clientX) => {
      const pts = this.points(), s = this.series();
      if (!s || !pts?.length) return;
      const x = clientX - host.getBoundingClientRect().left;
      let lo = 0, hi = pts.length - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if ((ts().timeToCoordinate(pts[mid].time) ?? -Infinity) < x) lo = mid + 1; else hi = mid;
      }
      if (lo > 0 && x - (ts().timeToCoordinate(pts[lo - 1].time) ?? 0) < (ts().timeToCoordinate(pts[lo].time) ?? 0) - x) lo--;
      const pt = pts[lo];
      chart.setCrosshairPosition(pt.value, pt.time, s);
      const y = s.priceToCoordinate(pt.value) ?? 0;
      this.#setHover({ x: ts().timeToCoordinate(pt.time) ?? x, y, time: pt.time });
    };
    const endScrub = () => {
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      downAt = null;
      if (scrubbing) { scrubbing = false; chart.clearCrosshairPosition(); this.#setHover(null); }
    };

    const onDown = (e) => {
      if (e.pointerType === 'touch') {
        downAt = { x: e.clientX, y: e.clientY };
        holdTimer = setTimeout(() => { holdTimer = null; scrubbing = true; scrubAt(downAt.x); }, this.holdMs);
        return;
      }
      if (e.button === 0 && this.hover) this.anchor = { x: this.hover.x, time: this.hover.time };
    };
    const onPtrMove = (e) => {
      if (e.pointerType !== 'touch') return;
      if (scrubbing) { scrubAt(e.clientX); return; }
      // moved before the hold landed → it's a scroll, not a scrub
      if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 8) endScrub();
    };
    const onPtrEnd = (e) => { if (e.pointerType === 'touch') endScrub(); };
    const onRelease = () => { if (this.anchor) this.anchor = null; };

    // horizontal wheel pans through time; vertical stays with the page
    const onWheel = (e) => {
      if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
      if (this.pan?.(-e.deltaX / 8)) e.preventDefault();
    };

    host.addEventListener('pointerdown', onDown);
    host.addEventListener('pointermove', onPtrMove);
    host.addEventListener('pointerup', onPtrEnd);
    host.addEventListener('pointercancel', onPtrEnd);
    host.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('pointerup', onRelease);
    window.addEventListener('pointercancel', onRelease);
    return () => {
      endScrub();
      chart.unsubscribeCrosshairMove(onMove);
      host.removeEventListener('pointerdown', onDown);
      host.removeEventListener('pointermove', onPtrMove);
      host.removeEventListener('pointerup', onPtrEnd);
      host.removeEventListener('pointercancel', onPtrEnd);
      host.removeEventListener('wheel', onWheel);
      window.removeEventListener('pointerup', onRelease);
      window.removeEventListener('pointercancel', onRelease);
    };
  }

  // The measured span over `points`, oldest → newest whichever way the mouse
  // went. Null until the drag has moved past 8px, so a click stays a hover.
  span(points) {
    const a = this.anchor, h = this.hover;
    if (!a || !h || Math.abs(h.x - a.x) <= 8) return null;
    let i0 = indexOf(points, a.time), i1 = indexOf(points, h.time);
    if (i0 < 0 || i1 < 0 || i0 === i1) return null;
    if (i0 > i1) [i0, i1] = [i1, i0];
    return { i0, i1, t0: points[i0].time, t1: points[i1].time };
  }
}

// ── measure band ──────────────────────────────────────────────────────────
// Tints the area under the main series between the measure's ends. Fed a
// full-length copy of the main points (transparent outside the span), so a
// Percentage scale rebases it exactly like the series it shades. Add it
// before the main series so it draws underneath.
export function addBand(chart) {
  return chart.addSeries(AreaSeries, {
    lineColor: 'rgba(0,0,0,0)', lineWidth: 1, topColor: 'rgba(0,0,0,0)', bottomColor: 'rgba(0,0,0,0)',
    priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    autoscaleInfoProvider: () => null,
  });
}

const painted = new WeakMap();   // band → what it last drew; hover moves within a bar skip the repaint
export function paintBand(band, points, m, pal) {
  if (!band) return;
  const on = !!(m && points?.length);
  const tint = on ? hexA((m.pct ?? m.abs ?? 0) >= 0 ? pal.GAIN : pal.LOSS, 0.18) : null;
  const key = on ? `${m.i0}|${m.i1}|${tint}` : '';
  const last = painted.get(band);
  if (last && last.points === points && last.key === key) return;
  painted.set(band, { points, key });
  if (!on) { band.setData([]); return; }
  const clear = 'rgba(0,0,0,0)';
  // a segment takes its left point's color, so the tint runs i0 … i1-1
  band.setData(points.map((p, i) => {
    const c = i >= m.i0 && i < m.i1 ? tint : clear;
    return { time: p.time, value: p.value, topColor: c, bottomColor: c };
  }));
}

// ── buy/sell markers ──────────────────────────────────────────────────────
// Each fill lands on its day's bar (or the nearest bar before it); one arrow
// per bar and side. byKey maps timeKey(bar time) → the fills on that bar.
export function tradeMarkers(bars, trades, pal) {
  if (!bars?.length || !trades?.length) return { markers: [], byKey: new Map() };
  const days = bars.map((b) => ({ day: barDay(b.time), time: b.time }));
  const first = days[0].day, last = days[days.length - 1].day;
  const sides = new Set();
  const byKey = new Map();
  for (const t of trades) {
    if (!t.date || t.date < first || t.date > last) continue;
    let barTime = null;
    for (const bd of days) { if (bd.day <= t.date) barTime = bd.time; else break; }
    if (barTime == null) continue;
    const k = timeKey(barTime);
    sides.add(`${k}|${isBuy(t) ? 'buy' : 'sell'}`);
    (byKey.get(k) ?? byKey.set(k, []).get(k)).push(t);
  }
  // bar order keeps the array time-ascending, which the library requires
  const markers = [];
  for (const b of bars) {
    const k = timeKey(b.time);
    if (sides.has(`${k}|buy`)) markers.push({ time: b.time, position: 'belowBar', color: pal.GAIN, shape: 'arrowUp' });
    if (sides.has(`${k}|sell`)) markers.push({ time: b.time, position: 'aboveBar', color: pal.LOSS, shape: 'arrowDown' });
  }
  return { markers, byKey };
}

const isBuy = (t) => (t.action || '').toLowerCase() === 'buy';

// tooltip lines for the fills on a bar; `what` = the ticker (portfolio) or 'sh'
export function tradeLines(trades, what = (t) => 'sh') {
  return (trades ?? []).map((t) => ({
    up: isBuy(t),
    text: `${isBuy(t) ? 'Buy' : 'Sell'} ${Number(t.shares).toLocaleString('en-US', { maximumFractionDigits: 4 })} ${what(t)}`
      + (t.price != null ? ` @ ${fmtUsd(t.price)}` : ''),
  }));
}

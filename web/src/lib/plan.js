// Plan projection — runs in the browser so the chart redraws on every slider move.
//
// Month by month: balance grows at the expected return, then this month's saving
// lands. Saving = take-home × rate. Take-home is today's figure until an income
// change's month (a new job, say), then that one; each grows by the raise once a
// year after it starts. Returns are real (after inflation), so every figure is in
// today's dollars.
//
// HYSA: its monthly deposit comes out of that saving (capped at it), the rest is
// invested. The APY is a bank's nominal rate, so the balance grows at APY less
// INFLATION to stay in today's dollars; interest is what the bank pays that month,
// in today's dollars too. It carries no range: a savings account doesn't swing.
//
// The range is the middle 80% of outcomes for a broad index fund: yearly log
// returns ~ N(μ, σ²) with σ = 15%, so over t years the annualized return sits
// within μ ± 1.28·σ/√t eight times in ten. Each point re-runs the path at that
// point's 10th / 90th percentile rate. It's an approximation (saving made late
// sees less of the swing than the start balance does) but it widens the way the
// real spread does: fast in dollars, slow in rate.

export const SIGMA = 0.15;
export const INFLATION = 0.025;
const Z80 = 1.2816;

// months from `start`'s month to a 'YYYY-MM' (0 = this month)
export function monthsFrom(start, ym) {
  const [y, mo] = ym.split('-').map(Number);
  return (y - start.getFullYear()) * 12 + (mo - 1 - start.getMonth());
}

// take-home for each month 1..months: today's, then each change from its month on
function incomes(income, steps, raisePct, months, start) {
  const segs = [{ from: 0, income: income || 0 }];
  for (const s of steps ?? []) segs.push({ from: Math.max(0, monthsFrom(start, s.month)), income: s.income || 0 });
  segs.sort((a, b) => a.from - b.from);
  const raise = 1 + raisePct / 100;
  const out = new Float64Array(months + 1);
  let k = 0;
  for (let m = 1; m <= months; m++) {
    while (k + 1 < segs.length && segs[k + 1].from <= m) k++;
    out[m] = segs[k].income * raise ** Math.floor((m - Math.max(1, segs[k].from)) / 12);
  }
  return out;
}

function path(balance, saving, annual, months) {
  const r = (1 + annual) ** (1 / 12) - 1;
  const out = new Float64Array(months + 1);
  let b = balance;
  out[0] = b;
  for (let m = 1; m <= months; m++) {
    b = b * (1 + r) + saving[m];
    out[m] = b;
  }
  return out;
}

// value at month m on a constant annual rate (the band's per-point re-run)
function valueAt(balance, saving, annual, m) {
  const r = (1 + annual) ** (1 / 12) - 1;
  let b = balance;
  for (let k = 1; k <= m; k++) b = b * (1 + r) + saving[k];
  return b;
}

// points[m] = { m, date, income, putIn, mid, lo, hi, hysa, interest }
//   mid/lo/hi = investments + HYSA; hysa = HYSA balance; interest = HYSA interest
//   paid in month m; income = take-home that month
export function project({ balance, income, steps = [], rate, returnPct, raisePct, years,
  hysa = { balance: 0, apy: 0, monthly: 0 }, start = new Date() }) {
  const months = Math.round(years * 12);
  const pay = incomes(income, steps, raisePct, months, start);
  const invest = new Float64Array(months + 1);
  const toHysa = new Float64Array(months + 1);
  for (let m = 1; m <= months; m++) {
    const saving = pay[m] * rate;
    toHysa[m] = Math.min(hysa.monthly || 0, saving);
    invest[m] = saving - toHysa[m];
  }

  const apy = (hysa.apy || 0) / 100;
  const nominal = (1 + apy) ** (1 / 12) - 1;
  const inflate = (1 + INFLATION) ** (1 / 12);
  const hb = new Float64Array(months + 1);
  const paid = new Float64Array(months + 1);
  hb[0] = hysa.balance || 0;
  for (let m = 1; m <= months; m++) {
    paid[m] = (hb[m - 1] * nominal) / inflate;
    hb[m] = (hb[m - 1] * (1 + nominal)) / inflate + toHysa[m];
  }

  const mu = Math.log(1 + returnPct / 100);
  const mid = path(balance, invest, returnPct / 100, months);

  const points = [];
  let putIn = balance + hb[0];
  for (let m = 0; m <= months; m++) {
    putIn += invest[m] + toHysa[m];
    let lo = mid[m], hi = mid[m];
    if (m > 0) {
      const spread = (Z80 * SIGMA) / Math.sqrt(m / 12);
      lo = valueAt(balance, invest, Math.exp(mu - spread) - 1, m);
      hi = valueAt(balance, invest, Math.exp(mu + spread) - 1, m);
    }
    const d = new Date(start.getFullYear(), start.getMonth() + m, 1);
    points.push({ m, date: d, income: pay[m], putIn, mid: mid[m] + hb[m], lo: lo + hb[m], hi: hi + hb[m],
      hysa: hb[m], interest: paid[m] });
  }
  return points;
}

const MINUS = '−';

export const usd0 = (n) =>
  n == null || !isFinite(n) ? '—' : (n < 0 ? MINUS : '') + '$' + Math.round(Math.abs(n)).toLocaleString('en-US');

export const usdSigned0 = (n) =>
  n == null || !isFinite(n) ? '—' : (n < 0 ? MINUS : '+') + '$' + Math.round(Math.abs(n)).toLocaleString('en-US');

// axis labels: $0, $40k, $1.2M
export function usdShort(n) {
  const a = Math.abs(n);
  if (a >= 1e6) return '$' + (a / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, '') + 'M';
  if (a >= 1e3) return '$' + Math.round(a / 1e3) + 'k';
  return '$' + Math.round(a);
}

// round-number axis ticks covering [0, hi]
export function niceTicks(hi, count = 4) {
  if (!(hi > 0)) return [0];
  const raw = hi / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((s) => s * mag).find((s) => s >= raw);
  const out = [0];
  while (out[out.length - 1] < hi - step * 0.001) out.push(out.length * step);
  return out;
}

export const monthLabel = (d) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

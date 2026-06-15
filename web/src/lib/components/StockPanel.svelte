<script>
  // Stock view as a WIDGET GRID — Google Finance's content in Sprout's widget
  // language. Strict 4-column grid, canvas showing through the gaps: header
  // (4×0.5: crumb + back top-right, name/quote, position-or-watch) → chart (4×2)
  // → key stats (4×1, three columns) → analyst outlook (two BARE centred cells:
  // ratings RingGauge | forecast bars) → news (4×1, sentiment-dotted headlines)
  // → related stocks (4 × 1×1 cards). Chrome-less so the dashboard stage and
  // the modal both render this grid directly on the page.
  import { onMount } from 'svelte';
  import StockChart from './StockChart.svelte';
  import RingGauge from './RingGauge.svelte';
  import { mockStock, fmtCap, fmtVol } from '$lib/mockStock.js';
  import { api } from '$lib/api.js';
  import { watchlist, loadWatchlist, toggleWatch, holdings, openStock, cardToHolding } from '$lib/stores.js';

  let { ticker, name = null, holding = null, onClose, glyph = '✕' } = $props();

  const owned = $derived(!!holding);

  // watch state for non-held tickers — shared store keeps the sidebar in sync
  const watched = $derived(($watchlist ?? []).some((w) => w.ticker === (ticker || '').toUpperCase()));
  let watchBusy = $state(false);
  async function onWatch() {
    if (watchBusy) return;
    watchBusy = true;
    try { await toggleWatch((ticker || '').toUpperCase(), !watched); } finally { watchBusy = false; }
  }

  let remote = $state(null);
  $effect(() => {
    const t = ticker;
    if (!t) { remote = null; return; }
    let cancelled = false;
    remote = null;
    api.stock(t).then((r) => { if (!cancelled) remote = r; }).catch(() => { if (!cancelled) remote = null; });
    return () => { cancelled = true; };
  });

  // related stocks ride their own fetch so they never slow the main payload
  let related = $state(null);
  $effect(() => {
    const t = ticker;
    if (!t) { related = null; return; }
    let cancelled = false;
    related = null;
    api.related(t).then((r) => {
      if (!cancelled && r?.ticker === (t || '').toUpperCase()) related = r.related ?? [];
    }).catch(() => { if (!cancelled) related = []; });
    return () => { cancelled = true; };
  });

  function openRelated(r) {
    const card = ($holdings ?? []).find((c) => c.ticker === r.ticker);
    openStock({ ticker: r.ticker, name: r.name, holding: card ? cardToHolding(card) : null });
  }

  const RATING_MAP = { strong_buy: 'Strong Buy', buy: 'Buy', hold: 'Hold', underperform: 'Underperform', sell: 'Sell', strong_sell: 'Strong Sell' };

  // base "holding-like" object so mockStock() can fill gaps for non-owned tickers too
  const base = $derived(holding ?? { t: ticker, name: name ?? ticker, last: remote?.price ?? null });

  const stock = $derived.by(() => {
    const m = mockStock(base);
    const r = remote;
    if (!r || r.ticker !== (ticker || '').toUpperCase()) return m;
    const price = r.price ?? m.price;
    return {
      ...m,
      price, prevClose: r.prevClose, open: r.open, dayLow: r.dayLow, dayHigh: r.dayHigh,
      lo52: r.week52Low ?? m.lo52, hi52: r.week52High ?? m.hi52, volume: r.volume, avgVolume: r.avgVolume,
      marketCap: r.marketCap, eps: r.eps, divYield: r.divYield,
      pe: r.pe != null ? +Number(r.pe).toFixed(1) : null,
      beta: r.beta != null ? +Number(r.beta).toFixed(2) : null,
      sector: r.sector || m.sector,
      dayPct: r.prevClose && price ? +((price / r.prevClose - 1) * 100).toFixed(2) : m.dayPct,
      _mock: false,
    };
  });

  // ── analyst outlook (real payload only — no mock analyst data) ──
  const analyst = $derived(remote?.analyst ?? null);
  // buy/hold/sell counts for the ratings RingGauge + legend
  const ratingSegs = $derived.by(() => {
    const b = analyst?.buckets;
    if (!b) return null;
    const buy = (b.strongBuy ?? 0) + (b.buy ?? 0);
    const hold = b.hold ?? 0;
    const sell = (b.sell ?? 0) + (b.strongSell ?? 0);
    const total = buy + hold + sell;
    return total ? { total, buy, hold, sell } : null;
  });
  const verdict = $derived(analyst?.verdict ? (RATING_MAP[analyst.verdict] ?? analyst.verdict) : null);
  const verdictTone = $derived(
    !analyst?.verdict ? 'mid' : analyst.verdict.includes('buy') ? 'up' : analyst.verdict.includes('sell') ? 'down' : 'mid'
  );

  // forecast bars scale: bars cap at 44% of the track so figures fit beside them
  const forecast = $derived.by(() => {
    const a = analyst, p = stock.price;
    if (!a || a.targetMean == null || !p) return null;
    const rows = [
      { label: 'highest', v: a.targetHigh },
      { label: 'average', v: a.targetMean },
      { label: 'lowest', v: a.targetLow },
    ].filter((r) => r.v != null);
    if (!rows.length) return null;
    const max = Math.max(...rows.map((r) => r.v), p) * 1.06;
    const W = 44;
    return {
      rows: rows.map((r) => ({ ...r, w: (r.v / max) * W, pct: (r.v / p - 1) * 100 })),
      curX: (p / max) * W,
    };
  });

  // ── sparkline path for a related card (viewBox 0 0 100 32) ──
  function sparkPath(spark, prevClose) {
    if (!spark || spark.length < 2) return null;
    const vals = prevClose != null ? [...spark, prevClose] : spark;
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.12 || 1;
    const y = (v) => 30 - ((v - (lo - pad)) / ((hi + pad) - (lo - pad))) * 28;
    const x = (i) => (i / (spark.length - 1)) * 100;
    const line = spark.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    return { line, area: `${line}L100,32L0,32Z`, prevY: prevClose != null ? y(prevClose) : null };
  }

  const f = (n) => Number(n ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pctS = (n) => (n == null ? '—' : (n > 0 ? '+' : '') + n.toFixed(1) + '%');
  const usdS = (n) => (n == null ? '—' : (n >= 0 ? '+$' : '−$') + f(Math.abs(n)));
  const money = (n) => (n == null ? '—' : '$' + f(n));
  const sUsd = (n) => (n == null ? '—' : (n < 0 ? '−$' : '$') + f(Math.abs(n)));
  const dayAbs = $derived(
    stock.prevClose && stock.price ? stock.price - stock.prevClose : null
  );

  // Realized P&L for this ticker (lifetime; from /api/stock) → show TOTAL P&L =
  // realized + the open position's unrealized. Covers holdings and tickers we've
  // fully sold (those have no card, so they land in the non-owned branch below).
  const realizedPnl = $derived(remote?.realizedPnl ?? null);
  const hasRealized = $derived(realizedPnl != null && Math.abs(realizedPnl) > 0.005);
  const totalPnl = $derived((owned ? (stock.plAbs ?? 0) : 0) + (realizedPnl ?? 0));
  const prevHeld = $derived(!owned && hasRealized);
  // ── headline sentiment — crude keyword scan driving the news dots (green /
  // yellow / red). SWAP POINT: replace with a real sentiment score on the
  // /api/stock news items; the 'pos'|'neu'|'neg' contract stays. ──
  const SENT_POS = /\b(beats?|surges?|soars?|jumps?|rall(?:y|ies)|record|upgrades?|outperforms?|gains?|rises?|tops?|strong|bullish|growth|profits?|wins?|climbs?|boosts?)\b/i;
  const SENT_NEG = /\b(miss(?:es)?|falls?|drops?|plunges?|sinks?|slumps?|downgrades?|underperforms?|lawsuits?|probes?|cuts?|layoffs?|weak|bearish|loss(?:es)?|warns?|recalls?|fraud|crash(?:es)?|tumbles?|slides?|fears?)\b/i;
  function sentimentOf(title) {
    const p = SENT_POS.test(title ?? ''), n = SENT_NEG.test(title ?? '');
    return p && !n ? 'pos' : n && !p ? 'neg' : 'neu';
  }
  const SENT_LABEL = { pos: 'positive', neu: 'neutral', neg: 'negative' };
  const ago = (at) => {
    if (at == null) return '';
    const s = Date.now() / 1000 - at;
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + 'm';
    if (s < 86400) return Math.round(s / 3600) + 'h';
    return Math.round(s / 86400) + 'd';
  };

  const fmtEarn = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso + 'T00:00:00');
    return isNaN(d) ? '—' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  function onKey(e) { if (e.key === 'Escape') onClose?.(); }
  onMount(() => {
    loadWatchlist();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
</script>

<div class="spg">
  <!-- header widget — 4 × 0.5: crumb · back (top right) · identity · quote · position/watch -->
  <section class="w w-head">
    <div class="hw-top">
      <span class="hw-crumb">{ticker}{#if stock.sector && stock.sector !== '—'} · {stock.sector}{/if}</span>
      <button class="btn btn-sm btn-quiet hw-back" onclick={() => onClose?.()}>
        <span aria-hidden="true">{glyph === '←' ? '←' : '✕'}</span>
        {glyph === '←' ? 'portfolio' : 'close'}
      </button>
    </div>
    <div class="hw-main">
      <div class="hw-id">
        <h2 class="hw-name">{stock.name}</h2>
        <div class="hw-quote">
          <span class="hw-px">${f(stock.price)}</span>
          <span class="hw-day {stock.dayPct >= 0 ? 'up' : 'down'}">
            {stock.dayPct >= 0 ? '▲' : '▼'} {pctS(stock.dayPct)}{#if dayAbs != null} ({usdS(dayAbs)}){/if} today
          </span>
        </div>
      </div>
      {#if owned}
        <div class="hw-pos">
          <span class="pos-ret {(stock.plPct ?? 0) >= 0 ? 'up' : 'down'}">
            <b>{pctS(stock.plPct)}</b><small>{usdS(stock.plAbs)}</small>
          </span>
          <span class="pos-kv"><span>p&amp;l</span><b class={totalPnl >= 0 ? 'up' : 'down'}>{usdS(totalPnl)}</b></span>
          <span class="pos-kv"><span>sh</span><b>{f(stock.shares)}</b></span>
          <span class="pos-kv"><span>avg</span><b>${f(stock.avgCost)}</b></span>
          <span class="pos-kv"><span>val</span><b>${f(stock.mktValue)}</b></span>
          <span class="pos-kv"><span>wt</span><b>{stock.weight != null ? stock.weight + '%' : '—'}</b></span>
        </div>
      {:else if prevHeld}
        <!-- fully sold out of this ticker: no live position, but a realized P&L -->
        <div class="hw-prev">
          <span class="pos-ret {totalPnl >= 0 ? 'up' : 'down'}">
            <b>{usdS(totalPnl)}</b><small>total p&amp;l · previously held</small>
          </span>
          <button class="btn btn-line hw-watch" class:on={watched} disabled={watchBusy} onclick={onWatch}>
            {watched ? '✓ Watching' : '+ Watch'}
          </button>
        </div>
      {:else}
        <button class="btn btn-line hw-watch" class:on={watched} disabled={watchBusy} onclick={onWatch}>
          {watched ? '✓ Watching' : '+ Watch'}
        </button>
      {/if}
    </div>
  </section>

  <!-- chart widget — 4 × 2 -->
  <section class="w w-chart">
    {#key ticker}
      <StockChart {ticker} history={remote?.history ?? null} price={stock.price} />
    {/key}
  </section>

  <!-- key stats widget — 4 × 1, three columns -->
  <section class="w w-stats">
    <div class="w-h">key stats</div>
    <div class="ks-cols">
      <div class="ks-col">
        <div class="g-row"><span>open</span><b>{money(stock.open)}</b></div>
        <div class="g-row"><span>high</span><b>{money(stock.dayHigh)}</b></div>
        <div class="g-row"><span>low</span><b>{money(stock.dayLow)}</b></div>
        <div class="g-row"><span>prev close</span><b>{money(stock.prevClose)}</b></div>
      </div>
      <div class="ks-col">
        <div class="g-row"><span>volume</span><b>{stock.volume != null ? fmtVol(stock.volume) : '—'}</b></div>
        <div class="g-row"><span>avg volume</span><b>{stock.avgVolume != null ? fmtVol(stock.avgVolume) : '—'}</b></div>
        <div class="g-row"><span>mkt cap</span><b>{stock.marketCap != null ? fmtCap(stock.marketCap) : '—'}</b></div>
        <div class="g-row"><span>p/e ratio</span><b>{stock.pe ?? '—'}</b></div>
      </div>
      <div class="ks-col">
        <div class="g-row"><span>eps</span><b>{sUsd(stock.eps)}</b></div>
        <div class="g-row"><span>div yield</span><b>{stock.divYield ? stock.divYield + '%' : '—'}</b></div>
        <div class="g-row"><span>beta</span><b>{stock.beta ?? '—'}</b></div>
        <div class="g-row"><span>earnings</span><b>{fmtEarn(remote?.earningsDate)}</b></div>
      </div>
    </div>
  </section>

  <!-- analyst outlook — two BORDERLESS widgets side by side, centred like the
       dashboard's ring row: ratings on the shared RingGauge · forecast bars -->
  {#if analyst && (ratingSegs || forecast)}
    {#if ratingSegs}
      <section class="w-bare w-ratings">
        <RingGauge heroSize={15}
          segments={[
            { key: 'buy', color: 'var(--gain)', value: ratingSegs.buy, tag: 'buy', hero: String(ratingSegs.buy), sub: 'analysts' },
            { key: 'hold', color: 'var(--yellow)', value: ratingSegs.hold, tag: 'hold', hero: String(ratingSegs.hold), sub: 'analysts' },
            { key: 'sell', color: 'var(--loss)', value: ratingSegs.sell, tag: 'sell', hero: String(ratingSegs.sell), sub: 'analysts' },
          ]}
          idle={{ tag: 'ratings', hero: verdict ?? '—', sub: analyst.count ? `${analyst.count} analysts · 3 mo` : null,
            heroColor: verdictTone === 'up' ? 'var(--gain)' : verdictTone === 'down' ? 'var(--loss)' : 'var(--ink)' }} />
      </section>
    {/if}
    {#if forecast}
      <section class="w-bare w-forecast">
        <div class="fc-grid">
          <span class="fc-h">12-mo forecast</span>
          {#each forecast.rows as r (r.label)}
            <span class="fc-label">{r.label}</span>
            <div class="fc-track">
              <div class="fc-bar" style="width:{r.w}%"></div>
              <span class="fc-fig">${f(r.v)} <small class={r.pct >= 0 ? 'up' : 'down'}>({pctS(r.pct)})</small></span>
            </div>
          {/each}
          <span class="fc-label"></span>
          <div class="fc-track fc-cur-track">
            <div class="fc-cur" style="left:{forecast.curX}%">
              <span class="fc-cur-pill">current ${f(stock.price)}</span>
            </div>
          </div>
        </div>
      </section>
    {/if}
  {/if}

  <!-- news — full-width headline list; the dot is the sentiment read
       (green = positive · yellow = neutral · red = negative, keyword heuristic) -->
  {#if remote?.news?.length}
    <section class="w w-news">
      <div class="w-h">news<span class="w-h-sub">{ticker}</span></div>
      <div class="nw-list">
        {#each remote.news as n (n.url ?? n.title)}
          {@const s = sentimentOf(n.title)}
          <a class="nw-row" href={n.url} target="_blank" rel="noopener noreferrer">
            <span class="nw-dot nw-{s}" title="{SENT_LABEL[s]} sentiment"></span>
            <span class="nw-body">
              <span class="nw-title">{n.title}</span>
              <span class="nw-meta">{n.source}{#if n.at} · {ago(n.at)} ago{/if}</span>
            </span>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  <!-- related stocks — 4 standalone 1×1 cards -->
  {#if related?.length}
    {#each related as r (r.ticker)}
      {@const sp = sparkPath(r.spark, r.prevClose)}
      {@const up = (r.dayPct ?? 0) >= 0}
      <button class="w rel-card" onclick={() => openRelated(r)}>
        <span class="rel-tkr">{r.ticker}</span>
        <span class="rel-name">{r.name}</span>
        <span class="rel-px">{money(r.price)}</span>
        <span class="rel-day {up ? 'up' : 'down'}">{r.dayPct != null ? pctS(r.dayPct) : '—'}</span>
        {#if sp}
          <svg class="rel-spark" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
            {#if sp.prevY != null}<line x1="0" y1={sp.prevY} x2="100" y2={sp.prevY} stroke="var(--muted)" stroke-width="0.7" stroke-dasharray="1.5 2.4" />{/if}
            <path d={sp.area} fill={up ? 'var(--gain)' : 'var(--loss)'} opacity="0.12" />
            <path d={sp.line} fill="none" stroke={up ? 'var(--gain)' : 'var(--loss)'} stroke-width="1.6" vector-effect="non-scaling-stroke" />
          </svg>
        {/if}
      </button>
    {/each}
  {/if}

  {#if stock._mock}<div class="sp-mock">demo data</div>{/if}
</div>

<style>
  /* ── the widget grid: 4 columns, paper shows through the gaps ── */
  .spg { position: relative; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px;
    align-content: start; }
  .w { min-width: 0; box-sizing: border-box; background: var(--surface);
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .w-h { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: var(--muted); display: flex; align-items: baseline; gap: 8px; }
  .w-h-sub { margin-left: auto; font-family: var(--mono); font-size: 9px; font-weight: 700;
    text-transform: none; letter-spacing: .04em; color: var(--muted); }

  /* header widget — 4 × 0.5; back rides the system .btn top right, watch is a
     .btn-line pill in the quote row */
  /* locked to --title-h so the watchlist (no position row) header matches the
     taller holdings header — space-between drops the watch button where the
     position row would sit. min-height (not height) so a wrapped position row is
     never clipped; --title-h is sized to fit the holdings content. */
  .w-head { grid-column: 1 / -1; min-height: var(--title-h, 152px); display: flex; flex-direction: column;
    justify-content: space-between; gap: 10px; padding: 12px 16px 14px; }
  .hw-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .hw-back span { font-size: 15px; line-height: 1; }
  .hw-crumb { font-family: var(--mono); font-size: 11.5px; color: var(--muted); }
  .hw-watch { align-self: flex-end; }
  /* previously-held: realized P&L stacked above the watch pill, right-aligned */
  .hw-prev { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
  .hw-main { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .hw-name { margin: 0 0 5px; font-family: var(--sans); font-size: 20px; font-weight: 700;
    letter-spacing: -.01em; line-height: 1.1; }
  .hw-quote { display: flex; align-items: baseline; gap: 11px; flex-wrap: wrap; }
  .hw-px { font-family: var(--mono); font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1; }
  .hw-day { font-family: var(--mono); font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
  /* position row: abbreviated labels (sh/avg/val/wt) + a modest gap trim let the
     five stats fit on ONE line at the narrow stage width, so the holdings header
     stays compact (~150) instead of wrapping to a tall two-line block. Figures
     keep their full size for legibility. */
  .hw-pos { display: flex; align-items: baseline; gap: 6px 12px; flex-wrap: wrap; }
  .pos-ret { display: inline-flex; align-items: baseline; gap: 7px; }
  .pos-ret b { font-family: var(--mono); font-size: 17px; font-weight: 700; line-height: 1; }
  .pos-ret small { font-family: var(--mono); font-size: 11px; font-weight: 700; opacity: .85; }
  .pos-kv { display: inline-flex; align-items: baseline; gap: 6px; }
  .pos-kv span { font-family: var(--sans); font-size: 9.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--muted); }
  .pos-kv b { font-family: var(--mono); font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }

  /* chart widget — 4 × 2 */
  .w-chart { grid-column: 1 / -1; height: 440px; padding: 14px 16px; }

  /* key stats widget — 4 × 1, three columns */
  .w-stats { grid-column: 1 / -1; padding: 12px 16px 14px; display: flex; flex-direction: column; gap: 8px; }
  .ks-cols { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 32px; flex: 1; }
  .ks-col { min-width: 0; }
  .g-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 6.5px 0;
    border-bottom: var(--bw) solid var(--hairline); }
  .ks-col .g-row:last-child { border-bottom: 0; }
  .g-row span { font-family: var(--sans); font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .02em; color: var(--muted); white-space: nowrap; }
  .g-row b { font-family: var(--mono); font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* analyst outlook — two BORDERLESS cells (span 2 each); ring and forecast
     each sit dead-centre in their cell (no legend — the ring's segments +
     hover core carry the buy/hold/sell read) */
  .w-bare { grid-column: span 2; min-height: 188px; display: flex; align-items: center;
    justify-content: center; padding: 6px 8px; }
  .w-ratings :global(.rgx) { height: auto; }

  .fc-h { grid-column: 1 / -1; font-family: var(--sans); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); margin-bottom: 2px; }
  .fc-grid { position: relative; width: min(100%, 360px); display: grid; grid-template-columns: 56px 1fr;
    row-gap: 8px; align-items: center; }
  .fc-label { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .04em; color: var(--muted); }
  .fc-track { position: relative; min-width: 0; height: 18px; display: flex; align-items: center; gap: 8px; }
  .fc-bar { box-sizing: border-box; height: 100%; min-width: 12px; flex: 0 0 auto;
    background: var(--ink); border-radius: 3px; }
  .fc-fig { font-family: var(--mono); font-size: 11.5px; font-weight: 700; color: var(--ink); white-space: nowrap; }
  .fc-fig small { font-size: 10px; }
  .fc-cur-track { height: 22px; }
  .fc-cur { position: absolute; top: 2px; transform: translateX(-50%); }
  /* dashed marker line rises from the pill up through the three bars */
  .fc-cur::before { content: ''; position: absolute; left: 50%; bottom: 100%; height: 82px; width: 0;
    border-left: 1.5px dashed color-mix(in srgb, var(--ink) 40%, transparent); pointer-events: none; }
  .fc-cur-pill { position: relative; font-family: var(--mono); font-size: 10px; font-weight: 700; white-space: nowrap;
    color: var(--ink); background: var(--paper); border: var(--bw) solid var(--ink); border-radius: 999px; padding: 2px 8px; }

  /* news widget — 4×1; headline rows split by hairlines, sentiment dot leads.
     Link styling matches MarketPulse: always underlined, ink on hover. */
  .w-news { grid-column: 1 / -1; display: flex; flex-direction: column; gap: 4px; padding: 12px 16px 6px; }
  .nw-list { display: flex; flex-direction: column; }
  .nw-row { display: flex; align-items: flex-start; gap: 11px; padding: 9px 0 10px;
    border-top: var(--bw) solid var(--hairline); text-decoration: none; }
  .nw-row:first-child { border-top: 0; }
  .nw-dot { flex: 0 0 auto; width: 9px; height: 9px; margin-top: 4px; border-radius: 50%;
    border: var(--bw) solid var(--ink); }
  .nw-pos { background: var(--gain); }
  .nw-neu { background: var(--yellow); }
  .nw-neg { background: var(--loss); }
  .nw-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .nw-title { font-family: var(--sans); font-size: 12.5px; font-weight: 600; line-height: 1.4; color: var(--ink);
    text-decoration: underline; text-underline-offset: 2.5px;
    text-decoration-color: color-mix(in srgb, var(--ink) 30%, transparent);
    transition: text-decoration-color .15s ease;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .nw-row:hover .nw-title { text-decoration-color: var(--ink); }
  .nw-meta { font-family: var(--mono); font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }

  /* related stock cards — 1 × 1 each */
  .rel-card { grid-column: span 1; display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
    padding: 11px 13px 0; cursor: pointer; font: inherit; color: var(--ink); text-align: left; overflow: hidden;
    transition: transform .12s ease, box-shadow .12s ease; }
  .rel-card:hover { transform: translate(-2px, -2px); box-shadow: var(--sh-pop); }
  .rel-card:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0 var(--ink); }
  .rel-tkr { font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .06em; color: var(--muted); }
  .rel-name { width: 100%; font-family: var(--sans); font-size: 13px; font-weight: 700; line-height: 1.2;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rel-px { font-family: var(--mono); font-size: 12.5px; font-weight: 700; color: var(--ink); margin-top: 3px; }
  .rel-day { font-family: var(--mono); font-size: 13.5px; font-weight: 700; }
  .rel-spark { display: block; width: calc(100% + 26px); margin: 7px -13px 0; height: 36px; }

  .sp-mock { position: absolute; bottom: -18px; right: 2px; pointer-events: none;
    font-family: var(--mono); font-size: 8px; text-transform: uppercase; letter-spacing: .14em; color: var(--muted); opacity: .5; }

  .up { color: var(--gain); } .down { color: var(--loss); }

  @media (max-width: 900px) {
    .spg { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .w-head, .w-chart, .w-stats, .w-bare { grid-column: 1 / -1; }
    .rel-card { grid-column: span 1; }
    .w-chart { height: 340px; }
    .ks-cols { grid-template-columns: 1fr; column-gap: 0; }
  }

  /* phone (mobile stock sheet): tighter rhythm, shorter chart, self-sized header */
  @media (max-width: 700px) {
    .spg { gap: 12px; }
    .w-head { min-height: 0; }
    .w-chart { height: 300px; padding: 10px 8px; }
    .hw-px { font-size: 24px; }
    .hw-pos { gap: 4px 10px; }
    .w-bare { min-height: 0; padding: 14px 8px; }
  }
</style>

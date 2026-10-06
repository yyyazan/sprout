<script>
  // Stock view as a WIDGET GRID — Google Finance's content in Sprout's widget
  // language. Strict 4-column grid, canvas showing through the gaps: header
  // (4×0.5: crumb + back top-right, name/quote, position-or-list-picker) → chart (4×2)
  // → key stats (4×1, three columns) → analyst outlook (two BARE centred cells:
  // ratings RingGauge | forecast range) → news (4×1, sentiment-dotted headlines)
  // → related stocks (4 × 1×1 cards). Chrome-less so the dashboard stage and
  // the modal both render this grid directly on the page.
  //
  // A fund (index or otherwise) keeps the header, chart, news and related, and
  // swaps what doesn't apply: key stats trade P/E, EPS, market cap and earnings
  // for net assets, yield and cost; the analyst pair becomes top holdings and
  // sectors (what's inside, in the same bare-cell slot).
  import { onMount } from 'svelte';
  import StockChart from './StockChart.svelte';
  import RingGauge from './RingGauge.svelte';
  import TickerBadge from './TickerBadge.svelte';
  import { mockStock, fmtCap, fmtVol } from '$lib/mockStock.js';
  import { cachedStock, cachedRelated, prefetch } from '$lib/stockCache.js';
  import { holdings, kinds, noteKinds, openStock, cardToHolding } from '$lib/stores.js';
  import ListPicker from './ListPicker.svelte';

  // showClose=false when a host provides its own way back (the dashboard stage's
  // portfolio strip); the modal keeps the ✕.
  let { ticker, name = null, holding = null, onClose, glyph = '✕', showClose = true } = $props();

  const owned = $derived(!!holding);

  // ── data: first frame from the shared cache when it has this ticker (hover
  // prefetch, a revisit), else skeletons. A cached copy over 30s old is
  // refetched and swapped in place. `late` = the data came after a skeleton,
  // so its sections fade in; a cache hit just appears. Mock numbers only
  // stand in when the fetch fails.
  let remote = $state(null);
  let failed = $state(false);
  let late = $state(false);
  $effect(() => {
    const t = ticker;
    if (!t) { remote = null; return; }
    let cancelled = false;
    const hit = cachedStock.peek(t);
    remote = hit ?? null;
    failed = false;
    late = !hit;
    cachedStock.within(30_000, t)
      .then((r) => { if (!cancelled) remote = r; })
      .catch(() => { if (!cancelled && !remote) failed = true; });
    return () => { cancelled = true; };
  });
  const ready = $derived(!!remote && remote.ticker === (ticker || '').toUpperCase());
  // ── fund layout: kind comes with the payload; before it lands, whatever the
  // kinds store already knows (held funds, listed funds) picks the skeleton ──
  const isFund = $derived(ready ? (remote.kind ?? 'stock') !== 'stock' : !!$kinds[(ticker || '').toUpperCase()]);
  $effect(() => { if (ready) noteKinds({ [remote.ticker]: remote.kind ?? 'stock' }); });
  const fund = $derived(ready && isFund ? remote.fund ?? null : null);
  const kindLabel = $derived(remote?.kind === 'index' ? 'Index fund' : 'Fund');
  // Morningstar's "Trading--Leveraged Equity" / "Large Blend" → sentence case
  const sentence = (c) => (c ? c.replace(/^Trading--/, '').toLowerCase().replace(/^./, (m) => m.toUpperCase()) : '');
  // what the position costs to hold, in dollars: your value, or a $1,000 stake when you hold none
  const yearlyCost = $derived(fund?.expense == null ? null : fund.expense * (owned ? (stock.mktValue ?? 0) : 1000));
  const topHoldings = $derived(fund?.holdings ?? []);
  const topTotal = $derived(topHoldings.reduce((a, h) => a + h.weight, 0));
  // seven biggest sectors, the rest folded into one row; a single-sector fund has no mix to show
  const sectorRows = $derived.by(() => {
    const all = fund?.sectors ?? [];
    if (all.length < 2) return [];
    const head = all.slice(0, 7), tail = all.slice(7).reduce((a, r) => a + r.weight, 0);
    return tail > 0.0005 ? [...head, { name: 'Other', weight: tail }] : head;
  });
  const wPct = (w) => (w * 100 < 10 ? (w * 100).toFixed(1) : Math.round(w * 100)) + '%';
  const ratioPct = (r) => (r == null ? '—' : (r * 100).toFixed(2) + '%');
  const peakOf = (rows) => Math.max(1e-9, ...rows.map((r) => r.weight));

  // what the header can show before the payload: a holding's own card numbers
  const quoteKnown = $derived(ready || failed || owned);
  const statsKnown = $derived(ready || failed);

  // related stocks ride their own fetch so they never slow the main payload
  let related = $state(null);
  let relatedLate = $state(false);
  $effect(() => {
    const t = ticker;
    if (!t) { related = null; return; }
    let cancelled = false;
    const hit = cachedRelated.peek(t);
    related = hit ? hit.related ?? [] : null;
    relatedLate = !hit;
    cachedRelated(t).then((r) => {
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
    if (!ready) return m;
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

  // 12-month targets: the average is the headline; low→high is a range on a
  // price axis that also spans today's price, so "now" always sits on it
  const forecast = $derived.by(() => {
    const a = analyst, p = stock.price;
    if (!a || a.targetMean == null || !p) return null;
    const vs = (v) => (v / p - 1) * 100;
    const out = { mean: a.targetMean, meanPct: vs(a.targetMean), range: null };
    const lo = a.targetLow, hi = a.targetHigh;
    if (lo != null && hi != null && hi > lo) {
      const d0 = Math.min(lo, p), d1 = Math.max(hi, p), pad = (d1 - d0) * 0.04;
      const x = (v) => ((v - d0 + pad) / (d1 - d0 + 2 * pad)) * 100;
      out.range = {
        low: lo, high: hi, lowPct: vs(lo), highPct: vs(hi),
        xLow: x(lo), xHigh: x(hi), xNow: x(p), xMean: x(a.targetMean),
      };
    }
    return out;
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
  const pctS = (n) => (n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(1) + '%');
  const usdS = (n) => (n == null ? '—' : (n >= 0 ? '+$' : '−$') + f(Math.abs(n)));
  const money = (n) => (n == null ? '—' : '$' + f(n));
  const sUsd = (n) => (n == null ? '—' : (n < 0 ? '−$' : '$') + f(Math.abs(n)));
  const dayAbs = $derived(
    stock.prevClose && stock.price ? stock.price - stock.prevClose : null
  );

  // Lifetime P&L + return for this ticker. /api/stock sends the sold side (closed
  // FIFO lots: realized $, their cost, shares, avg buy/sell); the open position
  // adds its own unrealized $ and cost. Return = total P&L over everything ever
  // bought. Tickers we've fully sold have no card, so they land in prevHeld.
  const sold = $derived(remote?.lifetime ?? null);
  const openCost = $derived(owned && stock.avgCost != null ? stock.avgCost * (stock.shares ?? 0) : 0);
  const lifePnl = $derived(sold ? (owned ? (stock.plAbs ?? 0) : 0) + sold.realized : null);
  const lifeCost = $derived(sold ? sold.cost + openCost : null);
  const lifePct = $derived(lifeCost ? (lifePnl / lifeCost) * 100 : null);
  const lifeDir = $derived((lifePnl ?? 0) >= 0 ? 'up' : 'down');
  const prevHeld = $derived(!owned && !!sold);
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
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
</script>

<div class="spg">
  <!-- header widget — 4 × 0.5: crumb, back (top right), identity, quote, position or list picker -->
  <section class="w w-head">
    <div class="hw-top">
      <span class="hw-crumb"><TickerBadge sym={ticker} size="md" />{#if statsKnown}{#if isFund}<span class="hw-kind">{kindLabel}</span>{#if fund?.category}<span class="hw-sector">{sentence(fund.category)}</span>{/if}{:else if stock.sector && stock.sector !== '—'}<span class="hw-sector">{stock.sector}</span>{/if}{:else}<span class="skel skel-t" style="width:76px"></span>{/if}</span>
      {#if showClose}
        <button class="btn btn-sm btn-quiet hw-back" onclick={() => onClose?.()}>
          <span aria-hidden="true">{glyph === '←' ? '←' : '✕'}</span>
          {glyph === '←' ? 'portfolio' : 'close'}
        </button>
      {/if}
    </div>
    <div class="hw-main">
      <div class="hw-id">
        <h2 class="hw-name">{stock.name}</h2>
        <div class="hw-quote">
          {#if quoteKnown}
            <span class="hw-px">${f(stock.price)}</span>
            <span class="hw-day {stock.dayPct >= 0 ? 'up' : 'down'}">
              {#if dayAbs != null}<span>{usdS(dayAbs)}</span>{/if}<span class="pct-pill {stock.dayPct >= 0 ? 'up' : 'down'}">{pctS(stock.dayPct)}</span><span class="hw-tf">today</span>
            </span>
          {:else}
            <span class="skel sk-px"></span><span class="skel skel-t" style="width:120px"></span>
          {/if}
        </div>
      </div>
      {#if owned}
        {#if sold}
          <!-- the whole ticker's return, sold lots included — right of the quote, where the
               row below has no room; without sells it equals the position, so it's skipped -->
          <div class="hw-life">
            <span class="hw-pos-label">Lifetime</span>
            <span class="pos-ret {lifeDir}">
              <b class="pct-pill {lifeDir}">{pctS(lifePct)}</b><small>{usdS(lifePnl)}</small>
            </span>
          </div>
        {/if}
        <div class="hw-pos">
          <span class="hw-pos-label">Your position</span>
          <span class="pos-ret {(stock.plPct ?? 0) >= 0 ? 'up' : 'down'}">
            <b class="pct-pill {(stock.plPct ?? 0) >= 0 ? 'up' : 'down'}">{pctS(stock.plPct)}</b><small>{usdS(stock.plAbs)}</small>
          </span>
          <span class="pos-kv"><span>Shares</span><b>{f(stock.shares)}</b></span>
          <span class="pos-kv"><span>Avg</span><b>${f(stock.avgCost)}</b></span>
          <span class="pos-kv"><span>Value</span><b>${f(stock.mktValue)}</b></span>
          <span class="pos-kv"><span>Weight</span><b>{stock.weight != null ? stock.weight + '%' : '—'}</b></span>
        </div>
      {:else if prevHeld}
        <!-- fully sold out of this ticker: the same row a holding gets, on the
             sold side — total return, shares sold, avg buy → avg sell -->
        <div class="hw-watch"><ListPicker {ticker} /></div>
        <div class="hw-pos">
          <span class="hw-pos-label">Previously held</span>
          <span class="pos-ret {lifeDir}">
            <b class="pct-pill {lifeDir}">{pctS(lifePct)}</b><small>{usdS(lifePnl)}</small>
          </span>
          <span class="pos-kv"><span>Shares sold</span><b>{f(sold.shares)}</b></span>
          <span class="pos-kv"><span>Avg buy</span><b>${f(sold.avgBuy)}</b></span>
          <span class="pos-kv"><span>Avg sell</span><b>${f(sold.avgSell)}</b></span>
        </div>
      {:else}
        <div class="hw-watch"><ListPicker {ticker} /></div>
      {/if}
    </div>
  </section>

  <!-- chart widget — 4 × 2; .chart-widget is the size both charts share -->
  <section class="w-chart chart-widget">
    {#key ticker}
      <StockChart {ticker} history={remote?.history ?? null} price={stock.price} />
    {/key}
  </section>

  <!-- key stats widget — 4 × 1, three columns -->
  <section class="w w-stats">
    <div class="w-h">Key stats</div>
    <div class="ks-cols">
      <div class="ks-col">
        <div class="g-row"><span>Open</span><b>{#if statsKnown}{money(stock.open)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        <div class="g-row"><span>High</span><b>{#if statsKnown}{money(stock.dayHigh)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        <div class="g-row"><span>Low</span><b>{#if statsKnown}{money(stock.dayLow)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        <div class="g-row"><span>Prev close</span><b>{#if statsKnown}{money(stock.prevClose)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
      </div>
      {#if isFund}
        <div class="ks-col">
          <div class="g-row"><span>Volume</span><b>{#if statsKnown}{stock.volume != null ? fmtVol(stock.volume) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Avg volume</span><b>{#if statsKnown}{stock.avgVolume != null ? fmtVol(stock.avgVolume) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Net assets</span><b>{#if statsKnown}{fund?.assets != null ? fmtCap(fund.assets) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Yield</span><b>{#if statsKnown}{fund?.yield ? ratioPct(fund.yield) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        </div>
        <div class="ks-col">
          <div class="g-row"><span>Expense ratio</span><b>{#if statsKnown}{ratioPct(fund?.expense)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Category avg</span><b>{#if statsKnown}{ratioPct(fund?.categoryExpense)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>{owned ? 'Your cost a year' : 'Cost per $1,000'}</span><b>{#if statsKnown}{yearlyCost != null ? money(yearlyCost) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Family</span><b>{#if statsKnown}{fund?.family ?? '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        </div>
      {:else}
        <div class="ks-col">
          <div class="g-row"><span>Volume</span><b>{#if statsKnown}{stock.volume != null ? fmtVol(stock.volume) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Avg volume</span><b>{#if statsKnown}{stock.avgVolume != null ? fmtVol(stock.avgVolume) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Market cap</span><b>{#if statsKnown}{stock.marketCap != null ? fmtCap(stock.marketCap) : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>P/E ratio</span><b>{#if statsKnown}{stock.pe ?? '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        </div>
        <div class="ks-col">
          <div class="g-row"><span>EPS</span><b>{#if statsKnown}{sUsd(stock.eps)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Dividend yield</span><b>{#if statsKnown}{stock.divYield ? stock.divYield + '%' : '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Beta</span><b>{#if statsKnown}{stock.beta ?? '—'}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
          <div class="g-row"><span>Earnings</span><b>{#if statsKnown}{fmtEarn(remote?.earningsDate)}{:else}<span class="skel skel-t sk-v"></span>{/if}</b></div>
        </div>
      {/if}
    </div>
  </section>

  <!-- analyst outlook — two BARE widgets side by side, centred like the
       dashboard's ring row: ratings on the shared RingGauge, forecast range -->
  {#if !statsKnown && isFund}
    {#each [0, 1] as i (i)}
      <section class="w-fund" aria-hidden="true">
        <span class="skel skel-t" style="width:84px"></span>
        {#each [0, 1, 2, 3, 4, 5] as r (r)}<span class="skel fd-sk"></span>{/each}
      </section>
    {/each}
  {:else if !statsKnown}
    <section class="w-bare w-ratings" aria-hidden="true"><span class="skel sk-ring"></span></section>
    <section class="w-forecast" aria-hidden="true">
      <span class="skel skel-t" style="width:112px"></span>
      <span class="skel sk-hero"></span>
      <span class="skel skel-t" style="width:84px;margin-top:6px"></span>
      <span class="skel sk-track"></span>
      <div class="fc-ends"><span class="skel skel-t" style="width:118px"></span><span class="skel skel-t" style="width:118px"></span></div>
    </section>
  {:else if isFund}
    <!-- what's inside: the ten biggest holdings and the sector mix, bars on the
         forecast track's spec; a leveraged or crypto fund has neither, so no cell -->
    {#if topHoldings.length}
      {@const peak = peakOf(topHoldings)}
      <section class="w-fund" class:solo={!sectorRows.length} class:arrive={late}>
        <div class="fd-head"><span class="w-h">Top holdings</span><span class="fd-sub">{wPct(topTotal)} of the fund</span></div>
        <div class="fd-rows">
          {#each topHoldings as h (h.symbol)}
            <button class="fd-row fd-go" aria-label="{h.name}" onclick={() => openRelated({ ticker: h.symbol, name: h.name })}>
              <span class="fd-key"><TickerBadge sym={h.symbol} /></span>
              <span class="fd-track"><span class="fd-bar" style="width:{(h.weight / peak) * 100}%"></span></span>
              <span class="fd-v">{wPct(h.weight)}</span>
            </button>
          {/each}
        </div>
      </section>
    {/if}
    {#if sectorRows.length}
      {@const peak = peakOf(sectorRows)}
      <section class="w-fund w-sectors" class:solo={!topHoldings.length} class:arrive={late}>
        <div class="fd-head"><span class="w-h">Sectors</span></div>
        <div class="fd-rows">
          {#each sectorRows as r (r.name)}
            <div class="fd-row">
              <span class="fd-key fd-name">{r.name}</span>
              <span class="fd-track"><span class="fd-bar" style="width:{(r.weight / peak) * 100}%"></span></span>
              <span class="fd-v">{wPct(r.weight)}</span>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {:else if analyst && (ratingSegs || forecast)}
    {#if ratingSegs}
      <section class="w-bare w-ratings" class:arrive={late}>
        <RingGauge heroSize={15}
          segments={[
            { key: 'buy', color: 'var(--gain)', value: ratingSegs.buy, tag: 'Buy', hero: String(ratingSegs.buy), sub: 'analysts' },
            { key: 'hold', color: 'var(--yellow)', value: ratingSegs.hold, tag: 'Hold', hero: String(ratingSegs.hold), sub: 'analysts' },
            { key: 'sell', color: 'var(--loss)', value: ratingSegs.sell, tag: 'Sell', hero: String(ratingSegs.sell), sub: 'analysts' },
          ]}
          idle={{ tag: 'Ratings', hero: verdict ?? '—', sub: analyst.count ? `${analyst.count} analysts` : null,
            heroColor: verdictTone === 'up' ? 'var(--gain)' : verdictTone === 'down' ? 'var(--loss)' : 'var(--ink)' }} />
      </section>
    {/if}
    {#if forecast}
      {@const g = forecast.range}
      <section class="w-forecast" class:arrive={late}>
        <span class="w-h">12-month forecast</span>
        <div class="fc-hero">
          <span class="fc-avg">${f(forecast.mean)}</span>
          <span class="fc-pct pct-pill {forecast.meanPct >= 0 ? 'up' : 'down'}">{pctS(forecast.meanPct)}</span>
        </div>
        <span class="fc-sub"><span class="fc-dot" aria-hidden="true"></span>Average target</span>
        {#if g}
          <!-- range on a price axis: below today = downside (loss), above = upside (gain) -->
          <div class="fc-track">
            <span class="fc-now" style="left:{g.xNow}%;transform:translateX(-{g.xNow}%)">
              <span class="fc-k">Now</span> ${f(stock.price)}
            </span>
            {#if g.xNow > g.xLow}
              <span class="fc-seg down" class:solo={g.xNow >= g.xHigh} style="left:{g.xLow}%;width:{Math.min(g.xNow, g.xHigh) - g.xLow}%"></span>
            {/if}
            {#if g.xNow < g.xHigh}
              <span class="fc-seg up" class:solo={g.xNow <= g.xLow} style="left:{Math.max(g.xNow, g.xLow)}%;width:{g.xHigh - Math.max(g.xNow, g.xLow)}%"></span>
            {/if}
            <span class="fc-tick" style="left:{g.xNow}%"></span>
            <span class="fc-dot fc-mean" style="left:{g.xMean}%"></span>
          </div>
          <div class="fc-ends">
            <span class="fc-end"><span class="fc-k">Low</span> ${f(g.low)} <span class="fc-pct pct-pill {g.lowPct >= 0 ? 'up' : 'down'}">{pctS(g.lowPct)}</span></span>
            <span class="fc-end"><span class="fc-k">High</span> ${f(g.high)} <span class="fc-pct pct-pill {g.highPct >= 0 ? 'up' : 'down'}">{pctS(g.highPct)}</span></span>
          </div>
        {/if}
      </section>
    {/if}
  {/if}

  <!-- news — full-width headline list; the dot is the sentiment read
       (green = positive · yellow = neutral · red = negative, keyword heuristic) -->
  {#if !statsKnown}
    <section class="w w-news" aria-hidden="true">
      <span class="skel skel-t" style="width:44px"></span>
      <div class="nw-list">
        <!-- bars sit in the real title/meta classes, so each row is a real row's height;
             one headline wraps, as they usually do -->
        {#each [[78], [96, 44], [64], [86]] as lines}
          <div class="nw-row">
            <span class="skel sk-dot"></span>
            <span class="nw-body sk-body">
              <span class="nw-title">{#each lines as wd}<span class="skel skel-t" style="width:{wd}%"></span>{/each}</span>
              <span class="nw-meta"><span class="skel skel-t" style="width:24%"></span></span>
            </span>
          </div>
        {/each}
      </div>
    </section>
  {:else if remote?.news?.length}
    <section class="w w-news" class:arrive={late}>
      <div class="w-h">News</div>
      <div class="nw-list">
        {#each remote.news as n (n.url ?? n.title)}
          {@const s = sentimentOf(n.title)}
          <a class="nw-row" href={n.url} target="_blank" rel="noopener noreferrer">
            <span class="nw-dot nw-{s}" title="{SENT_LABEL[s]} sentiment"></span>
            <span class="nw-body">
              <span class="nw-title">{n.title}</span>
              <span class="nw-meta"><span class="nw-src">{n.source}</span>{#if n.at}<span>{ago(n.at)} ago</span>{/if}</span>
            </span>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  <!-- related stocks — 4 standalone 1×1 cards -->
  {#if related == null}
    {#each [0, 1, 2, 3] as i (i)}
      <div class="w rel-card sk-rel" aria-hidden="true">
        <span class="skel sk-badge"></span>
        <span class="skel skel-t" style="width:80%"></span>
        <span class="skel skel-t" style="width:46%"></span>
        <span class="skel skel-t" style="width:34%"></span>
        <span class="skel sk-spark"></span>
      </div>
    {/each}
  {:else if related.length}
    {#each related as r (r.ticker)}
      {@const sp = sparkPath(r.spark, r.prevClose)}
      {@const up = (r.dayPct ?? 0) >= 0}
      <button class="w rel-card" class:arrive={relatedLate} use:prefetch={r.ticker} onclick={() => openRelated(r)}>
        <span class="rel-tkr"><TickerBadge sym={r.ticker} /></span>
        <span class="rel-name">{r.name}</span>
        <span class="rel-px">{money(r.price)}</span>
        <span class="rel-day pct-pill {up ? 'up' : 'down'}">{r.dayPct != null ? pctS(r.dayPct) : '—'}</span>
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

  {#if failed}<div class="sp-mock">Demo data</div>{/if}
</div>

<style>
  /* ── the widget grid: 4 columns, paper shows through the gaps ── */
  .spg { position: relative; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px;
    align-content: start; }
  .w { min-width: 0; box-sizing: border-box; background: var(--surface);
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  /* widget title = the card title spec (13/600 ink, sentence case) */
  .w-h { font-size: var(--fs-title); font-weight: 600; line-height: 1.2; color: var(--ink); }

  /* header widget — 4 × 0.5; back rides the system .btn top right, the list picker is a
     .btn-line pill in the quote row */
  /* locked to --title-h so a non-held (no position row) header matches the
     taller holdings header — space-between drops the list picker where the
     position row would sit. min-height (not height) so a wrapped position row is
     never clipped; --title-h is sized to fit the holdings content. */
  .w-head { grid-column: 1 / -1; min-height: var(--title-h, 152px); display: flex; flex-direction: column;
    justify-content: space-between; gap: 10px; padding: 12px 16px 14px; }
  .hw-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .hw-back span { font-size: 15px; line-height: 1; }
  .hw-crumb { display: inline-flex; align-items: center; gap: 8px; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .hw-sector { white-space: nowrap; }
  .hw-kind { white-space: nowrap; color: var(--ink); }
  .hw-watch { align-self: flex-end; }
  .hw-main { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .hw-name { margin: 0 0 5px; font-size: 20px; font-weight: 600; letter-spacing: -.01em; line-height: 1.1; }
  .hw-quote { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .hw-px { font-family: var(--num); font-size: 28px; font-weight: 600; letter-spacing: -.01em;
    font-variant-numeric: tabular-nums; line-height: 1; }
  .hw-day { display: inline-flex; align-items: center; gap: 6px; font-family: var(--num); font-size: 13px;
    font-weight: 500; font-variant-numeric: tabular-nums; }
  .hw-tf { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  /* position row: abbreviated labels (sh/avg/val/wt) + a modest gap trim let the
     five stats fit on ONE line at the narrow stage width, so the holdings header
     stays compact (~150) instead of wrapping to a tall two-line block. Figures
     keep their full size for legibility. */
  .hw-pos { display: flex; align-items: baseline; gap: 6px 12px; flex-wrap: wrap; }
  /* the row always sits under the quote; what shares the quote line (list picker for a
     previously-held ticker, lifetime for a holding) goes right */
  .hw-pos { flex-basis: 100%; }
  .hw-life { display: flex; align-items: baseline; gap: 6px 12px; }
  .hw-pos-label { font-size: var(--fs-meta); font-weight: 600; color: var(--muted); }
  .pos-ret { display: inline-flex; align-items: baseline; gap: 7px; }
  .pos-ret b { font-family: var(--num); font-size: 15px; font-weight: 600; line-height: 1.2; font-variant-numeric: tabular-nums; }
  .pos-ret small { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; font-variant-numeric: tabular-nums; }
  .pos-kv { display: inline-flex; align-items: baseline; gap: 5px; }
  .pos-kv span { font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .pos-kv b { font-family: var(--num); font-size: 13px; font-weight: 500; font-variant-numeric: tabular-nums; }

  /* chart widget — 4 × 2; box size comes from the global .chart-widget */
  .w-chart { grid-column: 1 / -1; min-width: 0; }

  /* key stats widget — 4 × 1, three columns */
  .w-stats { grid-column: 1 / -1; padding: 12px 16px 14px; display: flex; flex-direction: column; gap: 8px; }
  .ks-cols { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 24px; flex: 1; margin-top: 2px; }
  .ks-col { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
  .ks-col + .ks-col { border-left: var(--bw) solid var(--hairline); padding-left: 24px; }
  .g-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .g-row span { font-size: var(--fs-body); font-weight: 500; color: var(--muted); white-space: nowrap; }
  .g-row b { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; font-variant-numeric: tabular-nums;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* analyst outlook — ratings ring is a BARE cell, centred like the dashboard's
     ring row (its segments + hover core carry the read, no card needed around
     a graphic). Forecast is bare too now, so the pair reads as one outlook
     row instead of a boxed list next to a naked ring. */
  .w-bare { grid-column: span 2; min-height: 188px; display: flex; align-items: center;
    justify-content: center; padding: 6px 8px; }
  .w-ratings :global(.rgx) { height: auto; }

  /* fund cells — top holdings | sectors, bare like the analyst pair they stand in for.
     A row is key · bar · weight; the bar is the forecast track's spec (6px, 3px corners,
     hairline track) in muted, scaled to the cell's biggest row. Holdings rows open that
     ticker, so they take the ink hairline on hover like the Log's rows. */
  .w-fund { grid-column: span 2; min-width: 0; display: flex; flex-direction: column; gap: 4px; padding: 12px 16px 14px; }
  .w-fund.solo { grid-column: 1 / -1; }
  /* the title row is the same height in both cells (the holdings total rides it, right) so the rows start level */
  .fd-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; min-height: 18px; }
  .fd-sub { font-size: var(--fs-meta); font-weight: 500; color: var(--muted); white-space: nowrap; }
  .fd-rows { display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }
  .fd-row { display: grid; grid-template-columns: 72px minmax(0, 1fr) 40px; align-items: center; column-gap: 10px;
    min-height: 26px; padding: 0 6px; margin: 0 -6px; border: 0; border-radius: var(--r); background: transparent;
    font: inherit; color: inherit; text-align: left; }
  .fd-go { cursor: pointer; }
  .fd-go:hover, .fd-go:focus-visible { box-shadow: inset 0 0 0 var(--bw) var(--ink); outline: none; }
  .fd-key { min-width: 0; display: flex; }
  .fd-name { font-size: var(--fs-body); font-weight: 500; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
  .fd-track { height: 6px; border-radius: 3px; background: var(--hairline); overflow: hidden; }
  .fd-bar { display: block; height: 100%; border-radius: 3px; background: var(--muted); }
  .fd-v { text-align: right; font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    font-variant-numeric: tabular-nums; }
  .fd-sk { height: 26px; }
  .w-sectors .fd-row { grid-template-columns: 112px minmax(0, 1fr) 40px; }

  /* forecast — bare like the ring beside it: title, the average target as the
     headline (hero + pct-pill), then low→high as a range on a price axis */
  .w-forecast { grid-column: span 2; min-height: 188px; box-sizing: border-box; display: flex; flex-direction: column;
    justify-content: center; padding: 12px 16px 14px; }
  .fc-hero { display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }
  .fc-avg { font-family: var(--num); font-size: var(--fs-hero); font-weight: 600; line-height: 1.05; letter-spacing: -.01em;
    color: var(--ink); font-variant-numeric: tabular-nums; }
  .fc-pct { font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; }
  .fc-sub { display: flex; align-items: center; gap: 6px; margin-top: 4px;
    font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .fc-k { color: var(--muted); font-family: var(--sans); }

  /* track: 8px range bar, 3px corners (the old bars' corner). Room above for
     the Now label, which slides from left- to right-aligned with its x so it
     never runs off either end. */
  .fc-track { position: relative; height: 8px; margin: 34px 0 10px; }
  .fc-track::before { content: ''; position: absolute; inset: 0; border-radius: 3px; background: var(--hairline); }
  .fc-seg { position: absolute; top: 0; bottom: 0; }
  .fc-seg.down { background: var(--loss); border-radius: 3px 0 0 3px; }
  .fc-seg.up { background: var(--gain); border-radius: 0 3px 3px 0; }
  .fc-seg.solo { border-radius: 3px; }
  .fc-tick { position: absolute; top: -5px; bottom: -5px; width: 0; border-left: var(--bw) solid var(--ink); }
  .fc-now { position: absolute; bottom: calc(100% + 8px); white-space: nowrap;
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--ink); font-variant-numeric: tabular-nums; }
  /* the average: an ink dot ringed in paper so it reads on either color */
  .fc-dot { display: inline-block; width: 9px; height: 9px; box-sizing: border-box; border-radius: 50%; background: var(--ink); }
  .fc-mean { position: absolute; top: 50%; width: 12px; height: 12px; margin: -6px 0 0 -6px;
    box-shadow: 0 0 0 2px var(--paper); }
  .fc-ends { display: flex; justify-content: space-between; gap: 8px; }
  .fc-end { display: inline-flex; align-items: baseline; gap: 5px; white-space: nowrap;
    font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink); font-variant-numeric: tabular-nums; }

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
  .nw-title { font-size: 13px; font-weight: 500; line-height: 1.4; color: var(--ink);
    text-decoration: underline; text-underline-offset: 2.5px;
    text-decoration-color: color-mix(in srgb, var(--ink) 30%, transparent);
    transition: text-decoration-color .15s ease;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .nw-row:hover .nw-title { text-decoration-color: var(--ink); }
  .nw-meta { display: flex; justify-content: space-between; gap: 8px; font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .nw-src { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* related stock cards — 1 × 1 each */
  .rel-card { grid-column: span 1; display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
    padding: 11px 13px 0; cursor: pointer; font: inherit; color: var(--ink); text-align: left; overflow: hidden;
    transition: transform .12s ease, box-shadow .12s ease; }
  .rel-card:hover { transform: translate(-2px, -2px); box-shadow: var(--sh-pop); }
  .rel-card:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0 var(--ink); }
  .rel-tkr { margin-bottom: 4px; }
  .rel-name { width: 100%; font-size: 13px; font-weight: 600; line-height: 1.2;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rel-px { font-family: var(--num); font-size: 13px; font-weight: 500; color: var(--ink); margin-top: 3px;
    font-variant-numeric: tabular-nums; }
  .rel-day { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; }
  .rel-spark { display: block; width: calc(100% + 26px); margin: 7px -13px 0; height: 36px; }

  /* ── skeleton parts: each sized like what it stands in for (see app.css .skel) ── */
  .sk-px { display: inline-block; width: 132px; height: 28px; }
  .sk-v { width: 52px; }
  .sk-ring { width: 168px; height: 168px; border-radius: 50%; background: none;
    border: 15px solid color-mix(in srgb, var(--ink) 10%, transparent); }
  .sk-hero { width: 128px; height: 24px; margin-top: 10px; }
  .sk-track { height: 8px; margin: 34px 0 10px; }
  .sk-dot { flex: 0 0 auto; width: 9px; height: 9px; margin-top: 4px; border-radius: 50%; }
  .sk-body { flex: 1; }
  .sk-rel { gap: 7px; height: 145px; padding-bottom: 0; cursor: default; }
  .sk-rel:hover { transform: none; box-shadow: var(--sh); }
  .sk-badge { width: 46px; height: 18px; margin-bottom: 2px; }
  .sk-spark { align-self: stretch; height: 36px; margin: auto -13px 0; border-radius: 0; }

  .sp-mock { position: absolute; bottom: -18px; right: 2px; pointer-events: none;
    font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }

  .up { color: var(--gain); } .down { color: var(--loss); }

  @media (max-width: 900px) {
    .spg { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .w-head, .w-chart, .w-stats, .w-bare, .w-forecast, .w-fund { grid-column: 1 / -1; }
    .rel-card { grid-column: span 1; }
    .ks-cols { grid-template-columns: 1fr; column-gap: 0; row-gap: 12px; }
    .ks-col + .ks-col { border-left: 0; padding-left: 0; }
  }

  /* phone (mobile stock sheet): tighter rhythm, shorter chart, self-sized header */
  @media (max-width: 700px) {
    .spg { gap: 12px; }
    .w-head { min-height: 0; }
    .hw-px { font-size: 24px; }
    .hw-pos { gap: 4px 10px; }
    .w-bare { min-height: 0; padding: 14px 8px; }
  }
</style>

<script>
  // The dashboard's MAIN widget — a stage with three modes instead of
  // full-screen overlays: the portfolio chart at rest, the stock view inline
  // when a holding/search result is opened, and an inline search panel for ⌘K.
  import PortfolioChart from './PortfolioChart.svelte';
  import StockPanel from './StockPanel.svelte';
  import TickerBadge from './TickerBadge.svelte';
  import DriversCard from './DriversCard.svelte';
  import { api } from '$lib/api.js';
  import { prefetch } from '$lib/stockCache.js';
  import { detail, searchOpen, holdings, closeStock, closeSearch, openSearch, openSearchResult, noteSearchKinds } from '$lib/stores.js';

  let { equity = { x: [], y: [] }, spy = null, twr = null, netInvested = null, drivers = null } = $props();

  // the chart's current window, which the Drivers title card explains
  let win = $state(null);

  // search wins over an open stock view (⌘K should always summon the palette);
  // closing search falls back to the stock still in $detail, then the chart
  const mode = $derived($searchOpen ? 'search' : $detail ? 'stock' : 'portfolio');

  // ── scroll: moving inside the stage behaves like a page change ──
  // Leaving the portfolio remembers where it was scrolled and coming back
  // restores it; opening a stock (or the next one from its related cards)
  // while scrolled past the stage's top starts at the top of the page.
  let stageEl = $state();
  const view = $derived(mode === 'stock' ? 'stock:' + $detail.ticker : mode);
  let lastView = 'portfolio';
  let homeY = 0;
  $effect.pre(() => {
    // before the DOM swaps, while scrollY still belongs to the old view
    if (view !== 'portfolio' && lastView === 'portfolio') homeY = window.scrollY;
  });
  $effect(() => {
    const v = view;
    if (v === lastView) return;
    lastView = v;
    if (v === 'portfolio') { window.scrollTo(0, homeY); return; }
    if (stageEl && window.scrollY > stageEl.getBoundingClientRect().top + window.scrollY) window.scrollTo(0, 0);
  });

  // ── persistent search strip ──
  // Always the first thing in the stage, whatever's beneath it: an idle button
  // that opens search, or (in search mode) the live query input itself — same
  // shape and place either way, a Google-Finance-style top search bar.

  // ── inline search (same behavior as the ⌘K palette, no scrim) ──
  let q = $state('');
  let results = $state([]);
  let active = $state(0);
  let loading = $state(false);
  let input = $state();

  const quick = $derived(($holdings ?? []).map((c) => ({ symbol: c.ticker, name: c.company_name, type: 'Holding' })));
  const list = $derived(q.trim() ? results : quick);

  let seq = 0;
  let timer = null;
  $effect(() => {
    const query = q.trim();
    if (timer) clearTimeout(timer);
    if (!query) { results = []; loading = false; return; }
    loading = true;
    const mine = ++seq;
    timer = setTimeout(async () => {
      try {
        const r = await api.search(query);
        if (mine !== seq) return;
        results = r.results ?? [];
        noteSearchKinds(results);
        active = 0;
      } catch {
        if (mine === seq) results = [];
      } finally {
        if (mine === seq) loading = false;
      }
    }, 180);
  });

  // focus the input each time search mode opens; reset stale queries
  $effect(() => {
    if (mode === 'search') {
      q = '';
      queueMicrotask(() => input?.focus());
    }
  });

  function pick(r) { if (r) openSearchResult(r); }
  function onKey(e) {
    if (e.key === 'Escape') { closeSearch(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, list.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
    else if (e.key === 'Enter') { e.preventDefault(); pick(list[active]); }
  }
</script>

<!-- stock mode renders the widget grid bare on the page paper; search keeps a card shell -->
<section class="stage" bind:this={stageEl}>
  <!-- persistent search strip: idle button (opens search) or the live query input -->
  {#if mode === 'search'}
    <div class="strip strip-active">
      <span class="strip-icon" aria-hidden="true"></span>
      <input
        bind:this={input}
        bind:value={q}
        onkeydown={onKey}
        type="text"
        placeholder="Search"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
      {#if loading}<span class="strip-spin" aria-hidden="true"></span>{/if}
      <button class="strip-esc" onclick={() => closeSearch()}>esc</button>
    </div>
  {:else}
    <button class="strip strip-idle" onclick={() => openSearch()}>
      <span class="strip-icon" aria-hidden="true"></span>
      <span class="strip-ph">Search</span>
      <kbd class="strip-kbd">⌘K</kbd>
    </button>
  {/if}

  <!-- views swap in place — no enter animation; loading is the skeleton's job -->
  {#if mode === 'stock'}
    {#key $detail.ticker}
      <div class="stage-pane stage-widgets">
        <StockPanel ticker={$detail.ticker} name={$detail.name} holding={$detail.holding} onClose={() => closeStock()} glyph="←" />
      </div>
    {/key}
  {:else if mode === 'search'}
    <div class="stage-pane stage-search stage-card">
      {#if q.trim() && !loading && results.length === 0}
        <div class="ss-empty">No matches for “{q.trim()}”.</div>
      {:else if list.length}
        {#if !q.trim()}<div class="ss-section">Your holdings</div>{/if}
        <ul class="ss-list" role="listbox">
          {#each list as r, i (r.symbol)}
            <li>
              <button class="ss-item" class:active={i === active} role="option" aria-selected={i === active}
                      use:prefetch={r.symbol}
                      onmouseenter={() => (active = i)} onclick={() => pick(r)}>
                <span class="ss-sym"><TickerBadge sym={r.symbol} size="md" /></span>
                <span class="ss-name">{r.name}</span>
                <span class="ss-meta"><span>{r.type}</span>{#if r.exchange}<span>{r.exchange}</span>{/if}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else if !q.trim()}
        <div class="ss-empty">Search the whole market, not just your holdings.</div>
      {/if}
    </div>
  {/if}
  <!-- the portfolio stays mounted under the stock view and search, so coming
       back is instant and keeps its range, metric and compares. Same stack as
       the stock view: title card (--title-h) over the chart card. -->
  <div class="stage-pane stage-home" class:stage-off={mode !== 'portfolio'}>
    <DriversCard {drivers} {win} />
    <section class="chart-widget"><PortfolioChart {equity} {spy} {twr} {netInvested} onwindow={(w) => (win = w)} /></section>
  </div>
</section>

<style>
  .stage { min-height: 0; height: 100%; display: flex; flex-direction: column; gap: 16px; }

  /* .strip and .ss-* (search strip + result rows) are shared with the phone — see app.css */

  /* search brings a card shell; stock mode is a bare widget grid; home is two cards */
  .stage-card { background: var(--surface); border: var(--bw) solid var(--ink);
    border-radius: var(--r); box-shadow: var(--sh); overflow: hidden; }
  .stage-pane { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
  .stage-off { display: none; }
  /* let the widget grid set its own height — the page scrolls, not the stage */
  .stage-widgets { display: block; min-height: 0; }
  /* home: Drivers title card + chart card, the stock view's rhythm (16 gap).
     Both boxes are fixed-size, so a tall rail can't stretch the chart. */
  .stage-home { gap: 16px; }

  .stage-search { overflow: hidden; }
</style>

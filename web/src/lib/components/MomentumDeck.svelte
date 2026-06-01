<script>
  // Momentum deck + peek. Takes the dashboard `cards` payload, polls /api/momentum
  // for live intraday moves, and renders the fan (sorted by biggest move) beside a
  // sticky peek. Click a card to inspect it; click again (or nothing selected) →
  // peek defaults to the biggest mover.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  // `chart` is an optional snippet rendered in the empty cols 4–6 of the deck row
  // (the space the 1×2 peek freed) — the dashboard passes the portfolio chart there.
  let { cards = [], chart } = $props();

  let moveWin = $state('day');   // 'day' | 'wk'
  let selected = $state(null);   // ticker; null = biggest mover
  let moves = $state({});        // live /api/momentum overlay

  const SUIT_SYMBOL = { sp: '♠', ht: '♥', dm: '♦', cl: '♣', jk: '★' };
  const RANKS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'];

  const holdings = $derived(
    (cards ?? []).filter((c) => c && !c.is_joker).map((c) => ({
      t: c.ticker, name: c.company_name, suit: c.suit,
      pct: c.position_pct, day: c.day_pct, wk: c.week_pct, ret: c.voo_delta_pp ?? 0,
      value: c.market_value, last: c.current_price, shares: c.shares, basis: c.cost_basis,
    }))
  );

  // live move (fresh /api/momentum) with frozen-payload fallback for first paint
  const moveOf = (h, win) => {
    const live = moves[h.t];
    const v = live ? (win === 'day' ? live.day_pct : live.week_pct) : (win === 'day' ? h.day : h.wk);
    return v ?? 0;
  };

  // rank by weight: heaviest = A
  const rankOf = $derived.by(() => {
    const m = {};
    [...holdings].sort((a, b) => (b?.pct ?? 0) - (a?.pct ?? 0)).forEach((h, i) => { m[h.t] = RANKS[i] ?? '2'; });
    return m;
  });

  // ascending |move| → biggest mover renders last (face-up at the right)
  const movers = $derived([...holdings].sort((a, b) => Math.abs(moveOf(a, moveWin)) - Math.abs(moveOf(b, moveWin))));
  const maxMove = $derived(Math.max(1, ...holdings.map((h) => Math.abs(moveOf(h, moveWin)))));

  // felt shows the top 13 movers (last 13 of the ascending sort); the ribbon
  // below covers every holding, so capping the fan loses nothing.
  const visibleMovers = $derived(movers.slice(-13));
  // ribbon: every holding, heaviest → lightest, so width reads as concentration.
  const byWeight = $derived([...holdings].sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0)));

  const CARD_W = 132;       // .mcard width; keep in sync with CSS
  let fanW = $state(0);     // measured inner width of the fan track (the 2×1 felt)
  // overlap so every visible card fits the felt: each advances by `step`, last
  // card fully shown. `step` is also the visible sliver width each card exposes.
  const fanStep = $derived.by(() => {
    const n = visibleMovers.length;
    if (n <= 1 || !fanW) return CARD_W;
    return Math.max(16, Math.min(CARD_W, (fanW - CARD_W) / (n - 1)));
  });

  const peekH = $derived((selected && holdings.find((h) => h.t === selected)) || movers[movers.length - 1] || null);
  const peek = $derived.by(() => {
    const h = peekH;
    if (!h) return null;
    return {
      ...h,
      avg: h.shares ? h.basis / h.shares : null,
      retPct: h.basis ? (h.value / h.basis - 1) * 100 : null,
      gain: h.basis ? h.value - h.basis : null,
      dayMove: moveOf(h, 'day'),
      weekMove: moveOf(h, 'wk'),
    };
  });

  const f = (n) => (n ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pctS = (n) => ((n ?? 0) > 0 ? '+' : '') + (n ?? 0).toFixed(1) + '%';   // 0 → "0.0%"
  const usd = (n) => ((n ?? 0) >= 0 ? '+$' : '−$') + f(Math.abs(n ?? 0));

  async function loadMomentum() {
    try { const m = await api.momentum(); moves = m.moves ?? {}; } catch { /* keep last */ }
  }
  onMount(() => {
    loadMomentum();
    const t = setInterval(loadMomentum, 60_000);
    return () => clearInterval(t);
  });
</script>

<div class="deck-peek">
  <div class="deck-head">
    <div class="winbar">
      <button class:on={moveWin === 'day'} onclick={() => (moveWin = 'day')}>1d</button>
      <button class:on={moveWin === 'wk'} onclick={() => (moveWin = 'wk')}>1wk</button>
    </div>
  </div>

  <div class="felt">
    <div class="mfan" bind:clientWidth={fanW}>
      {#each visibleMovers as h, i (h.t)}
        {@const mv = moveOf(h, moveWin)}
        <button class="mcard suit-{h.suit}" class:selected={selected === h.t}
                style="margin-left:{i === 0 ? 0 : fanStep - CARD_W}px; --sliver:{fanStep}px"
                onclick={() => (selected = selected === h.t ? null : h.t)}>
          <div class="mstrip {mv >= 0 ? 'up' : 'down'}">
            <span class="mstrip-fill" style="height:{Math.max(3, Math.abs(mv) / maxMove * 50).toFixed(1)}%"></span>
          </div>
          <div class="mindex tl">
            <span class="mi-rank">{rankOf[h.t]}</span>
            <span class="mi-suit">{SUIT_SYMBOL[h.suit]}</span>
            <span class="mi-tkr">{h.t}</span>
          </div>
          <div class="mindex br">
            <span class="mi-rank">{rankOf[h.t]}</span>
            <span class="mi-suit">{SUIT_SYMBOL[h.suit]}</span>
            <span class="mi-tkr">{h.t}</span>
          </div>
        </button>
      {/each}
    </div>
  </div>

  {#if peek}
    <aside class="peek">
      <a class="glass-card peek-card" href="/investments/{peek.t}" aria-label="Full analysis: {peek.t}">
        <div class="peek-top">
          <div class="peek-badge suit-{peek.suit}">{rankOf[peek.t]}<span class="badge-suit">{SUIT_SYMBOL[peek.suit]}</span></div>
          <div class="peek-id">
            <div class="peek-tkr">{peek.t}</div>
            <div class="peek-name">{peek.name}</div>
          </div>
          <span class="peek-go" aria-hidden="true">→</span>
        </div>

        <div class="peek-sub">your return</div>
        {#if peek.retPct != null}
          <div class="peek-hero {peek.retPct >= 0 ? 'up' : 'down'}">
            <span class="peek-ret">{pctS(peek.retPct)}</span>
            <span class="peek-ret-abs">{usd(peek.gain)}</span>
          </div>
        {:else}
          <div class="peek-hero"><span class="peek-ret">—</span></div>
        {/if}

        <div class="peek-rows">
          <div class="pr"><span>value</span><b>${f(peek.value)}</b></div>
          <div class="pr"><span>weight</span><b>{peek.pct}%</b></div>
          <div class="pr"><span>today</span><b class={peek.dayMove >= 0 ? 'up' : 'down'}>{pctS(peek.dayMove)}</b></div>
          <div class="pr"><span>this week</span><b class={peek.weekMove >= 0 ? 'up' : 'down'}>{pctS(peek.weekMove)}</b></div>
          <div class="pr"><span>avg cost</span><b>{peek.avg != null ? `$${f(peek.avg)}` : '—'}</b></div>
          <div class="pr"><span>last</span><b>${f(peek.last)}</b></div>
        </div>

      </a>
    </aside>
  {/if}

  {#if chart}
    <div class="deck-chart">{@render chart()}</div>
  {/if}
</div>

<!-- allocation ribbon: the finder. width = weight, floored at ticker width. -->
<div class="alloc-ribbon" role="group" aria-label="all holdings — click to inspect">
  {#each byWeight as h (h.t)}
    <button class="ribbon-seg" class:selected={selected === h.t} style="flex-grow:{h.pct}"
            title="{h.name} · {h.pct}% of portfolio · ${f(h.value)}"
            onclick={() => (selected = selected === h.t ? null : h.t)}>
      <span class="seg-tkr">{h.t}</span>
    </button>
  {/each}
</div>

<style>
  /* same 6-col system as the KPI strip above; head over felt+peek, cols 5–6 breathe */
  /* minmax(0,1fr): tracks stay equal even when a peek's name/number is long, so
     the peek is ALWAYS exactly one column wide (never resizes per ticker) */
  .deck-peek { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 16px; align-items: start; }
  .deck-head { grid-column: 1 / 5; display: flex; margin-bottom: 6px; }
  /* 1d / 1wk — black radio, matching the design-page segmented switcher; top-left of the deck */
  .winbar { display: inline-flex; border: var(--bw) solid var(--ink); border-radius: var(--r);
    overflow: hidden; box-shadow: var(--sh); }
  .winbar button { font-family: var(--mono); font-size: 13px; font-weight: 700; cursor: pointer; padding: 8px 14px;
    background: var(--surface); color: var(--ink); border: 0; border-right: var(--bw) solid var(--ink); }
  .winbar button:last-child { border-right: 0; }
  .winbar button.on { background: var(--ink); color: var(--surface); }

  /* suit palette — pink ♥, yellow ♦, purple ♠, blue ♣ (glyphs get an ink outline) */
  .suit-sp { --suit: #8a63d2; }  /* spade   = purple */
  .suit-ht { --suit: #e8689b; }  /* heart   = pink   */
  .suit-dm { --suit: #ecb22e; }  /* diamond = yellow */
  .suit-cl { --suit: #4f86d6; }  /* club    = blue   */
  .suit-jk { --suit: #6f7a63; }

  /* padding-top matches the peek's inset so the cards' top lines up with the peek's top */
  .felt { --deck: #6f7a63; grid-column: 1 / 3; grid-row: 2; position: relative; z-index: 1; border-radius: var(--r); padding: 16px 22px 0; }
  .felt::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 56px;
    background: var(--deck); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: 0 4px 0 0 var(--ink); z-index: 0; }

  .mfan { position: relative; z-index: 1; display: flex; align-items: flex-end; height: 196px; padding-bottom: 10px; }
  .mcard { position: relative; flex: 0 0 auto; width: 132px; height: 168px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: 10px; box-shadow: var(--sh);
    cursor: pointer; overflow: hidden; padding: 0; font: inherit; color: inherit; text-align: left;
    transition: transform .16s ease, box-shadow .16s ease; }
  .mcard:hover { z-index: 999; transform: translateY(-20px); box-shadow: var(--sh-pop); }
  /* clicked card lifts + ink ring; no sibling spread (the peek carries the detail,
     and spreading pushed cards out over the peek) */
  .mcard.selected { z-index: 998; transform: translateY(-20px); box-shadow: var(--sh-pop); outline: 3px solid var(--brand); outline-offset: -3px; }

  .mstrip { position: absolute; top: 0; left: 0; bottom: 0; width: 34px; background: var(--paper);
    border-right: 2px solid var(--ink); overflow: hidden; }
  .mstrip-fill { position: absolute; left: 0; right: 0; bottom: 0; }
  .mstrip.up .mstrip-fill { background: var(--gain); }
  .mstrip.down .mstrip-fill { background: var(--loss); }

  .mindex { position: absolute; display: flex; flex-direction: column; align-items: center; line-height: .9; }
  /* tl is centred on the visible sliver's midpoint → equal margins left/right */
  .mindex.tl { top: 8px; left: calc(var(--sliver, 34px) / 2); transform: translateX(-50%); }
  .mindex.br { bottom: 8px; right: 8px; transform: rotate(180deg); }
  .mi-rank { font-family: var(--sans); font-weight: 700; font-size: 19px; color: var(--ink); line-height: .82; }
  .mi-suit { font-size: 19px; color: var(--suit); line-height: 1; margin-top: 1px;
    -webkit-text-stroke: 1px var(--ink); paint-order: stroke fill; }
  /* ticker rotated 90° (vertical) so it runs DOWN its own sliver, never bleeding
     into neighbours — also keeps the index column narrow so it centres cleanly */
  .mi-tkr { font-family: var(--mono); font-weight: 700; font-size: 11px; color: var(--ink); margin-top: 4px;
    writing-mode: vertical-rl; letter-spacing: -.02em; }

  /* ── peek (1×2 inspector — investor-first: leads with your return) ── */
  /* z-index above the felt's stacking layer → a lifted card can never cover it */
  .peek { grid-column: 3 / 4; grid-row: 2; min-height: clamp(300px, 26vw, 352px); position: relative; z-index: 2; }

  /* portfolio chart — fills the cols the 1×2 peek freed, same row & height as the peek */
  .deck-chart { grid-column: 4 / 7; grid-row: 2; min-height: clamp(300px, 26vw, 352px); }
  /* the whole card is the link to full analysis — a corner arrow is the only cue,
     no bulky button. hover gives the standard brutalist lift. */
  .peek-card { height: 100%; padding: 16px; display: flex; flex-direction: column; color: inherit; text-decoration: none;
    transition: transform .12s ease, box-shadow .12s ease; }
  .peek-card:hover { transform: translate(-2px, -2px); box-shadow: var(--sh-pop); }
  .peek-top { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
  .peek-badge { width: 40px; height: 40px; flex: 0 0 auto; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; background: var(--suit, var(--brand)); border: var(--bw) solid var(--ink); border-radius: 8px; }
  .badge-suit { font-size: 10px; -webkit-text-stroke: .75px var(--ink); paint-order: stroke fill; }
  .peek-id { min-width: 0; flex: 1; }
  .peek-tkr { font-size: 18px; font-weight: 700; }
  .peek-name { font-family: var(--mono); font-size: 11px; color: var(--muted);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .peek-go { flex: 0 0 auto; font-family: var(--sans); font-size: 20px; font-weight: 700; color: var(--muted);
    transition: color .12s ease, transform .12s ease; }
  .peek-card:hover .peek-go { color: var(--ink); transform: translateX(3px); }
  .peek-sub { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; color: var(--ink);
    opacity: .55; margin-bottom: 3px; }
  /* stacked (% over $) so the hero is always two lines → peek height never shifts */
  .peek-hero { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; margin-bottom: 16px; }
  .peek-ret { font-family: var(--mono); font-size: 28px; font-weight: 700; line-height: 1; }
  .peek-ret-abs { font-family: var(--mono); font-size: 14px; font-weight: 700; opacity: .8; }
  .peek-rows { display: flex; flex-direction: column; gap: 7px; }
  .pr { display: flex; align-items: baseline; justify-content: space-between; font-size: 12px; }
  .pr span { color: var(--muted); }
  .pr b { font-family: var(--mono); font-weight: 700; font-size: 13px; }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  /* ── allocation ribbon — every holding, width = weight, floored at ticker width ── */
  .alloc-ribbon { display: flex; align-items: stretch; height: 42px; width: 100%; overflow: hidden;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .ribbon-seg { flex: 0 1 0; min-width: max-content; display: flex; align-items: center; justify-content: center;
    padding: 0 11px; border: 0; border-right: 2px solid var(--ink); background: var(--surface); color: var(--ink);
    cursor: pointer; font: inherit; transition: background .12s ease; }
  .ribbon-seg:last-child { border-right: 0; }
  .ribbon-seg:hover { background: var(--paper); }
  .ribbon-seg.selected { background: var(--brand); }
  .seg-tkr { font-family: var(--mono); font-weight: 700; font-size: 12px; letter-spacing: -.02em; white-space: nowrap; }

  @media (max-width: 1100px) {
    .deck-peek { grid-template-columns: 1fr; }
    .deck-head, .felt, .peek, .deck-chart { grid-column: 1; grid-row: auto; }
    .peek { min-height: 0; }
    .deck-chart { min-height: 320px; }
  }
</style>

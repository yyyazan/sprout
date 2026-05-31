<script>
  // Momentum deck + peek. Takes the dashboard `cards` payload, polls /api/momentum
  // for live intraday moves, and renders the fan (sorted by biggest move) beside a
  // sticky peek. Click a card to inspect it; click again (or nothing selected) →
  // peek defaults to the biggest mover.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let { cards = [] } = $props();

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

  const peekH = $derived((selected && holdings.find((h) => h.t === selected)) || movers[movers.length - 1] || null);
  const peek = $derived.by(() => {
    const h = peekH;
    if (!h) return null;
    return {
      ...h,
      avg: h.shares ? h.basis / h.shares : null,
      retPct: h.basis ? (h.value / h.basis - 1) * 100 : null,
      dayMove: moveOf(h, 'day'),
      weekMove: moveOf(h, 'wk'),
      isBiggest: !selected,
    };
  });

  const f = (n) => (n ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sgn = (n) => ((n ?? 0) >= 0 ? '+' : '');

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
  <div class="deck-col">
    <div class="deck-head">
      <span class="deck-title">today’s movers</span>
      <span class="deck-sub">sorted by biggest move · click to inspect</span>
      <div class="winbar">
        <button class:on={moveWin === 'day'} onclick={() => (moveWin = 'day')}>today</button>
        <button class:on={moveWin === 'wk'} onclick={() => (moveWin = 'wk')}>this week</button>
      </div>
    </div>

    <div class="felt">
      <div class="mfan">
        {#each movers as h (h.t)}
          {@const mv = moveOf(h, moveWin)}
          <button class="mcard suit-{h.suit}" class:selected={selected === h.t}
                  onclick={() => (selected = selected === h.t ? null : h.t)}>
            <div class="mstrip {mv >= 0 ? 'up' : 'down'}">
              <span class="mstrip-fill" style="height:{Math.max(3, Math.abs(mv) / maxMove * 50).toFixed(1)}%"></span>
            </div>
            <div class="mindex tl">
              <span class="mi-rank">{rankOf[h.t]}</span>
              <span class="mi-suit">{SUIT_SYMBOL[h.suit]}</span>
              <span class="mi-tkr">{h.t}</span>
            </div>
            <div class="mface">
              <div class="mc-logo">{h.t.slice(0, 2)}</div>
              <div class="mc-name">{h.name}</div>
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
  </div>

  {#if peek}
    <aside class="peek">
      <div class="glass-card peek-card">
        <div class="peek-top">
          <div class="peek-badge suit-{peek.suit}">{rankOf[peek.t]}<span class="badge-suit">{SUIT_SYMBOL[peek.suit]}</span></div>
          <div>
            <div class="peek-tkr">{peek.t}</div>
            <div class="peek-name">{peek.name}{peek.isBiggest ? ' · biggest mover' : ''}</div>
          </div>
        </div>
        <div class="peek-big">${f(peek.value)}</div>
        <div class="peek-biglabel">{peek.pct}% of portfolio · {peek.shares} sh</div>

        <div class="peek-quad">
          <div class="qd"><span>today</span><b class={peek.dayMove >= 0 ? 'up' : 'down'}>{sgn(peek.dayMove)}{peek.dayMove}%</b></div>
          <div class="qd"><span>this week</span><b class={peek.weekMove >= 0 ? 'up' : 'down'}>{sgn(peek.weekMove)}{peek.weekMove}%</b></div>
          <div class="qd"><span>avg cost</span><b>{peek.avg != null ? `$${f(peek.avg)}` : '—'}</b></div>
          <div class="qd"><span>last</span><b>${f(peek.last)}</b></div>
        </div>

        {#if peek.retPct != null}
          <div class="peek-sub">your return</div>
          <div class="peek-ret {peek.retPct >= 0 ? 'up' : 'down'}">{sgn(peek.retPct)}{peek.retPct.toFixed(1)}%</div>
        {/if}

        <a class="peek-cta" href="/investments/{peek.t}">Full analysis →</a>
      </div>
    </aside>
  {/if}
</div>

<style>
  .deck-peek { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
  .deck-col { display: flex; flex-direction: column; min-width: 0; }

  .deck-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
  .deck-title { font-size: 16px; font-weight: 700; }
  .deck-sub { font-size: 12px; color: var(--muted); }
  .winbar { margin-left: auto; display: flex; gap: 5px; }
  .winbar button { font-family: var(--sans); font-size: 11px; font-weight: 600; cursor: pointer; padding: 3px 9px;
    border: 2px solid var(--ink); border-radius: 5px; background: var(--surface); color: var(--ink); }
  .winbar button.on { background: var(--ink); color: var(--surface); }

  /* neutral suit palette (no green/red/yellow — those are momentum) */
  .suit-sp { --suit: #566373; }
  .suit-ht { --suit: #b1897e; }
  .suit-dm { --suit: #8a7a92; }
  .suit-cl { --suit: #8f8a7c; }
  .suit-jk { --suit: #6f7a63; }

  .felt { --deck: #6f7a63; position: relative; border-radius: var(--r); padding: 22px 0 0 10px; }
  .felt::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 56px;
    background: var(--deck); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: 0 4px 0 0 var(--ink); z-index: 0; }

  .mfan { position: relative; z-index: 1; display: flex; align-items: flex-end; height: 196px; padding-bottom: 10px; }
  .mcard { position: relative; flex: 0 0 auto; width: 132px; height: 168px; margin-left: -98px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: 10px; box-shadow: var(--sh);
    cursor: pointer; overflow: hidden; padding: 0; font: inherit; color: inherit; text-align: left;
    transition: transform .16s ease, box-shadow .16s ease; }
  .mcard:first-child { margin-left: 0; }
  .mcard:hover { z-index: 999; transform: translateY(-20px); box-shadow: var(--sh-pop); }
  /* clicked card stays elevated + ink ring; following cards spread so its face is clear */
  .mcard.selected { z-index: 998; transform: translateY(-20px); box-shadow: var(--sh-pop); outline: 3px solid var(--brand); outline-offset: -3px; }
  .mcard:hover ~ .mcard, .mcard.selected ~ .mcard { transform: translateX(100px); }

  .mstrip { position: absolute; top: 0; left: 0; bottom: 0; width: 34px; background: var(--paper);
    border-right: 2px solid var(--ink); overflow: hidden; }
  .mstrip-fill { position: absolute; left: 0; right: 0; bottom: 0; }
  .mstrip.up .mstrip-fill { background: var(--gain); }
  .mstrip.down .mstrip-fill { background: var(--loss); }

  .mindex { position: absolute; display: flex; flex-direction: column; align-items: center; line-height: .9; }
  .mindex.tl { top: 9px; left: 11px; }
  .mindex.br { bottom: 9px; right: 11px; transform: rotate(180deg); }
  .mi-rank { font-family: var(--sans); font-weight: 700; font-size: 19px; color: var(--ink); line-height: .82; }
  .mi-suit { font-size: 13px; color: var(--suit); line-height: 1; margin-top: 2px; }
  .mi-tkr { font-family: var(--mono); font-weight: 700; font-size: 8px; color: var(--ink); margin-top: 3px; letter-spacing: -.02em; }

  .mface { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 7px; padding: 6px 10px; }
  .mc-logo { width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; font-weight: 700;
    font-size: 15px; background: var(--suit, var(--brand)); border: var(--bw) solid var(--ink); border-radius: 9px; color: var(--ink); }
  .mc-name { font-family: var(--sans); font-weight: 300; font-size: 13px; color: var(--ink); text-align: center;
    letter-spacing: -0.01em; max-height: 34px; overflow: hidden; }

  /* ── peek ── */
  .peek { position: sticky; top: 18px; }
  .peek-card { padding: 18px 18px 16px; display: flex; flex-direction: column; }
  .peek-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .peek-badge { width: 44px; height: 44px; flex: 0 0 auto; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 17px; background: var(--suit, var(--brand)); border: var(--bw) solid var(--ink); border-radius: 8px; }
  .badge-suit { font-size: 11px; }
  .peek-tkr { font-size: 19px; font-weight: 700; }
  .peek-name { font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .peek-big { font-family: var(--mono); font-size: 30px; font-weight: 700; line-height: 1.05; }
  .peek-biglabel { font-size: 12px; color: var(--muted); margin-top: 2px; margin-bottom: 14px; }
  .peek-quad { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
  .qd { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
  .qd span { color: var(--muted); }
  .qd b { font-family: var(--mono); font-size: 15px; }
  .peek-sub { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; color: var(--ink);
    opacity: .6; margin: 16px 0 6px; }
  .peek-ret { font-family: var(--mono); font-size: 18px; font-weight: 700; }
  .peek-cta { display: block; text-align: center; margin-top: 16px; padding: 11px; font-weight: 700;
    background: var(--ink); color: var(--surface); border-radius: var(--r); border: var(--bw) solid var(--ink);
    box-shadow: var(--sh); transition: transform .12s ease, box-shadow .12s ease; }
  .peek-cta:hover { transform: translate(-2px, -2px); box-shadow: var(--sh-pop); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  @media (max-width: 1100px) {
    .deck-peek { grid-template-columns: 1fr; }
    .peek { position: static; }
  }
</style>

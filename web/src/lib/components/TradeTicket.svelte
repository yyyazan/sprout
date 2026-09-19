<script>
  // Trade tile (1×1, sits under the cash tile in the rail). Mirrors CashGoalCard:
  // a glance summary up top — trades this month, the buy/sell split, the last fill —
  // and clicking the tile floats a yellow panel up from the bottom (to 60% of the
  // card) holding a working trade logger. Unlike the old mock, this one posts:
  // it hits the same /trades endpoint the log page uses.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { holdings, trades as tradesStore, loadTrades } from '$lib/stores.js';

  const today = () => new Date().toISOString().slice(0, 10);
  const TICKER_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // "2026-06-10" → "Jun 10" without touching Date() (no tz drift)
  const shortDate = (s) => {
    const [, m, d] = (s || '').split('-');
    return m ? `${MON[+m - 1]} ${+d}` : '';
  };

  let { onSaved } = $props();

  // Glance data — from the shared trades store (the mobile log pane reads the
  // same store, so the dashboard only fetches /api/trades once).
  const trades = $derived($tradesStore ?? []);
  onMount(() => loadTrades());

  const monthKey = $derived(today().slice(0, 7)); // "YYYY-MM"
  const monthTrades = $derived(trades.filter((t) => (t.date || '').startsWith(monthKey)));
  const buys = $derived(monthTrades.filter((t) => (t.action || '').toLowerCase() === 'buy').length);
  const sells = $derived(monthTrades.length - buys);
  // trades come newest-first from the API
  const last = $derived(trades[0] ?? null);
  const lastIsBuy = $derived((last?.action || '').toLowerCase() === 'buy');
  const sharesFmt = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 });

  // Click the tile to toggle the rising logger panel.
  let open = $state(false);
  const toggle = () => (open = !open);

  // Trade entry — mirrors the log page's trade form: side · ticker · shares · date.
  let side = $state('buy');
  let ticker = $state('');
  let shares = $state('');
  let price = $state(''); // per-share execution price; blank → server uses the close
  let date = $state(today());
  let saving = $state(false);
  let saveError = $state(null);
  let tickerEl;

  const flipSide = () => (side = side === 'buy' ? 'sell' : 'buy');
  // once the user edits the ticker, stop the auto-prefill — otherwise deleting
  // the last character re-fills it with the top holding (the "can't clear" bug)
  let tickerTouched = $state(false);

  async function save() {
    if (saving) return;
    const tk = (ticker || '').trim().toUpperCase();
    if (!TICKER_RE.test(tk)) { saveError = 'Enter a valid ticker'; return; }
    if (!(Number(shares) > 0)) { saveError = 'Enter shares > 0'; return; }
    if (price !== '' && !(Number(price) > 0)) { saveError = 'Enter price > 0'; return; }
    saving = true;
    saveError = null;
    try {
      const res = await api.addTrade({
        ticker: tk,
        action: side,
        shares: Number(shares),
        price: price === '' ? null : Number(price),
        trade_date: date
      });
      if (res?.ok) {
        ticker = ''; shares = ''; price = '';
        await loadTrades(true);
        onSaved?.();
      } else {
        // surface the first field error from the validator
        saveError = res?.errors ? Object.values(res.errors)[0] : 'Save failed';
      }
    } catch {
      saveError = 'Save failed';
    } finally {
      saving = false;
    }
  }

  // Prefill ticker with the largest holding (once, before the user types).
  $effect(() => {
    if (!tickerTouched && !ticker && $holdings?.length) {
      ticker = [...$holdings].sort((a, b) => (b.position_pct ?? 0) - (a.position_pct ?? 0))[0].ticker;
    }
  });
  $effect(() => { if (open && tickerEl) tickerEl.focus(); });
</script>

<div class="glass-card pressable trade-card" class:open role="button" tabindex="0" aria-expanded={open}
  onclick={toggle}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}>
  <!-- corner token: ink-outlined tile with an up-arrow over a muted down-arrow —
       reads as "trades", and lifts on hover like the cash coin (logger affordance).
       Neutral blue (not red/green) so it never reads as a buy/sell signal. -->
  <svg class="tt-badge" viewBox="0 0 120 120" width="32" height="32" aria-hidden="true">
    <rect x="6" y="6" width="108" height="108" rx="26" fill="#5b8def" stroke="#1a1a1a" stroke-width="6" />
    <!-- up arrow (buy) -->
    <path d="M44 78 V52 M44 52 L33 63 M44 52 L55 63" fill="none" stroke="#1a1a1a"
      stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
    <!-- down arrow (sell) -->
    <path d="M78 42 V68 M78 68 L67 57 M78 68 L89 57" fill="none" stroke="#1a1a1a"
      stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity="0.45" />
  </svg>

  <!-- persistent "this opens" badge, half-overlapping the badge's corner — same
       mark as the cash tile's, so the two logger cards read as one pattern. -->
  <span class="tt-add" aria-hidden="true"></span>

  <div class="tt-head">
    <div class="kpi-label">Trades</div>
    <div class="kpi-value">{monthTrades.length}</div>
    <div class="kpi-subtitle">this month</div>
  </div>

  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Buys</span><span class="bal-v">{buys}</span></div>
    <div class="bal-row"><span class="bal-k">Sells</span><span class="bal-v">{sells}</span></div>
    {#if last}
      <div class="bal-row">
        <span class="bal-k">Last</span>
        <span class="bal-v"><span class={lastIsBuy ? 'up' : 'down'}>{lastIsBuy ? '+' : '−'}{sharesFmt(last.shares)}</span> {last.ticker} <span class="dim">{shortDate(last.date)}</span></span>
      </div>
    {/if}
  </div>

  <!-- Rising logger panel: grows from 0 to its own content height on click (a CSS-grid
       0fr→1fr track — see the CashGoalCard rise for why a fixed/percentage height
       doesn't work here). The side toggle sits left; ticker/shares/date/price fill a
       2×2 field grid to its right; save is a circle on the far right. Clicks/keys
       inside are stopped so interacting doesn't toggle the tile; inert when closed. -->
  <div class="tt-rise" inert={!open}
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}>
   <div class="tt-clip">
    <div class="tt-rise-inner">
    <div class="tt-body">
      <button type="button" class="tt-side" class:pos={side === 'buy'} class:neg={side === 'sell'} onclick={flipSide}
        aria-label={side === 'buy' ? 'Buy — tap to switch to sell' : 'Sell — tap to switch to buy'}>{side === 'buy' ? 'Buy' : 'Sell'}</button>
      <div class="tt-grid">
        <div class="tt-cell tt-ticker-wrap" class:invalid={saveError}>
          <input class="tt-in tt-ticker" bind:value={ticker} bind:this={tickerEl} placeholder="AAPL"
            list="tt-tickers" autocomplete="off" autocorrect="off" spellcheck="false"
            style="text-transform:uppercase"
            oninput={() => { tickerTouched = true; saveError = null; }}
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
            aria-label="Ticker" />
        </div>
        <input class="tt-in tt-cell tt-shares" class:invalid={saveError} type="number" step="any" min="0" inputmode="decimal" placeholder="shares"
          bind:value={shares}
          oninput={() => { saveError = null; }}
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
          aria-label="Shares" />
        <input class="tt-cell tt-date-input" type="date" bind:value={date} max={today()} aria-label="Trade date" />
        <input class="tt-in tt-cell tt-price" type="number" step="any" min="0" inputmode="decimal"
          placeholder="price" bind:value={price}
          oninput={() => { saveError = null; }}
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
          aria-label="Execution price per share (blank uses closing price)" />
      </div>
      <button type="button" class="tt-save" onclick={save} disabled={saving}
        aria-label="Save trade">✓</button>
    </div>
    <datalist id="tt-tickers">
      {#each $holdings ?? [] as h (h.ticker)}<option value={h.ticker}>{h.company_name}</option>{/each}
    </datalist>
    {#if saveError}<div class="tt-save-err" role="alert">{saveError}</div>{/if}
    </div>
   </div>
  </div>
</div>

<style>
  .trade-card { position: relative; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; overflow: hidden; }
  /* keep the headline clear of the badge in the corner */
  .tt-head { padding-right: 38px; }

  .tt-badge { position: absolute; top: 12px; right: 12px; z-index: 1; overflow: visible;
    transition: transform .2s cubic-bezier(.34, 1.56, .5, 1); }
  .trade-card:hover .tt-badge { transform: translateY(-2px); }

  /* quiet "+" affordance badge, half-overlapping the token's bottom-right edge.
     The plus is drawn as two CSS bars (not text) so it sits dead-center
     regardless of font metrics; the whole badge spins 45° into an × on open. */
  .tt-add { position: absolute; top: 39px; right: 7px; z-index: 2; pointer-events: none;
    width: 17px; height: 17px; border-radius: 50%;
    background: var(--surface); border: 1.5px solid var(--hairline); color: var(--muted);
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease; }
  .tt-add::before, .tt-add::after { content: ''; position: absolute; top: 50%; left: 50%;
    background: currentColor; transform: translate(-50%, -50%); }
  .tt-add::before { width: 8px; height: 1.5px; }
  .tt-add::after { width: 1.5px; height: 8px; }
  .trade-card:hover .tt-add { border-color: var(--ink); color: var(--ink); }
  .trade-card.open .tt-add { background: var(--ink); border-color: var(--ink); color: var(--paper); transform: rotate(45deg); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  /* Logger panel: grows from the bottom to its own content height on click. A
     single-row CSS grid (0fr → 1fr) rather than a fixed/percentage height — see
     the CashGoalCard rise for why percentage doesn't resolve here. */
  .tt-rise {
    position: absolute; left: 0; right: 0; bottom: 0;
    display: grid; grid-template-rows: 0fr;
    z-index: 2; cursor: default;
    transition: grid-template-rows .45s cubic-bezier(.22, 1, .36, 1);
  }
  .trade-card.open .tt-rise { grid-template-rows: 1fr; }
  /* the grid ITEM: bare — no padding/border of its own, so it has nothing to
     hold the 0fr track open (grid track auto-sizing floors at an item's padding
     + border regardless of min-height:0, which only zeros its content minimum —
     that residual floor was the sliver that never fully collapsed). */
  .tt-clip { min-height: 0; overflow: hidden; }
  /* the actual visual sheet — same paper/ink chrome as every other widget, no
     loud fill; a top hairline is the only seam. */
  .tt-rise-inner {
    background: var(--surface);
    border-top: var(--bw) solid var(--ink);
    border-radius: calc(var(--r) * 2) calc(var(--r) * 2) 0 0;
    display: flex; flex-direction: column; justify-content: center; gap: 6px;
    padding: 10px 12px;
  }
  /* the card's hover-lift was fighting the panel's own height transition on
     click — it's an active edit surface once open, not a hover-preview target. */
  .trade-card.open, .trade-card.open:hover { transform: none; box-shadow: var(--sh); }

  /* Body: side toggle (left, natural pill size) · a 2×2 field grid (ticker/shares
     over date/price, both rows sharing the same two column widths) · save (right,
     a plain circle) — both sit vertically centred against the taller grid, not
     stretched to match it. */
  .tt-body { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }
  .tt-side { flex: 0 0 auto; padding: 7px 12px; box-sizing: border-box; border: 1.5px solid var(--hairline);
    border-radius: 999px; background: transparent; font-family: var(--sans); font-size: 11.5px;
    font-weight: 600; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .tt-side.pos { border-color: var(--gain); color: var(--gain); }
  .tt-side.neg { border-color: var(--loss); color: var(--loss); }
  .tt-side.pos:active { background: color-mix(in srgb, var(--gain) 16%, transparent); }
  .tt-side.neg:active { background: color-mix(in srgb, var(--loss) 16%, transparent); }
  .tt-save { flex: 0 0 30px; width: 30px; height: 30px; padding: 0; box-sizing: border-box;
    border-radius: 999px; background: transparent; font-size: 13px; cursor: pointer;
    border: 1.5px solid var(--hairline); color: var(--ink);
    display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .tt-save:hover { border-color: var(--ink); }
  .tt-save:active { background: var(--ink); color: var(--paper); }
  .tt-save:disabled { opacity: .4; cursor: default; }

  /* 2×2 grid: ticker/shares (row 1) over date/price (row 2), two equal columns —
     each row was sizing its own cells independently before, so nothing lined up. */
  .tt-grid { flex: 1 1 auto; min-width: 0; display: grid;
    grid-template-columns: 1fr 1fr; grid-template-rows: 28px 28px; gap: 6px; }
  /* .tt-in (borderless text style) comes first so .tt-cell's border isn't the
     later, winning declaration on cells that carry both classes (shares/price) —
     that ordering bug is why they were rendering with no visible border. */
  .tt-in { min-width: 0; padding: 0 8px; border: 0; outline: none; background: transparent;
    font-family: var(--num); font-size: var(--fs-body); font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums;
    -moz-appearance: textfield; appearance: textfield; }
  .tt-ticker { flex: 1 1 auto; min-width: 0; }
  .tt-in::placeholder { color: var(--muted); }
  .tt-in::-webkit-outer-spin-button, .tt-in::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  .tt-cell { box-sizing: border-box; min-width: 0; background: var(--surface);
    border: var(--bw) solid var(--ink); border-radius: var(--r); }
  .tt-cell.invalid { background: color-mix(in srgb, var(--loss) 12%, var(--surface)); border-color: var(--loss); }
  .tt-ticker-wrap { display: flex; align-items: center; padding: 0 2px; }

  .tt-date-input { padding: 0 8px; font-family: var(--num); font-size: var(--fs-meta);
    font-weight: 600; color: var(--ink); cursor: pointer; }
  .tt-date-input::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .85; }

  .tt-save-err { flex: 0 0 auto; color: var(--loss); font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; text-align: center; }

  @media (prefers-reduced-motion: reduce) {
    .tt-badge { transition: none; }
    .trade-card:hover .tt-badge { transform: none; }
    .tt-rise { transition: none; }
    .tt-add { transition: none; }
  }
</style>

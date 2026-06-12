<script>
  // Trade tile (1×1, sits under the cash tile in the rail). Mirrors CashGoalCard:
  // a glance summary up top — trades this month, the buy/sell split, the last fill —
  // and clicking the tile floats a yellow panel up from the bottom (to 60% of the
  // card) holding a working trade logger. Unlike the old mock, this one posts:
  // it hits the same /trades endpoint the log page uses.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { holdings } from '$lib/stores.js';

  const today = () => new Date().toISOString().slice(0, 10);
  const TICKER_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // "2026-06-10" → "Jun 10" without touching Date() (no tz drift)
  const shortDate = (s) => {
    const [, m, d] = (s || '').split('-');
    return m ? `${MON[+m - 1]} ${+d}` : '';
  };

  let { onSaved } = $props();

  // Glance data — fetched locally, refreshed after a save.
  let trades = $state([]);
  async function loadTrades() { trades = await api.trades(); }
  onMount(loadTrades);

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
        await loadTrades();
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

<div class="glass-card trade-card" class:open role="button" tabindex="0" aria-expanded={open}
  onclick={toggle}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}>
  <!-- corner token: ink-outlined tile with a gold up-arrow over a muted down-arrow —
       reads as "trades", and lifts on hover like the cash coin (logger affordance). -->
  <svg class="tt-badge" viewBox="0 0 120 120" width="32" height="32" aria-hidden="true">
    <rect x="6" y="6" width="108" height="108" rx="26" fill="#FF3E00" stroke="#1a1a1a" stroke-width="6" />
    <!-- up arrow (buy) -->
    <path d="M44 78 V52 M44 52 L33 63 M44 52 L55 63" fill="none" stroke="#1a1a1a"
      stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
    <!-- down arrow (sell) -->
    <path d="M78 42 V68 M78 68 L67 57 M78 68 L89 57" fill="none" stroke="#1a1a1a"
      stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity="0.45" />
  </svg>

  <div class="tt-head">
    <div class="kpi-label">Trade</div>
    <div class="kpi-value">{monthTrades.length}</div>
    <div class="kpi-subtitle">{monthTrades.length === 1 ? 'trade' : 'trades'} this month</div>
  </div>

  <div class="tt-foot">
    <div class="tt-foot-head">
      <span class="tt-split">{buys} buys / {sells} sells</span>
      {#if last}
        <span class="tt-last">last {last.ticker} {lastIsBuy ? '+' : '−'}{sharesFmt(last.shares)} · {shortDate(last.date)}</span>
      {/if}
    </div>
  </div>

  <!-- Yellow logger panel: rises from the bottom to 60% of the tile on click. Holds the
       trade-entry bar ([buy/sell] · ticker · shares · ✓) and a date row. Clicks/keys
       inside are stopped so interacting doesn't toggle the tile; inert when closed. -->
  <div class="tt-rise" inert={!open}
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}>
    <div class="tt-entry" class:invalid={saveError}>
      <button type="button" class="tt-seg tt-side" class:sell={side === 'sell'} onclick={flipSide}
        aria-label={side === 'buy' ? 'Buy — tap to switch to sell' : 'Sell — tap to switch to buy'}>{side === 'buy' ? 'Buy' : 'Sell'}</button>
      <input class="tt-in tt-ticker" bind:value={ticker} bind:this={tickerEl} placeholder="AAPL"
        list="tt-tickers" autocomplete="off" autocorrect="off" spellcheck="false"
        style="text-transform:uppercase"
        oninput={() => { tickerTouched = true; saveError = null; }}
        onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
        aria-label="Ticker" />
      <input class="tt-in tt-shares" type="number" step="any" min="0" inputmode="decimal" placeholder="0"
        bind:value={shares}
        oninput={() => { saveError = null; }}
        onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
        aria-label="Shares" />
      <button type="button" class="tt-seg tt-save" onclick={save} disabled={saving}
        aria-label="Save trade">✓</button>
    </div>
    <datalist id="tt-tickers">
      {#each $holdings ?? [] as h (h.ticker)}<option value={h.ticker}>{h.company_name}</option>{/each}
    </datalist>
    <!-- date · execution price; price blank = filled with that day's close on save -->
    <div class="tt-date-row">
      <input class="tt-date-input" type="date" bind:value={date} max={today()} aria-label="Trade date" />
      <input class="tt-price-input" type="number" step="any" min="0" inputmode="decimal"
        placeholder="@ close" bind:value={price}
        oninput={() => { saveError = null; }}
        onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
        aria-label="Execution price per share (blank uses closing price)" />
    </div>
    {#if saveError}<div class="tt-save-err" role="alert">{saveError}</div>{/if}
  </div>
</div>

<style>
  .trade-card { position: relative; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; overflow: hidden; cursor: pointer; }
  .trade-card .kpi-value { font-size: 22px; }
  /* keep the headline clear of the badge in the corner */
  .tt-head { padding-right: 38px; }

  .tt-badge { position: absolute; top: 12px; right: 12px; z-index: 1; overflow: visible;
    transition: transform .2s cubic-bezier(.34, 1.56, .5, 1); }
  .trade-card:hover .tt-badge { transform: translateY(-2px); }

  .tt-foot-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .tt-split { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; color: var(--ink); opacity: .6; white-space: nowrap; }
  .tt-last { font-family: var(--mono); font-size: 11px; font-weight: 700; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* Logger panel: Svelte-orange bar floats up to 60% of the tile on click, rounded top.
     Everything inside sits on this fixed light bg, so its controls use fixed ink/white
     colors (NOT theme vars) — otherwise dark-mode --ink turns the input text white-on-white. */
  .tt-rise {
    position: absolute; left: 0; right: 0; bottom: 0; height: 0;
    background: #FF3E00;
    border-radius: 16px 16px 0 0;
    z-index: 2; overflow: hidden; cursor: default;
    display: flex; flex-direction: column; justify-content: center; gap: 7px;
    padding: 0 12px;
    transition: height .45s cubic-bezier(.22, 1, .36, 1);
  }
  .trade-card.open .tt-rise { height: 60%; }

  /* Entry: one conjoined bar — [ Buy/Sell ] [ ticker ] [ shares ] [ ✓ ].
     Fixed ink/white colors (see .tt-rise note) so it reads in both themes. */
  .tt-entry { flex: 0 0 auto; display: flex; align-items: stretch; height: 30px;
    background: #fff; border: var(--bw) solid #1a1a1a; border-radius: var(--r); overflow: hidden; box-shadow: var(--sh); }
  .tt-entry.invalid { background: #ffd9d9; }
  .tt-entry.invalid .tt-in { background: #ffd9d9; }
  .tt-seg { flex: 0 0 auto; padding: 0; border: 0; background: #1a1a1a; color: #fff;
    font-family: var(--sans); font-size: 12px; font-weight: 800; line-height: 1; cursor: pointer;
    display: flex; align-items: center; justify-content: center; }
  .tt-side { flex: 0 0 46px; width: 46px; border-right: var(--bw) solid #1a1a1a; }
  .tt-save { flex: 0 0 30px; width: 30px; border-left: var(--bw) solid #1a1a1a; font-size: 15px; }
  .tt-seg:active { background: #000; }
  .tt-save:disabled { opacity: .4; cursor: default; }

  .tt-in { min-width: 0; padding: 0 8px; border: 0; outline: none; background: #fff;
    font-family: var(--mono); font-size: 13px; font-weight: 700; color: #1a1a1a; font-variant-numeric: tabular-nums;
    -moz-appearance: textfield; appearance: textfield; }
  .tt-ticker { flex: 1 1 auto; border-right: var(--bw) solid #1a1a1a; }
  .tt-shares { flex: 0 0 58px; width: 58px; }
  .tt-in::placeholder { color: #1a1a1a; opacity: .3; }
  .tt-in::-webkit-outer-spin-button, .tt-in::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  /* Date row — native date input plus the execution-price box to its right. */
  .tt-date-row { flex: 0 0 auto; display: flex; gap: 7px; }
  .tt-date-input, .tt-price-input { box-sizing: border-box; height: 28px; min-width: 0;
    padding: 0 12px; border: var(--bw) solid #1a1a1a; border-radius: var(--r); background: #fff; box-shadow: var(--sh);
    font-family: var(--mono); font-size: 12px; font-weight: 700; color: #1a1a1a; }
  .tt-date-input { flex: 1 1 auto; cursor: pointer; }
  .tt-date-input::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .85; }
  .tt-price-input { flex: 0 0 84px; padding: 0 8px; font-variant-numeric: tabular-nums;
    -moz-appearance: textfield; appearance: textfield; }
  .tt-price-input::placeholder { color: #1a1a1a; opacity: .3; }
  .tt-price-input::-webkit-outer-spin-button, .tt-price-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  .tt-save-err { flex: 0 0 auto; color: #1a1a1a; font-family: var(--mono); font-size: 10px; font-weight: 700; text-align: center; }

  @media (prefers-reduced-motion: reduce) {
    .tt-badge { transition: none; }
    .trade-card:hover .tt-badge { transform: none; }
    .tt-rise { transition: none; }
  }
</style>

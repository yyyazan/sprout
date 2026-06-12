<script>
  // Shared activity lists — born as the mobile Log pane's rows, now used by BOTH
  // the phone Log pane and the desktop /trades page. Each section (trades ·
  // transactions · optional realized P&L) shows a recent slice and expands via
  // "view all"; an active search always shows every match. Entry lives elsewhere
  // (dashboard cash tile + trade ticket) — these lists are read-only.
  import { fmt } from '$lib/format.js';

  // realized = null hides the FIFO section (mobile); pass the /api/realized list on desktop
  let { trades = [], txns = [], realized = null } = $props();

  const RECENT = 6;   // collapsed slice size

  // ── trades: search by ticker/action ──
  let tradeQ = $state('');
  let tradesAll = $state(false);
  const tradesFiltered = $derived.by(() => {
    const q = tradeQ.trim().toLowerCase();
    const list = q
      ? trades.filter((t) => `${t.ticker} ${t.action}`.toLowerCase().includes(q))
      : trades;
    return tradesAll || q ? list : list.slice(0, RECENT);
  });

  // ── transactions: date + amount only; search by date ──
  let txnQ = $state('');
  let txnsAll = $state(false);
  const txnsFiltered = $derived.by(() => {
    const q = txnQ.trim().toLowerCase();
    const list = q ? txns.filter((x) => (x.date || '').toLowerCase().includes(q)) : txns;
    return txnsAll || q ? list : list.slice(0, RECENT);
  });

  // ── realized FIFO lots: search by ticker ──
  let realQ = $state('');
  let realAll = $state(false);
  const realFiltered = $derived.by(() => {
    const q = realQ.trim().toLowerCase();
    const list = q
      ? (realized ?? []).filter((r) => (r.ticker || '').toLowerCase().includes(q))
      : (realized ?? []);
    return realAll || q ? list : list.slice(0, RECENT);
  });
</script>

<div class="al-grid">
  <!-- TRADES -->
  <section class="al-sec">
    <div class="al-sec-head">
      <span class="al-sec-title">Trades</span>
      {#if trades.length > RECENT && !tradeQ.trim()}
        <button class="al-viewall" onclick={() => (tradesAll = !tradesAll)}>
          {tradesAll ? 'show less' : `view all ${trades.length}`}
        </button>
      {/if}
    </div>
    <div class="al-search">
      <span class="al-search-ic" aria-hidden="true">⌕</span>
      <input class="al-search-in" type="search" bind:value={tradeQ} placeholder="Search trades by ticker…"
        autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" aria-label="Search trades" />
    </div>
    {#if tradesFiltered.length}
      {#each tradesFiltered as t (t.date + t.ticker + t.action + t.shares)}
        <div class="al-row">
          <span class="al-sym">{t.ticker}</span>
          <span class="al-kind {t.action === 'buy' ? 'up' : 'down'}">{t.action}</span>
          <span class="al-fig">{fmt.shares(t.shares)} sh{#if t.price != null}<span class="al-px"> @ {fmt.money2(t.price)}</span>{/if}</span>
          <span class="al-date">{t.date}</span>
        </div>
      {/each}
    {:else}
      <div class="al-empty">{tradeQ.trim() ? 'No matching trades.' : 'No trades yet.'}</div>
    {/if}
  </section>

  <!-- TRANSACTIONS — date is the headline, amount sits rightmost -->
  <section class="al-sec">
    <div class="al-sec-head">
      <span class="al-sec-title">Transactions</span>
      {#if txns.length > RECENT && !txnQ.trim()}
        <button class="al-viewall" onclick={() => (txnsAll = !txnsAll)}>
          {txnsAll ? 'show less' : `view all ${txns.length}`}
        </button>
      {/if}
    </div>
    <div class="al-search">
      <span class="al-search-ic" aria-hidden="true">⌕</span>
      <input class="al-search-in" type="search" bind:value={txnQ} placeholder="Search by date (YYYY-MM-DD)…"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Search transactions" />
    </div>
    {#if txnsFiltered.length}
      {#each txnsFiltered as x (x.date + x.amount)}
        <div class="al-row al-row-txn">
          <span class="al-txn-date">{x.date}</span>
          <span class="al-txn-amt {x.amount >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(x.amount)}</span>
        </div>
      {/each}
    {:else}
      <div class="al-empty">{txnQ.trim() ? 'No matching transactions.' : 'No transactions yet.'}</div>
    {/if}
  </section>

  <!-- REALIZED P&L (FIFO) — desktop log only; each row is one closed lot -->
  {#if realized}
    <section class="al-sec al-sec-wide">
      <div class="al-sec-head">
        <span class="al-sec-title">Realized P&L · FIFO</span>
        {#if realized.length > RECENT && !realQ.trim()}
          <button class="al-viewall" onclick={() => (realAll = !realAll)}>
            {realAll ? 'show less' : `view all ${realized.length}`}
          </button>
        {/if}
      </div>
      <div class="al-search">
        <span class="al-search-ic" aria-hidden="true">⌕</span>
        <input class="al-search-in" type="search" bind:value={realQ} placeholder="Search lots by ticker…"
          autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" aria-label="Search realized lots" />
      </div>
      {#if realFiltered.length}
        {#each realFiltered as r (r.ticker + r.buy_date + r.sell_date + r.shares)}
          <div class="al-row">
            <span class="al-sym">{r.ticker}</span>
            <span class="al-lot">{fmt.shares(r.shares)} sh · {fmt.money2(r.buy_price)} → {fmt.money2(r.sell_price)}</span>
            <span class="al-date">{r.buy_date} → {r.sell_date}</span>
            <span class="al-real {r.realized_pnl >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(r.realized_pnl)}</span>
          </div>
        {/each}
      {:else}
        <div class="al-empty">{realQ.trim() ? 'No matching lots.' : 'Nothing realized yet.'}</div>
      {/if}
    </section>
  {/if}
</div>

<style>
  /* one column on the phone; trades | transactions side by side on desktop,
     with the realized section spanning the full width underneath */
  .al-grid { display: grid; grid-template-columns: 1fr; column-gap: 40px; align-items: start; }
  .al-sec { min-width: 0; }
  @media (min-width: 900px) {
    .al-grid { grid-template-columns: 1fr 1fr; }
    .al-sec-wide { grid-column: 1 / -1; }
  }

  .al-sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px;
    padding: 20px 2px 8px; }
  .al-sec-title { font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .al-viewall { font-family: var(--mono); font-size: 11px; font-weight: 700; color: var(--ink);
    background: transparent; border: 0; padding: 0; cursor: pointer; text-decoration: underline;
    text-underline-offset: 3px; text-decoration-color: color-mix(in srgb, var(--ink) 35%, transparent); }

  /* search bar — same language as the main mobile search */
  .al-search { display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
    padding: 8px 10px; border: var(--bw) solid var(--hairline); border-radius: var(--r); }
  .al-search-ic { font-size: 14px; color: var(--muted); flex: 0 0 auto; }
  .al-search-in { flex: 1 1 auto; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--text); font-family: var(--sans); font-size: 13px; font-weight: 600;
    -webkit-appearance: none; appearance: none; }
  .al-search-in::placeholder { color: var(--muted); font-weight: 500; }
  .al-search-in::-webkit-search-cancel-button { -webkit-appearance: none; }
  /* iOS focus-zoom guard — inputs under 16px make Safari zoom the page */
  @media (max-width: 700px) { .al-search-in { font-size: 16px; } }

  .al-empty { padding: 14px 4px; font-family: var(--mono); font-size: 12px; color: var(--muted); }

  .al-row { display: flex; align-items: baseline; gap: 10px; min-height: 44px; padding: 10px 4px;
    border-bottom: var(--bw) solid var(--hairline); box-sizing: border-box; }
  .al-sym { flex: 0 0 auto; font-family: var(--mono); font-size: 13px; font-weight: 700; }
  .al-kind { flex: 0 0 auto; font-family: var(--sans); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; }
  .al-fig { flex: 1 1 auto; text-align: right; font-family: var(--mono); font-size: 12px; font-weight: 700;
    font-variant-numeric: tabular-nums; }
  .al-px { font-weight: 700; color: var(--muted); }
  .al-date { flex: 0 0 auto; font-family: var(--mono); font-size: 11px; color: var(--muted);
    font-variant-numeric: tabular-nums; }

  /* transaction row: date is the headline (left, ink), amount rightmost */
  .al-row-txn { align-items: center; }
  .al-txn-date { flex: 1 1 auto; font-family: var(--mono); font-size: 15px; font-weight: 700;
    color: var(--ink); font-variant-numeric: tabular-nums; }
  .al-txn-amt { flex: 0 0 auto; font-family: var(--mono); font-size: 14px; font-weight: 700;
    font-variant-numeric: tabular-nums; }

  /* realized lot row: lot detail fills the middle, P&L rightmost */
  .al-lot { flex: 1 1 auto; min-width: 0; font-family: var(--mono); font-size: 11.5px; color: var(--muted);
    font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .al-real { flex: 0 0 auto; font-family: var(--mono); font-size: 13px; font-weight: 700;
    font-variant-numeric: tabular-nums; }

  .up { color: var(--gain); }
  .down { color: var(--loss); }
</style>

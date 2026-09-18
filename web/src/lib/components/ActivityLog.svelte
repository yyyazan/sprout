<script>
  // Shared activity lists — the phone Log pane and the desktop /trades page
  // both render this. Each section (trades · transactions · optional realized
  // lots) shows a recent slice and expands via "View all"; an active search
  // always shows every match. Read-only: entry lives in the cash + trade tiles.
  import { fmt } from '$lib/format.js';
  import TickerBadge from './TickerBadge.svelte';

  // realized = null hides the lots section (mobile); pass /api/realized on desktop
  let { trades = [], txns = [], realized = null, recent = 6 } = $props();

  // "8.0000" reads like a spreadsheet; keep the precision, drop the padding
  const sh = (n) => n == null ? '' : Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 });

  // ── trades: search by ticker/action ──
  let tradeQ = $state('');
  let tradesAll = $state(false);
  const tradesFiltered = $derived.by(() => {
    const q = tradeQ.trim().toLowerCase();
    const list = q
      ? trades.filter((t) => `${t.ticker} ${t.action}`.toLowerCase().includes(q))
      : trades;
    return tradesAll || q ? list : list.slice(0, recent);
  });

  // ── transactions: search by date ──
  let txnQ = $state('');
  let txnsAll = $state(false);
  const txnsFiltered = $derived.by(() => {
    const q = txnQ.trim().toLowerCase();
    const list = q ? txns.filter((x) => (x.date || '').toLowerCase().includes(q)) : txns;
    return txnsAll || q ? list : list.slice(0, recent);
  });

  // ── realized FIFO lots: search by ticker ──
  let realQ = $state('');
  let realAll = $state(false);
  const realFiltered = $derived.by(() => {
    const q = realQ.trim().toLowerCase();
    const list = q
      ? (realized ?? []).filter((r) => (r.ticker || '').toLowerCase().includes(q))
      : (realized ?? []);
    return realAll || q ? list : list.slice(0, recent);
  });
</script>

<!-- rows are keyed by index on purpose: two identical fills on one day are
     legitimate and a content key would throw on the duplicate -->
<div class="al-grid">
  <section class="al-sec">
    <div class="al-head">
      <span class="al-title">Trades</span>
      <label class="al-search">
        <span class="al-search-ic" aria-hidden="true">⌕</span>
        <input type="search" bind:value={tradeQ} placeholder="Search"
          autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" aria-label="Search trades" />
      </label>
      {#if trades.length > recent}
        <button class="btn btn-sm btn-quiet" class:al-hide={tradeQ.trim()} onclick={() => (tradesAll = !tradesAll)}>
          {tradesAll ? 'Show less' : `View all ${trades.length}`}
        </button>
      {/if}
    </div>
    {#if tradesFiltered.length}
      {#each tradesFiltered as t, i (i)}
        <div class="al-row al-trade">
          <TickerBadge sym={t.ticker} />
          <span class="al-kind {t.action === 'buy' ? 'up' : 'down'}">{t.action === 'buy' ? 'Buy' : 'Sell'}</span>
          <span class="al-fig">{sh(t.shares)} sh{#if t.price != null}&nbsp;<span class="dim">@ {fmt.money2(t.price)}</span>{/if}</span>
          <span class="al-date">{t.date}</span>
        </div>
      {/each}
    {:else}
      <div class="al-empty">{tradeQ.trim() ? 'No matching trades.' : 'No trades yet.'}</div>
    {/if}
  </section>

  <section class="al-sec">
    <div class="al-head">
      <span class="al-title">Transactions</span>
      <label class="al-search">
        <span class="al-search-ic" aria-hidden="true">⌕</span>
        <input type="search" bind:value={txnQ} placeholder="Search"
          autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Search transactions" />
      </label>
      {#if txns.length > recent}
        <button class="btn btn-sm btn-quiet" class:al-hide={txnQ.trim()} onclick={() => (txnsAll = !txnsAll)}>
          {txnsAll ? 'Show less' : `View all ${txns.length}`}
        </button>
      {/if}
    </div>
    {#if txnsFiltered.length}
      {#each txnsFiltered as x, i (i)}
        <div class="al-row al-txn">
          <span class="al-date al-lead">{x.date}</span>
          <span class="al-kind-q">{x.direction ?? (x.amount >= 0 ? 'Deposit' : 'Withdrawal')}</span>
          <span class="al-fig {x.amount >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(x.amount)}</span>
        </div>
      {/each}
    {:else}
      <div class="al-empty">{txnQ.trim() ? 'No matching transactions.' : 'No transactions yet.'}</div>
    {/if}
  </section>

  <!-- realized lots (FIFO) — desktop only; each row is one closed lot -->
  {#if realized}
    <section class="al-sec al-sec-wide">
      <div class="al-head">
        <span class="al-title">Realized</span>
        <label class="al-search">
          <span class="al-search-ic" aria-hidden="true">⌕</span>
          <input type="search" bind:value={realQ} placeholder="Search"
            autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" aria-label="Search realized lots" />
        </label>
        {#if realized.length > recent}
          <button class="btn btn-sm btn-quiet" class:al-hide={realQ.trim()} onclick={() => (realAll = !realAll)}>
            {realAll ? 'Show less' : `View all ${realized.length}`}
          </button>
        {/if}
      </div>
      {#if realFiltered.length}
        {#each realFiltered as r, i (i)}
          <div class="al-row al-lot">
            <TickerBadge sym={r.ticker} />
            <span class="al-fig">{sh(r.shares)} sh</span>
            <span class="al-fig dim">{fmt.money2(r.buy_price)} → {fmt.money2(r.sell_price)}</span>
            <span class="al-date">{r.buy_date} → {r.sell_date}</span>
            <span class="al-fig al-pnl {r.realized_pnl >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(r.realized_pnl)}</span>
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
     with the realized lots spanning the full width underneath */
  .al-grid { display: grid; grid-template-columns: 1fr; column-gap: 40px; row-gap: 8px; align-items: start; }
  .al-sec { min-width: 0; }
  @media (min-width: 900px) {
    .al-grid { grid-template-columns: 1fr 1fr; }
    .al-sec-wide { grid-column: 1 / -1; }
  }

  /* section head: title, then the search and the expand control pushed right */
  .al-head { display: flex; align-items: center; gap: 8px; padding: 14px 0 6px; }
  /* a search hides the expand control without letting the head shift */
  .al-hide { visibility: hidden; }
  .al-title { flex: 1 1 auto; font-size: var(--fs-title); font-weight: 600; color: var(--ink); }

  .al-search { flex: 0 1 180px; min-width: 0; display: flex; align-items: center; gap: 6px;
    padding: 4px 10px; border: var(--bw) solid var(--hairline); border-radius: 999px;
    transition: border-color .12s ease; }
  .al-search:focus-within { border-color: var(--ink); }
  .al-search-ic { font-size: 13px; color: var(--muted); flex: 0 0 auto; }
  .al-search input { flex: 1 1 auto; min-width: 0; width: 100%; border: 0; outline: 0; background: transparent;
    color: var(--text); font-family: var(--sans); font-size: var(--fs-body); font-weight: 500;
    -webkit-appearance: none; appearance: none; }
  .al-search input::placeholder { color: var(--muted); }
  .al-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
  /* phone: search takes its own line; inputs under 16px make Safari zoom the page */
  @media (max-width: 700px) {
    .al-head { flex-wrap: wrap; }
    .al-search { flex: 1 1 100%; order: 3; }
    .al-search input { font-size: 16px; }
  }

  .al-empty { padding: 14px 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  /* rows: hairline between repeated rows only; each row type is its own grid
     so the columns line up down the list */
  .al-row { display: grid; align-items: center; column-gap: 12px; min-height: 44px; padding: 8px 0;
    border-bottom: var(--bw) solid var(--hairline); box-sizing: border-box; }
  .al-trade { grid-template-columns: auto auto 1fr auto; }
  .al-txn { grid-template-columns: auto 1fr auto; }
  .al-lot { grid-template-columns: auto auto auto 1fr auto; }

  .al-kind { font-size: var(--fs-body); font-weight: 500; }
  .al-kind-q { font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .al-fig { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    font-variant-numeric: tabular-nums; white-space: nowrap; }
  .al-trade .al-fig { text-align: right; }
  .al-lot .al-fig.dim { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .al-pnl { min-width: 84px; text-align: right; }
  .dim { color: var(--muted); }
  .al-date { font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted);
    font-variant-numeric: tabular-nums; white-space: nowrap; }
  /* transaction rows lead with the date, so it takes the body size in ink */
  .al-lead { font-size: var(--fs-body); color: var(--ink); }

  .up { color: var(--gain-ink); }
  .down { color: var(--loss-ink); }
</style>

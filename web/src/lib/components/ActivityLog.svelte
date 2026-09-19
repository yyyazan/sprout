<script>
  // Shared activity lists — the phone Log pane and the desktop /trades page
  // both render this, stacked trades → transactions → realized (never side by
  // side — a wide two-column layout is what made the rows hard to scan and
  // forced three separate search bars). One search filters all three lists at
  // once. Column order is deliberately the same shape everywhere — date leads,
  // a colored headline figure (buy/sell, amount, or P&L) trails — so the eye
  // doesn't have to relearn the row on every section. Entry lives in the cash
  // + trade tiles; trades and transactions can also be edited or deleted in
  // place here — realized lots are FIFO-computed from the trade history, not
  // stored, so they're read-only and just fall out of whatever trades remain
  // after an edit.
  import { fmt } from '$lib/format.js';
  import { api } from '$lib/api.js';
  import { loadTrades } from '$lib/stores.js';
  import TickerBadge from './TickerBadge.svelte';

  const today = () => new Date().toISOString().slice(0, 10);
  const TICKER_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;

  // onChanged: called after any edit/delete saves, so the parent can refresh
  // whatever else the mutation touches (dashboard KPIs, realized lots, txns).
  let { trades = [], txns = [], realized = null, recent = 6, onChanged = null } = $props();

  // "8.0000" reads like a spreadsheet; keep the precision, drop the padding
  const sh = (n) => n == null ? '' : Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 });

  // ── trade row actions: edit-in-place / delete-with-confirm ──
  let editTradeId = $state(null);
  let delTradeId = $state(null);
  let etTicker = $state(''), etAction = $state('buy'), etShares = $state(''), etPrice = $state(''), etDate = $state('');
  let etSaving = $state(false), etError = $state(null);

  function startEditTrade(t) {
    delTradeId = null;
    editTradeId = t.id;
    etTicker = t.ticker; etAction = t.action; etShares = String(t.shares);
    etPrice = t.price == null ? '' : String(t.price); etDate = t.date;
    etError = null;
  }
  const cancelEditTrade = () => (editTradeId = null);

  async function saveEditTrade(id) {
    if (etSaving) return;
    const tk = (etTicker || '').trim().toUpperCase();
    if (!TICKER_RE.test(tk)) { etError = 'Invalid ticker'; return; }
    if (!(Number(etShares) > 0)) { etError = 'Shares > 0'; return; }
    if (etPrice !== '' && !(Number(etPrice) > 0)) { etError = 'Price > 0'; return; }
    etSaving = true; etError = null;
    try {
      const res = await api.editTrade(id, {
        ticker: tk, action: etAction, shares: Number(etShares),
        price: etPrice === '' ? null : Number(etPrice), trade_date: etDate
      });
      if (res?.ok) {
        editTradeId = null;
        await loadTrades(true);
        onChanged?.();
      } else {
        etError = res?.errors ? Object.values(res.errors)[0] : 'Save failed';
      }
    } catch {
      etError = 'Save failed';
    } finally {
      etSaving = false;
    }
  }

  const askDeleteTrade = (id) => { editTradeId = null; delTradeId = id; };
  const cancelDeleteTrade = () => (delTradeId = null);
  async function confirmDeleteTrade(id) {
    delTradeId = null;
    const res = await api.deleteTrade(id).catch(() => null);
    if (res?.ok) { await loadTrades(true); onChanged?.(); }
  }

  // ── transaction row actions: same shape as trades, one field set ──
  let editTxnId = $state(null);
  let delTxnId = $state(null);
  let exSign = $state('+'), exAmount = $state(''), exDate = $state('');
  let exSaving = $state(false), exError = $state(null);

  function startEditTxn(x) {
    delTxnId = null;
    editTxnId = x.id;
    exSign = x.amount >= 0 ? '+' : '-';
    exAmount = String(Math.abs(x.amount));
    exDate = x.date;
    exError = null;
  }
  const cancelEditTxn = () => (editTxnId = null);

  async function saveEditTxn(id) {
    if (exSaving) return;
    if (!(Number(exAmount) > 0)) { exError = 'Amount > 0'; return; }
    exSaving = true; exError = null;
    try {
      const res = await api.editTransaction(id, {
        txn_date: exDate, txn_type: exSign === '+' ? 'Deposit' : 'Withdrawal', amount: Number(exAmount)
      });
      if (res?.ok) {
        editTxnId = null;
        onChanged?.();
      } else {
        exError = res?.error || 'Save failed';
      }
    } catch {
      exError = 'Save failed';
    } finally {
      exSaving = false;
    }
  }

  const askDeleteTxn = (id) => { editTxnId = null; delTxnId = id; };
  const cancelDeleteTxn = () => (delTxnId = null);
  async function confirmDeleteTxn(id) {
    delTxnId = null;
    const res = await api.deleteTransaction(id).catch(() => null);
    if (res?.ok) onChanged?.();
  }

  // ── one search box drives all three lists ──
  let query = $state('');
  const q = $derived(query.trim().toLowerCase());

  let tradesAll = $state(false);
  const tradesFiltered = $derived.by(() => {
    const list = q ? trades.filter((t) => `${t.ticker} ${t.action} ${t.date}`.toLowerCase().includes(q)) : trades;
    return tradesAll || q ? list : list.slice(0, recent);
  });

  let txnsAll = $state(false);
  const txnsFiltered = $derived.by(() => {
    const list = q ? txns.filter((x) => `${x.date} ${x.direction ?? ''}`.toLowerCase().includes(q)) : txns;
    return txnsAll || q ? list : list.slice(0, recent);
  });

  let realAll = $state(false);
  const realFiltered = $derived.by(() => {
    const list = q ? (realized ?? []).filter((r) => (r.ticker || '').toLowerCase().includes(q)) : (realized ?? []);
    return realAll || q ? list : list.slice(0, recent);
  });
</script>

<div class="al-wrap">
  <label class="al-search">
    <span class="al-search-ic" aria-hidden="true">⌕</span>
    <input type="search" bind:value={query} placeholder="Search trades, transactions, realized"
      autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" aria-label="Search activity" />
  </label>

  <section class="al-sec">
    <div class="al-head"><span class="al-title">Trades</span></div>
    {#if tradesFiltered.length}
      <div class="al-colhead al-trade" aria-hidden="true">
        <span>Ticker</span><span>Action</span><span>Shares</span><span>Date</span><span>Price</span><span></span>
      </div>
      <div class="al-rows" class:al-fade={!tradesAll && !q && trades.length > recent}>
        {#each tradesFiltered as t (t.id)}
          {#if editTradeId === t.id}
            <div class="al-row al-edit">
              <button type="button" class="al-e-side" class:pos={etAction === 'buy'} class:neg={etAction === 'sell'}
                onclick={() => (etAction = etAction === 'buy' ? 'sell' : 'buy')}>{etAction === 'buy' ? 'Buy' : 'Sell'}</button>
              <div class="al-e-fields">
                <input class="al-e-in al-e-ticker" bind:value={etTicker} style="text-transform:uppercase" aria-label="Ticker" />
                <input class="al-e-in" type="number" step="any" min="0" inputmode="decimal" placeholder="shares" bind:value={etShares} aria-label="Shares" />
                <input class="al-e-date" type="date" bind:value={etDate} max={today()} aria-label="Date" />
                <input class="al-e-in" type="number" step="any" min="0" inputmode="decimal" placeholder="price" bind:value={etPrice} aria-label="Price" />
              </div>
              <span class="al-e-actions">
                <button type="button" class="al-e-btn" disabled={etSaving} onclick={() => saveEditTrade(t.id)} aria-label="Save">✓</button>
                <button type="button" class="al-e-btn al-e-quiet" onclick={cancelEditTrade} aria-label="Cancel">✕</button>
              </span>
              {#if etError}<div class="al-e-err" role="alert">{etError}</div>{/if}
            </div>
          {:else if delTradeId === t.id}
            <div class="al-row al-del-row">
              <span class="al-del-prompt">Delete this trade?</span>
              <span class="al-e-actions">
                <button type="button" class="al-e-btn al-e-danger" onclick={() => confirmDeleteTrade(t.id)}>Delete</button>
                <button type="button" class="al-e-btn al-e-quiet" onclick={cancelDeleteTrade}>Cancel</button>
              </span>
            </div>
          {:else}
            <div class="al-row al-trade">
              <span class="al-tkr"><TickerBadge sym={t.ticker} /></span>
              <span class="al-kind {t.action === 'buy' ? 'up' : 'down'}">{t.action === 'buy' ? 'Buy' : 'Sell'}</span>
              <span class="al-fig">{sh(t.shares)}</span>
              <span class="al-date">{t.date}</span>
              <span class="al-fig">{t.price != null ? fmt.money2(t.price) : '—'}</span>
              <span class="al-row-actions">
                <button type="button" class="al-ic" onclick={() => startEditTrade(t)} aria-label="Edit trade">✎</button>
                <button type="button" class="al-ic" onclick={() => askDeleteTrade(t.id)} aria-label="Delete trade">✕</button>
              </span>
            </div>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="al-empty">{q ? 'No matching trades.' : 'No trades yet.'}</div>
    {/if}
    {#if trades.length > recent && !q}
      <div class="al-viewall-wrap">
        <button class="btn btn-sm btn-quiet" onclick={() => (tradesAll = !tradesAll)}>
          {tradesAll ? 'Show less' : `View all ${trades.length}`}
        </button>
      </div>
    {/if}
  </section>

  <section class="al-sec">
    <div class="al-head"><span class="al-title">Transactions</span></div>
    {#if txnsFiltered.length}
      <div class="al-colhead al-txn" aria-hidden="true">
        <span>Date</span><span>Amount</span><span></span>
      </div>
      <div class="al-rows" class:al-fade={!txnsAll && !q && txns.length > recent}>
        {#each txnsFiltered as x (x.id)}
          {#if editTxnId === x.id}
            <div class="al-row al-edit">
              <button type="button" class="al-e-side" class:pos={exSign === '+'} class:neg={exSign === '-'}
                onclick={() => (exSign = exSign === '+' ? '-' : '+')}>{exSign === '+' ? 'Deposit' : 'Withdraw'}</button>
              <div class="al-e-fields al-e-fields-1row">
                <input class="al-e-in" type="number" step="any" min="0" inputmode="decimal" placeholder="amount" bind:value={exAmount} aria-label="Amount" />
                <input class="al-e-date" type="date" bind:value={exDate} max={today()} aria-label="Date" />
              </div>
              <span class="al-e-actions">
                <button type="button" class="al-e-btn" disabled={exSaving} onclick={() => saveEditTxn(x.id)} aria-label="Save">✓</button>
                <button type="button" class="al-e-btn al-e-quiet" onclick={cancelEditTxn} aria-label="Cancel">✕</button>
              </span>
              {#if exError}<div class="al-e-err" role="alert">{exError}</div>{/if}
            </div>
          {:else if delTxnId === x.id}
            <div class="al-row al-del-row">
              <span class="al-del-prompt">Delete this transaction?</span>
              <span class="al-e-actions">
                <button type="button" class="al-e-btn al-e-danger" onclick={() => confirmDeleteTxn(x.id)}>Delete</button>
                <button type="button" class="al-e-btn al-e-quiet" onclick={cancelDeleteTxn}>Cancel</button>
              </span>
            </div>
          {:else}
            <div class="al-row al-txn">
              <span class="al-date">{x.date}</span>
              <span class="al-fig {x.amount >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(x.amount)}</span>
              <span class="al-row-actions">
                <button type="button" class="al-ic" onclick={() => startEditTxn(x)} aria-label="Edit transaction">✎</button>
                <button type="button" class="al-ic" onclick={() => askDeleteTxn(x.id)} aria-label="Delete transaction">✕</button>
              </span>
            </div>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="al-empty">{q ? 'No matching transactions.' : 'No transactions yet.'}</div>
    {/if}
    {#if txns.length > recent && !q}
      <div class="al-viewall-wrap">
        <button class="btn btn-sm btn-quiet" onclick={() => (txnsAll = !txnsAll)}>
          {txnsAll ? 'Show less' : `View all ${txns.length}`}
        </button>
      </div>
    {/if}
  </section>

  <!-- realized lots (FIFO) — each row is one closed lot, read-only, newest
       close first (fifo_realized groups by ticker internally, so the API
       re-sorts by sell date — see api/serialize.py:realized_payload) -->
  {#if realized}
    <section class="al-sec">
      <div class="al-head"><span class="al-title">Realized</span></div>
      {#if realFiltered.length}
        <div class="al-colhead al-lot" aria-hidden="true">
          <span>Ticker</span><span>Shares</span><span>Date</span><span>P&amp;L</span>
        </div>
        <div class="al-rows" class:al-fade={!realAll && !q && realized.length > recent}>
          {#each realFiltered as r, i (i)}
            <div class="al-row al-lot">
              <span class="al-tkr"><TickerBadge sym={r.ticker} /></span>
              <span class="al-fig">{sh(r.shares)}</span>
              <span class="al-date">{r.sell_date}</span>
              <span class="al-fig {r.realized_pnl >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(r.realized_pnl)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <div class="al-empty">{q ? 'No matching lots.' : 'Nothing realized yet.'}</div>
      {/if}
      {#if realized.length > recent && !q}
        <div class="al-viewall-wrap">
          <button class="btn btn-sm btn-quiet" onclick={() => (realAll = !realAll)}>
            {realAll ? 'Show less' : `View all ${realized.length}`}
          </button>
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  /* trades → transactions → realized, always stacked — a side-by-side layout
     was what made the columns hard to line up and pushed three search bars
     into cramped headers. One column, one search, more room per row. */
  .al-wrap { display: flex; flex-direction: column; gap: 26px; }
  .al-sec { min-width: 0; }

  .al-search { width: 100%; max-width: 380px; min-width: 0; display: flex; align-items: center; gap: 6px;
    padding: 6px 12px; border: var(--bw) solid var(--hairline); border-radius: 999px;
    transition: border-color .12s ease; }
  .al-search:focus-within { border-color: var(--ink); }
  .al-search-ic { font-size: 13px; color: var(--muted); flex: 0 0 auto; }
  .al-search input { flex: 1 1 auto; min-width: 0; width: 100%; border: 0; outline: 0; background: transparent;
    color: var(--text); font-family: var(--sans); font-size: var(--fs-body); font-weight: 500;
    -webkit-appearance: none; appearance: none; }
  .al-search input::placeholder { color: var(--muted); }
  .al-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
  @media (max-width: 700px) {
    .al-search { max-width: none; }
    .al-search input { font-size: 16px; } /* under 16px makes Safari zoom the page */
  }

  .al-head { padding: 2px 0 6px; }
  .al-title { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }

  .al-empty { padding: 14px 10px; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  /* column headers and data rows share one grid template per table (.al-trade
     / .al-txn / .al-lot) so a label always sits directly above its column —
     the header just swaps padding/typography, never the geometry. */
  .al-row, .al-colhead { display: grid; align-items: center; column-gap: 6px; box-sizing: border-box; }
  .al-colhead { padding: 0 8px 6px; border-bottom: var(--bw) solid var(--hairline); margin-bottom: 2px; }
  .al-colhead span { min-width: 0; font-size: 10px; font-weight: 600; color: var(--muted); text-align: center;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* rows: alternating wash instead of a hairline per row — reads as a ledger
     at a glance and needs no per-row border. Fades toward transparent at the
     bottom edge when a section is truncated, as a "more below" hint sitting
     right above the View all control. */
  .al-rows { display: flex; flex-direction: column; }
  .al-rows.al-fade {
    mask-image: linear-gradient(to bottom, black calc(100% - 34px), transparent 100%);
    -webkit-mask-image: linear-gradient(to bottom, black calc(100% - 34px), transparent 100%);
  }
  .al-row { min-height: 40px; padding: 7px 8px; border-radius: var(--r); }
  .al-rows > .al-row:nth-child(even) { background: var(--hover); }
  /* an active edit/confirm row reads as its own state, not a resting stripe */
  .al-row.al-edit, .al-row.al-del-row { background: var(--surface); }

  /* every data column shares the row equally (a trailing utility column for
     the hover actions is the one exception — it's chrome, not data, so it
     stays a small fixed width and sits outside the split). Same column order
     everywhere: ticker · action · shares · date · price/amount/P&L, with
     whichever of those a table doesn't have simply omitted. Roomier padding
     past a tablet-ish breakpoint, where headers also pick up their small-caps
     treatment (too cramped to read well at phone widths). */
  .al-trade { grid-template-columns: repeat(5, 1fr) 48px; }
  .al-txn { grid-template-columns: repeat(2, 1fr) 48px; }
  .al-lot { grid-template-columns: repeat(4, 1fr); }
  @media (min-width: 640px) {
    .al-row, .al-colhead { column-gap: 10px; }
    .al-row { padding: 8px 10px; min-height: 44px; }
    .al-colhead { padding: 0 10px 8px; }
    .al-colhead span { text-transform: uppercase; letter-spacing: .05em; }
  }

  /* ticker badge: centered in its column rather than stretched to fill it —
     a 2-letter badge (MU) shouldn't carry as much colored area as a 4-letter
     one (SNDK) just because the column has to fit the longest ticker */
  .al-tkr { display: flex; justify-content: center; min-width: 0; }

  .al-kind { text-align: center; font-size: var(--fs-body); font-weight: 500; }
  .al-fig { min-width: 0; text-align: center; font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .al-date { min-width: 0; text-align: center; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted);
    font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .up { color: var(--gain-ink); }
  .down { color: var(--loss-ink); }

  /* row actions: hidden until the row is hovered/focused, so a full list of
     trades or transactions doesn't read as a wall of buttons — touch devices
     have no hover, so they stay visible there. */
  .al-row-actions { display: flex; gap: 2px; justify-self: end; opacity: 0; pointer-events: none;
    transition: opacity .12s ease; }
  .al-row:hover .al-row-actions, .al-row:focus-within .al-row-actions { opacity: 1; pointer-events: auto; }
  @media (hover: none) {
    .al-row-actions { opacity: 1; pointer-events: auto; }
  }
  .al-ic { width: 22px; height: 22px; padding: 0; border: 0; border-radius: 999px; background: transparent;
    color: var(--muted); font-size: 11px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, color .12s ease; }
  .al-ic:hover { background: var(--hairline); color: var(--ink); }

  /* View all / Show less: bottom of the (possibly faded) list, not the header */
  .al-viewall-wrap { display: flex; justify-content: center; padding: 8px 0 2px; }

  /* edit-in-place: the row swaps its grid for a compact inline form — side/sign
     toggle, a 2×2 field grid (ticker/shares over date/price — same order as
     TradeTicket's add form; 2 fields alone for a transaction), then save/cancel. */
  .al-row.al-edit { grid-template-columns: auto 1fr auto; column-gap: 8px; position: relative; }
  .al-e-side { flex: 0 0 auto; padding: 6px 10px; box-sizing: border-box; border: 1.5px solid var(--hairline);
    border-radius: 999px; background: transparent; font-family: var(--sans); font-size: 11px;
    font-weight: 600; line-height: 1; cursor: pointer; white-space: nowrap; align-self: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .al-e-side.pos { border-color: var(--gain); color: var(--gain); }
  .al-e-side.neg { border-color: var(--loss); color: var(--loss); }
  .al-e-fields { min-width: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .al-e-fields-1row { grid-template-rows: 28px; }
  .al-e-in, .al-e-date { min-width: 0; width: 100%; height: 28px; box-sizing: border-box; padding: 0 8px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; color: var(--ink);
    font-variant-numeric: tabular-nums; -moz-appearance: textfield; }
  .al-e-in::placeholder { color: var(--muted); }
  .al-e-in::-webkit-outer-spin-button, .al-e-in::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
  .al-e-date { cursor: pointer; }
  .al-e-ticker { text-transform: uppercase; }
  .al-e-actions { display: flex; gap: 4px; align-self: center; justify-self: end; }
  .al-e-btn { flex: 0 0 auto; height: 26px; padding: 0 10px; box-sizing: border-box;
    border-radius: 999px; background: transparent; font-size: 12px; font-weight: 600; cursor: pointer;
    border: 1.5px solid var(--hairline); color: var(--ink);
    display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .al-e-btn:hover { border-color: var(--ink); }
  .al-e-btn:disabled { opacity: .4; cursor: default; }
  .al-e-quiet { color: var(--muted); }
  .al-e-danger { border-color: var(--loss); color: var(--loss); }
  .al-e-danger:hover { background: var(--loss); color: var(--paper); }
  .al-e-err { grid-column: 1 / -1; color: var(--loss); font-family: var(--num); font-size: var(--fs-meta);
    font-weight: 600; padding-top: 4px; }

  /* delete confirm: replaces the row's content with a plain yes/no prompt */
  .al-del-row { grid-template-columns: 1fr auto; }
  .al-del-prompt { font-size: var(--fs-body); font-weight: 500; color: var(--ink); }

  @media (max-width: 700px) {
    .al-row.al-edit { grid-template-columns: 1fr; row-gap: 6px; }
    .al-e-actions { justify-self: start; }
  }
</style>

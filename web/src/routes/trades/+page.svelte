<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { fmt } from '$lib/format.js';
  import FeedbackButton from '$lib/components/FeedbackButton.svelte';

  const TICKER_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;
  const today = () => new Date().toISOString().slice(0, 10);

  let trades = $state([]);
  let transactions = $state([]);
  let realized = $state([]);
  let tab = $state('trade');

  // Trade form
  let tTicker = $state('');
  let tAction = $state('buy');
  let tShares = $state('');
  let tDate = $state(today());
  let tErrors = $state({});

  // Txn form
  let xType = $state('Deposit');
  let xAmount = $state('');
  let xDate = $state(today());
  let xError = $state(null);

  let tickerLive = $derived(
    tTicker && !TICKER_RE.test(tTicker.toUpperCase()) ? 'Invalid format.' : null
  );
  let sharesLive = $derived(
    tShares !== '' && !(Number(tShares) > 0) ? 'Must be > 0.' : null
  );

  async function loadAll() {
    [trades, transactions, realized] = await Promise.all([
      api.trades(),
      api.transactions(),
      api.realized()
    ]);
  }
  onMount(loadAll);

  // Return the API result so FeedbackButton can drive its working→success/error signal.
  async function submitTrade() {
    const res = await api.addTrade({
      ticker: tTicker,
      action: tAction,
      shares: tShares === '' ? null : Number(tShares),
      trade_date: tDate
    });
    if (res.ok) {
      tErrors = {};
      tTicker = ''; tShares = '';
      await loadAll();
    } else {
      tErrors = res.errors || {};
    }
    return res;
  }

  async function submitTxn() {
    const res = await api.addTransaction({
      txn_date: xDate,
      txn_type: xType,
      amount: xAmount === '' ? null : Number(xAmount)
    });
    if (res.ok) {
      xError = null;
      xAmount = '';
      await loadAll();
    } else {
      xError = res.error;
    }
    return res;
  }
</script>

<div class="content">
  <div class="page-title">Log</div>

  <div class="glass-card">
    <div style="display:flex; gap:8px; margin-bottom:16px">
      <button class="seg" class:active={tab === 'trade'} onclick={() => (tab = 'trade')}>Trade</button>
      <button class="seg" class:active={tab === 'txn'} onclick={() => (tab = 'txn')}>Transaction</button>
    </div>

    {#if tab === 'trade'}
      <div class="form-grid">
        <label>Ticker
          <input bind:value={tTicker} placeholder="AAPL" style="text-transform:uppercase" />
          {#if tErrors.ticker || tickerLive}<span class="field-err">{tErrors.ticker || tickerLive}</span>{/if}
        </label>
        <label>Action
          <select bind:value={tAction}><option value="buy">Buy</option><option value="sell">Sell</option></select>
          {#if tErrors.action}<span class="field-err">{tErrors.action}</span>{/if}
        </label>
        <label>Shares
          <input type="number" step="any" bind:value={tShares} placeholder="1.0" />
          {#if tErrors.shares || sharesLive}<span class="field-err">{tErrors.shares || sharesLive}</span>{/if}
        </label>
        <label>Date
          <input type="date" bind:value={tDate} max={today()} />
          {#if tErrors.date}<span class="field-err">{tErrors.date}</span>{/if}
        </label>
        <FeedbackButton label="Save trade" action={submitTrade} />
      </div>
    {:else}
      <div class="form-grid">
        <label>Type
          <select bind:value={xType}><option>Deposit</option><option>Withdrawal</option></select>
        </label>
        <label>Amount (USD)
          <input type="number" step="any" bind:value={xAmount} placeholder="100.00" />
        </label>
        <label>Date
          <input type="date" bind:value={xDate} max={today()} />
        </label>
        <FeedbackButton label="Save transaction" action={submitTxn} />
      </div>
      {#if xError}<div class="field-err" style="margin-top:10px">{xError}</div>{/if}
    {/if}
  </div>

  <div class="glass-card table-card">
    <div class="chart-title" style="margin-bottom:10px">Trade record</div>
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr><th>Date</th><th>Ticker</th><th>Action</th><th>Shares</th></tr></thead>
        <tbody>
          {#each trades as t}
            <tr><td>{t.date}</td><td>{t.ticker}</td><td>{t.action}</td><td>{fmt.shares(t.shares)}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <div class="glass-card table-card">
    <div class="chart-title" style="margin-bottom:10px">Transactions</div>
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr><th>Date</th><th>Direction</th><th>Amount</th></tr></thead>
        <tbody>
          {#each transactions as x}
            <tr><td>{x.date}</td><td>{x.direction}</td>
              <td><span class={x.amount >= 0 ? 'cell-gain' : 'cell-loss'}>{fmt.signedMoney2(x.amount)}</span></td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <div class="glass-card table-card">
    <div class="chart-title" style="margin-bottom:10px">Realized P&L (FIFO)</div>
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr><th>Ticker</th><th>Shares</th><th>Buy</th><th>Sell</th><th>Buy $</th><th>Sell $</th><th>Realized</th></tr></thead>
        <tbody>
          {#each realized as r}
            <tr>
              <td>{r.ticker}</td><td>{fmt.shares(r.shares)}</td>
              <td>{r.buy_date}</td><td>{r.sell_date}</td>
              <td>{fmt.money2(r.buy_price)}</td><td>{fmt.money2(r.sell_price)}</td>
              <td><span class={r.realized_pnl >= 0 ? 'cell-gain' : 'cell-loss'}>{fmt.signedMoney2(r.realized_pnl)}</span></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</div>

<style>
  .seg { padding: 9px 16px; border: var(--bw) solid var(--ink); border-radius: var(--r); background: var(--surface); font-family: var(--mono); font-size: 13px; font-weight: 700; cursor: pointer; box-shadow: var(--sh); transition: transform .1s ease, box-shadow .1s ease; }
  .seg:hover:not(.active) { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 var(--ink); }
  .seg.active { background: var(--ink); color: var(--surface); }
  .form-grid { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; }
  .form-grid label { display: flex; flex-direction: column; gap: 6px; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  .form-grid input, .form-grid select { padding: 10px 12px; border: var(--bw) solid var(--ink); border-radius: var(--r); font-family: var(--sans); font-size: 14px; color: var(--text); background: var(--surface); box-shadow: var(--sh); }
  .form-grid input:focus, .form-grid select:focus { outline: none; background: #fffdf5; }
  .field-err { color: var(--loss); font-size: 11px; font-weight: 700; }
</style>

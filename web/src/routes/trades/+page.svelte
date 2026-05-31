<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { fmt } from '$lib/format.js';

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
  let tFeedback = $state(null);

  // Txn form
  let xType = $state('Deposit');
  let xAmount = $state('');
  let xDate = $state(today());
  let xError = $state(null);
  let xFeedback = $state(null);

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

  async function submitTrade() {
    tFeedback = null;
    const res = await api.addTrade({
      ticker: tTicker,
      action: tAction,
      shares: tShares === '' ? null : Number(tShares),
      trade_date: tDate
    });
    if (res.ok) {
      tErrors = {};
      tFeedback = { ok: true, msg: `Saved ${tAction} ${tTicker.toUpperCase()}` };
      tTicker = ''; tShares = '';
      await loadAll();
    } else {
      tErrors = res.errors || {};
    }
  }

  async function submitTxn() {
    xFeedback = null;
    const res = await api.addTransaction({
      txn_date: xDate,
      txn_type: xType,
      amount: xAmount === '' ? null : Number(xAmount)
    });
    if (res.ok) {
      xError = null;
      xFeedback = { ok: true, msg: `Saved ${xType.toLowerCase()}` };
      xAmount = '';
      await loadAll();
    } else {
      xError = res.error;
    }
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
        <button class="submit" onclick={submitTrade}>Save trade</button>
      </div>
      {#if tFeedback}<div class="feedback ok">✓ {tFeedback.msg}</div>{/if}
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
        <button class="submit" onclick={submitTxn}>Save transaction</button>
      </div>
      {#if xError}<div class="feedback err">{xError}</div>{/if}
      {#if xFeedback}<div class="feedback ok">✓ {xFeedback.msg}</div>{/if}
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
              <td class={x.amount >= 0 ? 'cell-gain' : 'cell-loss'}>{fmt.signedMoney2(x.amount)}</td></tr>
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
              <td class={r.realized_pnl >= 0 ? 'cell-gain' : 'cell-loss'}>{fmt.signedMoney2(r.realized_pnl)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</div>

<style>
  .seg { padding: 6px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); cursor: pointer; }
  .seg.active { background: var(--border); font-weight: 600; }
  .form-grid { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; }
  .form-grid label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
  .form-grid input, .form-grid select { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; color: var(--text); background: var(--surface); }
  .field-err { color: var(--loss); font-size: 11px; }
  .submit { padding: 9px 16px; border: none; border-radius: 8px; background: var(--accent); color: #fff; font-weight: 600; cursor: pointer; }
  .feedback { margin-top: 12px; padding: 8px 12px; border-radius: 8px; font-size: 13px; }
  .feedback.ok { background: rgba(47,158,125,.12); color: var(--gain); }
  .feedback.err { background: rgba(201,79,79,.12); color: var(--loss); }
</style>

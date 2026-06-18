<script>
  import { fmt } from '$lib/format.js';
  import TickerBadge from './TickerBadge.svelte';
  let { positions } = $props();

  const COLUMNS = [
    { id: 'ticker', name: 'Ticker', f: (v) => v },
    { id: 'shares', name: 'Shares', f: fmt.shares },
    { id: 'cost_basis', name: 'Cost Basis', f: fmt.money2 },
    { id: 'current_price', name: 'Current Price', f: fmt.money2 },
    { id: 'total_invested', name: 'Invested', f: fmt.money2 },
    { id: 'market_value', name: 'Market Value', f: fmt.money2 },
    { id: 'unrealized_pnl', name: 'Unrealized $', f: fmt.signedMoney2, color: true },
    { id: 'return_pct', name: 'Return %', f: fmt.signedPct2, color: true },
    { id: 'weight', name: 'Weight %', f: fmt.pct1 }
  ];

  let sortKey = $state(null);
  let sortDir = $state(1);

  function sortBy(id) {
    if (sortKey === id) sortDir = -sortDir;
    else { sortKey = id; sortDir = 1; }
  }

  let rows = $derived.by(() => {
    const r = [...positions];
    if (sortKey) {
      r.sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        if (typeof x === 'number' && typeof y === 'number') return (x - y) * sortDir;
        return String(x).localeCompare(String(y)) * sortDir;
      });
    }
    return r;
  });
</script>

<div class="glass-card table-card">
  <div class="chart-title" style="margin-bottom:10px">Positions</div>
  <div class="data-table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          {#each COLUMNS as col}
            <th onclick={() => sortBy(col.id)}>{col.name}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row}
          <tr>
            {#each COLUMNS as col}
              <td>
                {#if col.id === 'ticker'}
                  <TickerBadge sym={col.f(row[col.id])} size="md" />
                {:else if col.id === 'return_pct'}
                  <span class="pct-pill {row[col.id] >= 0 ? 'up' : 'down'}">{col.f(row[col.id])}</span>
                {:else if col.color}
                  <span class={row[col.id] >= 0 ? 'cell-gain' : 'cell-loss'}>{col.f(row[col.id])}</span>
                {:else}
                  {col.f(row[col.id])}
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

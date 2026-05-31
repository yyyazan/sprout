<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { twrVsBench, drawdownArea, pnlBars, allocationDonut } from '$lib/plotly.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import ChartCard from '$lib/components/ChartCard.svelte';
  import PositionsTable from '$lib/components/PositionsTable.svelte';

  let d = $state(null);
  let error = $state(null);

  onMount(async () => {
    try {
      d = await api.investments();
    } catch (e) {
      error = String(e);
    }
  });
</script>

{#if error}
  <div class="content"><p style="color:var(--loss)">Failed to load: {error}</p></div>
{:else if d}
  <div class="content">
    <div class="page-title">Investments</div>
    <div class="widget-grid">
      <KpiCard label="TWR" value={d.kpis.twr} kind="percent" size="small" />
      <KpiCard label="Max Drawdown" value={d.kpis.max_drawdown} kind="percent" size="small" />
      <KpiCard label="Sharpe" value={d.kpis.sharpe} kind="ratio" size="small" />
      <KpiCard label="SPY TWR" value={d.kpis.spy_twr} kind="percent" size="small" />
      <KpiCard label="SPY DD" value={d.kpis.spy_dd} kind="percent" size="small" />
      <KpiCard label="SPY Sharpe" value={d.kpis.spy_sharpe} kind="ratio" size="small" />
      <ChartCard title="Time-Weighted Return" subtitle="Strips out cash-flow timing — pure holding performance" figure={twrVsBench(d.charts.twr)} size="large" />
      <ChartCard title="Drawdown" figure={drawdownArea(d.charts.drawdown)} size="large" />
      <ChartCard title="Unrealized P&L by Ticker" figure={pnlBars(d.charts.pnl_bars)} size="large" />
      <ChartCard title="Allocation" figure={allocationDonut(d.charts.allocation)} size="large" />
    </div>
    <PositionsTable positions={d.positions} />
  </div>
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}

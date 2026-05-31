<script>
  import TimeSeriesChart from './TimeSeriesChart.svelte';
  import PnlBars from './PnlBars.svelte';
  import DonutChart from './DonutChart.svelte';

  // `chart` is a tagged spec from charts.js: {kind:'timeseries'|'bars'|'donut', ...}.
  let { title, subtitle = null, chart, size = 'large' } = $props();
</script>

<div class="glass-card chart-card widget-{size}">
  <div class="chart-head">
    <span class="chart-title">{title}</span>
    {#if subtitle}<span class="chart-subtitle">{subtitle}</span>{/if}
  </div>
  {#if chart.kind === 'timeseries'}
    <TimeSeriesChart spec={chart} />
  {:else if chart.kind === 'bars'}
    <PnlBars tickers={chart.tickers} values={chart.values} />
  {:else if chart.kind === 'donut'}
    <DonutChart labels={chart.labels} values={chart.values} />
  {/if}
</div>

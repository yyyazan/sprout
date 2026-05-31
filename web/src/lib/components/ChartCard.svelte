<script>
  import Chart from './Chart.svelte';
  let { title, subtitle = null, figure, size = 'large' } = $props();
</script>

<div class="glass-card chart-card widget-{size}">
  <div class="chart-head">
    <span class="chart-title">{title}</span>
    {#if subtitle}<span class="chart-subtitle">{subtitle}</span>{/if}
  </div>
  <Chart {figure} />
</div>

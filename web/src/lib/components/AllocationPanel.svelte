<script>
  import DonutChart from './DonutChart.svelte';
  import { PALETTE } from '$lib/charts.js';
  let { alloc, size = 'tall' } = $props();
  let total = $derived(alloc.values.reduce((a, b) => a + b, 0));
</script>

<div class="glass-card alloc-panel widget-{size}">
  <div class="alloc-panel-title">Allocation</div>
  <div class="alloc-donut" style="height:190px"><DonutChart labels={alloc.labels} values={alloc.values} /></div>
  <div class="alloc-list">
    {#each alloc.labels as label, i}
      <div class="alloc-row">
        <span class="alloc-dot" style="background:{PALETTE[i % PALETTE.length]}"></span>
        <span class="alloc-ticker">{label}</span>
        <span class="alloc-amount">${alloc.values[i].toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
        <span class="alloc-pct">{total ? ((alloc.values[i] / total) * 100).toFixed(1) : '0.0'}%</span>
      </div>
    {/each}
  </div>
</div>

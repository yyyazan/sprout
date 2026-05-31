<script>
  import { onMount, onDestroy } from 'svelte';
  import { loadPlotly } from '$lib/plotly.js';

  // `figure` is { data, layout, config } from a plotly.js factory.
  let { figure } = $props();

  let host;
  let plotly = null;

  async function draw() {
    if (!host || !figure) return;
    plotly = await loadPlotly();
    plotly.react(host, figure.data, figure.layout, figure.config);
  }

  onMount(draw);

  // Redraw when the figure changes.
  $effect(() => {
    if (figure) draw();
  });

  onDestroy(() => {
    if (plotly && host) plotly.purge(host);
  });
</script>

<div class="plot-host" bind:this={host}></div>

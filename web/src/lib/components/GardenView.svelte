<script>
  import { onMount, onDestroy } from 'svelte';
  let { positions, period } = $props();

  onMount(async () => {
    await import('$lib/three/garden.js');
    if (window.initGarden) window.initGarden({ positions, period });
  });

  onDestroy(() => {
    // garden.js exposes its teardown so SPA navigation doesn't leak the rAF loop.
    if (window.gardenTeardown) window.gardenTeardown();
  });
</script>

<div class="garden-canvas-root" id="garden-root"></div>

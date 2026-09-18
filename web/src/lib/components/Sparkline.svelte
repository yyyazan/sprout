<script>
  // Inline sparkline — one ink path, no axes, no fill. Takes a plain array of
  // values; color follows the row (gain/loss) through currentColor.
  let { values = [], width = 72, height = 22 } = $props();

  const d = $derived.by(() => {
    const v = (values ?? []).filter((x) => x != null);
    if (v.length < 2) return '';
    const lo = Math.min(...v), hi = Math.max(...v);
    const span = hi - lo || 1;
    const pad = 1.5; // keep the stroke inside the box at the extremes
    const sx = (width - pad * 2) / (v.length - 1);
    const sy = (height - pad * 2) / span;
    return v.map((y, i) => `${i ? 'L' : 'M'}${(pad + i * sx).toFixed(1)} ${(height - pad - (y - lo) * sy).toFixed(1)}`).join(' ');
  });
</script>

<svg class="spark" viewBox="0 0 {width} {height}" width={width} height={height} aria-hidden="true">
  <path {d} fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
</svg>

<style>
  .spark { display: block; flex: 0 0 auto; }
</style>

<script>
  // Toolbar dropdown for both charts: a system pill (text → outline on hover →
  // ink while open or active) over a bordered panel. The panel's rows use the
  // .cm-* classes below; children get { close }.
  import { onMount } from 'svelte';

  let { label, icon = null, count = 0, active = false, width = 150, children } = $props();

  let open = $state(false);
  let root;
  const close = () => (open = false);

  onMount(() => {
    // composedPath, not contains(): a picked row may already be unmounted by now
    const onDoc = (e) => { if (open && !e.composedPath().includes(root)) open = false; };
    window.addEventListener('click', onDoc);
    return () => window.removeEventListener('click', onDoc);
  });
</script>

<div class="cm" bind:this={root}>
  <button class="cm-btn" class:on={open || active} onclick={() => (open = !open)} aria-expanded={open}>
    {#if icon === 'line'}
      <svg class="cm-ic" viewBox="0 0 24 24" aria-hidden="true"><polyline points="3,16 9,10 14,14 21,6" /></svg>
    {:else if icon === 'compare'}
      <svg class="cm-ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h15M15 4l4 4-4 4M20 16H5M9 12l-4 4 4 4" /></svg>
    {:else if icon === 'indicators'}
      <svg class="cm-ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12c2.2-6 4.8-6 7 0s4.8 6 7 0c.9-2.4 2-3.7 4-4" /></svg>
    {/if}
    {label}
    {#if count}<span class="cm-count">{count}</span>{/if}
    <svg class="cm-cv" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
  </button>
  {#if open}
    <div class="cm-panel" style="min-width:{width}px">{@render children({ close })}</div>
  {/if}
</div>

<style>
  .cm { position: relative; flex: 0 0 auto; }
  .cm-btn { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--sans); font-size: var(--fs-body); font-weight: 600; color: var(--ink);
    padding: 5px 12px; background: transparent; border: var(--bw) solid transparent;
    border-radius: 999px; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .cm-btn:hover { border-color: var(--ink); }
  .cm-btn.on { background: var(--ink); border-color: var(--ink); color: var(--paper); }
  .cm-ic, .cm-cv { flex: 0 0 auto; fill: none; stroke: currentColor; stroke-width: 1.8;
    stroke-linecap: round; stroke-linejoin: round; }
  .cm-ic { width: 14px; height: 14px; }
  .cm-cv { width: 11px; height: 11px; margin-left: -1px; opacity: .7; }
  /* narrow chart (phone): the label carries the meaning, so the icon goes
     first — keeps menus + the right-side control on one line */
  @container chart (max-width: 440px) { .cm-ic { display: none; } }
  .cm-count { font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; line-height: 1;
    padding: 2px 6px; border-radius: 999px; background: var(--paper); color: var(--ink); border: 1px solid currentColor; }

  .cm-panel { position: absolute; top: calc(100% + 5px); left: 0; z-index: 20;
    display: flex; flex-direction: column; padding: 5px; gap: 1px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  /* rows: check column, label, optional muted symbol on the right */
  .cm-panel :global(.cm-item) { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; text-align: left;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink);
    padding: 7px 9px; border: 0; background: transparent; border-radius: 6px; }
  .cm-panel :global(.cm-item:hover) { background: var(--hover); }
  .cm-panel :global(.cm-item.sel) { font-weight: 600; }
  .cm-panel :global(.cm-check) { flex: 0 0 14px; font-size: 12px; color: var(--brand); }
  .cm-panel :global(.cm-name) { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .cm-panel :global(.cm-sym) { margin-left: auto; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .cm-panel :global(.cm-note) { padding: 7px 9px; font-size: var(--fs-body); color: var(--muted); }
</style>

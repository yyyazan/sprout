<script>
  // The shell both charts render into, so they can't drift apart again:
  // toolbar (menus · readout · right-side control) → compare chips → plot →
  // range tabs. The readout is the window's move, or the move from the window
  // start to the hovered bar; `read` = { pct, label, extra: { text, up } }.
  import { BRAND } from '$lib/chartTheme.js';
  import { fmtPct } from '$lib/chartKit.svelte.js';

  let {
    ranges, range = $bindable(), onrange = null,
    compares = $bindable([]), self = '',
    read = null, bare = false,
    tools, right = null, children,
  } = $props();
</script>

<div class="cf">
  <div class="cf-bar" class:cf-hide={bare}>
    {@render tools()}
    <div class="cf-read">
      {#if read}
        <span class="cf-v {read.pct == null ? '' : read.pct >= 0 ? 'up' : 'down'}">{fmtPct(read.pct)}</span>
        <span class="cf-k">{read.label}</span>
        {#if read.extra}<span class="cf-s {read.extra.up ? 'up' : 'down'}">{read.extra.text}</span>{/if}
      {/if}
    </div>
    {#if right}<div class="cf-right">{@render right()}</div>{/if}
  </div>

  <!-- active compares: legend chips, dot = series colour, click to remove -->
  {#if compares.length}
    <div class="cf-chips">
      <span class="cf-chip cf-chip-self"><span class="cf-dot" style="background:{BRAND}"></span>{self}</span>
      {#each compares as c (c.sym)}
        <button class="cf-chip" onclick={() => (compares = compares.filter((x) => x.sym !== c.sym))} title="Remove {c.sym}">
          <span class="cf-dot" style="background:{c.color}"></span>{c.sym}<span class="cf-x" aria-hidden="true">✕</span>
        </button>
      {/each}
    </div>
  {/if}

  <div class="cf-plot">{@render children()}</div>

  <div class="cf-ranges" class:cf-hide={bare} role="group" aria-label="range">
    {#each ranges as k}
      <button class:on={range === k} onclick={() => { range = k; onrange?.(k); }}>{k}</button>
    {/each}
  </div>
</div>

<style>
  .cf { height: 100%; min-width: 0; display: flex; flex-direction: column; gap: 10px;
    container: chart / inline-size; }
  /* empty portfolio: keep the layout, hide controls with nothing to act on */
  .cf-hide { visibility: hidden; }

  .cf-bar { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }
  /* readout: 18/600 figure leads, muted label, one secondary figure. Takes the
     toolbar's middle so nothing shifts as it changes. */
  .cf-read { flex: 1 1 auto; min-width: 0; display: flex; align-items: baseline; gap: 8px; padding-left: 6px;
    font-family: var(--num); font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; }
  .cf-v { font-size: 18px; font-weight: 600; line-height: 1; letter-spacing: -.01em; }
  .cf-k { font-family: var(--sans); font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .cf-s { font-size: var(--fs-body); font-weight: 500; }
  .cf-right { flex: 0 0 auto; display: inline-flex; margin-left: auto; }

  .cf-chips { flex: 0 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .cf-chip { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; color: var(--ink);
    padding: 3px 9px; background: transparent; border: var(--bw) solid var(--hairline); border-radius: 999px; }
  .cf-chip:hover { border-color: var(--ink); }
  .cf-chip-self { cursor: default; color: var(--muted); }
  .cf-chip-self:hover { border-color: var(--hairline); }
  .cf-dot { width: 8px; height: 8px; border-radius: 50%; border: 1px solid var(--ink); flex: 0 0 auto; }
  .cf-x { font-size: 9px; opacity: .6; }

  .cf-plot { flex: 1 1 auto; min-height: 0; position: relative; }

  /* range tabs — system pill states; no rule above them, the gap separates.
     11 pills won't fit a phone, so the row scrolls sideways without a bar. */
  .cf-ranges { flex: 0 0 auto; display: flex; align-items: center; gap: 2px; padding-top: 4px;
    overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
  .cf-ranges::-webkit-scrollbar { display: none; }
  .cf-ranges button { flex: 0 0 auto; font-family: var(--num); font-size: 11.5px; font-weight: 600; cursor: pointer;
    color: var(--muted); font-variant-numeric: tabular-nums;
    padding: 4px 11px; background: transparent; border: var(--bw) solid transparent; border-radius: 999px;
    transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .cf-ranges button:hover { color: var(--ink); border-color: var(--ink); }
  .cf-ranges button.on { color: var(--paper); background: var(--ink); border-color: var(--ink); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  /* too narrow for menus + readout + a hovered date on one line (the 3-column
     dashboard stage, the phone): the readout takes its own line under the
     menus. A container query, so both charts wrap at the same width. */
  @container chart (max-width: 720px) {
    .cf-bar { flex-wrap: wrap; row-gap: 8px; }
    .cf-read { flex-basis: 100%; order: 1; padding-left: 2px; }
  }
  @media (max-width: 700px) {
    .cf-ranges button { padding-inline: 9px; }
  }
</style>

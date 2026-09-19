<script>
  import { untrack } from 'svelte';
  import { openStock, cardToHolding } from '$lib/stores.js';
  // debug → full-viewport inspect mode (OrbitControls + grid/axes + editor),
  // used by the /garden page. Omitted on the dashboard band (idle-sway orbit).
  // interactive=false → ambient only (no hover/click/drag); fill → take the
  // host's full height instead of the dashboard band height; bare → plants
  // only on a transparent canvas (no sky/ground), so the host's bg shows;
  // slots → a custom [{x,z,rot}] arrangement in place of the bed's PLANT_SLOTS.
  let { positions, period, debug = false, interactive = true, fill = false, bare = false, slots = null } = $props();

  // Hover/tap state, fed by the pick layer's onHover callback. Shape:
  // { card, x, y, above } | null. Cleared (null) on leave / tap-away / teardown.
  let hover = $state(null);

  // pick.js → here: track the hovered plant; open its detail on click/tap.
  function onHover(p) { hover = p; }
  function onPick(card) {
    openStock({ ticker: card.ticker, name: card.company_name, holding: cardToHolding(card) });
  }

  // One effect owns the garden's lifetime: it builds after mount, rebuilds when
  // the host swaps `slots` (the sign-in screen does this at its breakpoint), and
  // tears down on unmount. Only `slots` is tracked — positions/period are read
  // untracked so the dashboard's periodic data refresh never rebuilds the scene.
  // Dynamic import keeps three.js out of the initial bundle and browser-only.
  $effect(() => {
    const s = slots;
    let cancelled = false;
    let teardown;
    import('$lib/three/garden/index.js').then(({ initGarden }) => {
      if (cancelled) return;
      teardown = initGarden(
        untrack(() => ({ positions, period, slots: s })),
        untrack(() => ({ debug, interactive, bare, onHover, onPick }))
      );
    });
    return () => { cancelled = true; teardown?.(); };
  });
</script>

<div class="garden-canvas-root" class:garden-canvas-root--fill={debug || fill} id="garden-root">
  {#if hover}
    {@const c = hover.card}
    {@const d = c.day_pct == null ? null : +c.day_pct}
    <div
      class="g-tip"
      class:pos={d != null && d >= 0}
      class:neg={d != null && d < 0}
      class:below={!hover.above}
      style="left:{hover.x}px; top:{hover.y}px"
    >
      <span class="g-tip-ticker">{c.ticker}</span>
      <span class="g-tip-alloc">{(+c.position_pct).toFixed(1)}% of book</span>
      <span class="g-tip-mom">
        {#if d == null}—{:else}{d >= 0 ? '▲' : '▼'} {Math.abs(d).toFixed(2)}% today{/if}
      </span>
    </div>
  {/if}
</div>

<style>
  /* Tooltip mirrors the chart .sc-tip / .ts-tooltip patterns + design tokens. */
  .g-tip {
    position: absolute;
    z-index: 3;
    pointer-events: none;
    white-space: nowrap;
    transform: translate(-50%, calc(-100% - 14px));
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    padding: 6px 9px;
    background: var(--surface);
    color: var(--text);
    border: var(--bw) solid var(--ink);
    border-radius: var(--r);
    box-shadow: var(--sh-pop);
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
  }
  .g-tip.below { transform: translate(-50%, 14px); }
  .g-tip-ticker { font-family: var(--sans); font-weight: 700; font-size: 12px; }
  .g-tip-alloc { font-size: 11px; color: var(--muted); }
  .g-tip-mom { font-size: 10px; color: var(--muted); }
  .g-tip.pos .g-tip-mom { color: var(--gain); }
  .g-tip.neg .g-tip-mom { color: var(--loss); }
</style>

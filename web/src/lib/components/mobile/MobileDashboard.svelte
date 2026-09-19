<script>
  // Phone dashboard shell: three always-mounted panes (Home, Holdings, Log) in
  // one horizontal track, live-dragged like a native page view, plus the fixed
  // bottom tab bar and the full-screen stock sheet. Takes over the data wiring
  // the desktop Sidebar normally does (momentum poll + watchlist), since the
  // sidebar isn't mounted on mobile.
  import { onMount } from 'svelte';
  import { startMomentum, loadWatchlist, detail } from '$lib/stores.js';
  import MobileTabBar from './MobileTabBar.svelte';
  import MobileHome from './MobileHome.svelte';
  import MobileHoldings from './MobileHoldings.svelte';
  import MobileLog from './MobileLog.svelte';
  import MobileStockSheet from './MobileStockSheet.svelte';

  let { d, garden, refresh } = $props();

  const TAB_ORDER = ['home', 'holdings', 'log'];
  let tab = $state('home');
  onMount(() => { startMomentum(); loadWatchlist(); });

  const idx = $derived(TAB_ORDER.indexOf(tab));

  // ── live-tracking pager ──────────────────────────────────────────────
  // The three panes sit side by side in one flex row (300% wide, each pane a
  // third). At rest the track sits at -idx*(100/3)% so only one column shows;
  // a drag adds a live pixel offset on top of that base position, so content
  // follows the finger 1:1 instead of only reacting once you let go. A tap on
  // the dock just changes `tab` — the same CSS transition on the base
  // position slides the track over, so a tap and a released drag both settle
  // through the one mechanism. Each pane scrolls internally (own overflow),
  // which is also what makes side-by-side layout possible without one long
  // pane's height leaking into the other two.
  const SWIPE_MIN = 60;
  const EDGE_RESIST = 0.35;   // rubber-band past the first/last tab
  const AXIS_SLOP = 8;        // px of travel before an axis (h vs v) is picked
  // Only a touch starting on something with its OWN horizontal drag is left
  // alone entirely: the lightweight-charts canvas (hold-and-drag scrub) and
  // the garden canvas (drag-to-orbit on touch, see three/garden/layers/
  // interaction.js) — both are <canvas>. Buttons/links/badges are click-only
  // so they stay draggable; excluding them made swipe nearly dead on
  // Holdings, whose rows span most of the pane.
  const NO_SWIPE = 'canvas, input, textarea, [contenteditable="true"]';

  let dragging = $state(false);
  let dragDX = $state(0);
  let startX = null, startY = null, axis = null;
  let trackEl;

  // Svelte's ontouchmove attribute registers passively, so preventDefault()
  // inside it is silently ignored — attach this one by hand, non-passive.
  onMount(() => {
    trackEl.addEventListener('touchmove', onTouchMove, { passive: false });
    return () => trackEl.removeEventListener('touchmove', onTouchMove);
  });

  function onTouchStart(e) {
    if (e.touches.length !== 1 || $detail || e.touches[0].target.closest?.(NO_SWIPE)) {
      startX = null;
      return;
    }
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    axis = null;
  }
  function onTouchMove(e) {
    if (startX == null) return;
    const t = e.touches[0];
    const dx = t.clientX - startX, dy = t.clientY - startY;
    if (axis == null) {
      if (Math.hypot(dx, dy) < AXIS_SLOP) return;
      axis = Math.abs(dx) > Math.abs(dy) * 1.3 ? 'x' : 'y';
      if (axis === 'x') dragging = true;
    }
    if (axis !== 'x') return;
    e.preventDefault(); // once we're paging, a stray dy shouldn't also scroll
    dragDX = (idx === 0 && dx > 0) || (idx === TAB_ORDER.length - 1 && dx < 0) ? dx * EDGE_RESIST : dx;
  }
  function reset() {
    dragging = false;
    dragDX = 0;
    startX = null;
    axis = null;
  }
  function onTouchEnd() {
    if (dragging && Math.abs(dragDX) > SWIPE_MIN) {
      if (dragDX < 0 && idx < TAB_ORDER.length - 1) tab = TAB_ORDER[idx + 1];
      else if (dragDX > 0 && idx > 0) tab = TAB_ORDER[idx - 1];
    }
    reset();
  }
</script>

<div class="m-shell">
  <div class="m-track" class:dragging bind:this={trackEl}
    style="transform: translateX(calc({(-idx * 100) / 3}% + {dragDX}px))"
    ontouchstart={onTouchStart} ontouchend={onTouchEnd} ontouchcancel={reset}>
    <div class="m-pane"><MobileHome {d} {garden} onSeeAll={() => (tab = 'holdings')} /></div>
    <div class="m-pane"><MobileHoldings /></div>
    <div class="m-pane"><MobileLog {d} {refresh} /></div>
  </div>
</div>

<MobileTabBar bind:tab />

{#if $detail}
  <MobileStockSheet />
{/if}

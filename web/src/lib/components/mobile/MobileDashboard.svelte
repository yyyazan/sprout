<script>
  // Phone dashboard shell: three always-mounted panes (Home, Holdings, Log)
  // toggled by display so the three.js garden and the charts never re-init
  // on tab bounces, plus the fixed bottom tab bar and the full-screen stock
  // sheet. Takes over the data wiring the desktop Sidebar normally does
  // (momentum poll + watchlist), since the sidebar isn't mounted on mobile.
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

  // pane wrappers, keyed like TAB_ORDER — used only to replay the enter
  // animation below; the mounted panes inside are never touched.
  let paneEls = {};
  let prevIdx = 0;

  // fresh tab, fresh scroll — panes share the page scroll position otherwise.
  // iOS can't transition a display:none → display:block flip, so a plain tab
  // switch just jumps; this replays a small directional slide-in on whichever
  // pane just became visible instead. Toggling the class on the wrapper (not
  // the pane component) means the garden/charts inside are never re-mounted.
  $effect(() => {
    const i = TAB_ORDER.indexOf(tab);
    const dir = i === prevIdx ? null : i > prevIdx ? 'right' : 'left';
    prevIdx = i;
    window.scrollTo(0, 0);
    const el = paneEls[tab];
    if (!dir || !el) return;
    el.classList.remove('enter-left', 'enter-right');
    void el.offsetWidth; // force a reflow so the animation replays
    el.classList.add(dir === 'right' ? 'enter-right' : 'enter-left');
  });

  // swipe left/right anywhere in a pane to move a tab over — same three-stop
  // order as the dock. Decided on touchend from the net delta so an ordinary
  // vertical scroll (even a diagonal one) never gets mistaken for a swipe.
  // Only a touch that starts on something with its OWN horizontal drag is
  // left alone: the lightweight-charts canvas (hold-and-drag scrub) and the
  // garden's (drag-to-orbit on touch, see interaction.js) — both are <canvas>.
  // Ordinary buttons/links/badges are click-only, so they stay swipeable —
  // holdings rows span most of the Holdings pane, and excluding buttons
  // outright made swipe nearly dead there. Text inputs keep their own
  // selection-drag untouched too.
  const SWIPE_MIN = 60;
  const NO_SWIPE = 'canvas, input, textarea, [contenteditable="true"]';
  let touchX = 0, touchY = 0, touching = false;
  function onTouchStart(e) {
    if (e.touches.length !== 1 || $detail || e.target.closest?.(NO_SWIPE)) { touching = false; return; }
    touching = true;
    touchX = e.touches[0].clientX;
    touchY = e.touches[0].clientY;
  }
  function onTouchEnd(e) {
    if (!touching) return;
    touching = false;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchX, dy = t.clientY - touchY;
    if (Math.abs(dx) < SWIPE_MIN || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    const i = TAB_ORDER.indexOf(tab);
    if (dx < 0 && i < TAB_ORDER.length - 1) tab = TAB_ORDER[i + 1];
    else if (dx > 0 && i > 0) tab = TAB_ORDER[i - 1];
  }
</script>

<div class="m-shell" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
  <div class="m-pane" class:hidden={tab !== 'home'} bind:this={paneEls.home}><MobileHome {d} {garden} onSeeAll={() => (tab = 'holdings')} /></div>
  <div class="m-pane" class:hidden={tab !== 'holdings'} bind:this={paneEls.holdings}><MobileHoldings /></div>
  <div class="m-pane" class:hidden={tab !== 'log'} bind:this={paneEls.log}><MobileLog {d} {refresh} /></div>
</div>

<MobileTabBar bind:tab />

{#if $detail}
  <MobileStockSheet />
{/if}

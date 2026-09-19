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

  let tab = $state('home');
  onMount(() => { startMomentum(); loadWatchlist(); });

  // fresh tab, fresh scroll — panes share the page scroll position otherwise
  $effect(() => { tab; window.scrollTo(0, 0); });

  // swipe left/right anywhere in a pane to move a tab over — same three-stop
  // order as the dock. Decided on touchend from the net delta so an ordinary
  // vertical scroll (even a diagonal one) never gets mistaken for a swipe.
  const TAB_ORDER = ['home', 'holdings', 'log'];
  const SWIPE_MIN = 60;
  let touchX = 0, touchY = 0, touching = false;
  function onTouchStart(e) {
    if (e.touches.length !== 1 || $detail) return;
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
  <div class="m-pane" class:hidden={tab !== 'home'}><MobileHome {d} {garden} onSeeAll={() => (tab = 'holdings')} /></div>
  <div class="m-pane" class:hidden={tab !== 'holdings'}><MobileHoldings /></div>
  <div class="m-pane" class:hidden={tab !== 'log'}><MobileLog {d} {refresh} /></div>
</div>

<MobileTabBar bind:tab />

{#if $detail}
  <MobileStockSheet />
{/if}

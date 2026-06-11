<script>
  // Phone dashboard shell: four always-mounted panes (Home · Search · Holdings ·
  // Log) toggled by display so the three.js garden and the charts never re-init
  // on tab bounces, plus the fixed bottom tab bar and the full-screen stock
  // sheet. Takes over the data wiring the desktop Sidebar normally does
  // (momentum poll + watchlist), since the sidebar isn't mounted on mobile.
  import { onMount } from 'svelte';
  import { startMomentum, loadWatchlist, detail } from '$lib/stores.js';
  import MobileTabBar from './MobileTabBar.svelte';
  import MobileHome from './MobileHome.svelte';
  import MobileSearch from './MobileSearch.svelte';
  import MobileHoldings from './MobileHoldings.svelte';
  import MobileLog from './MobileLog.svelte';
  import MobileStockSheet from './MobileStockSheet.svelte';

  let { d, garden, refresh } = $props();

  let tab = $state('home');
  onMount(() => { startMomentum(); loadWatchlist(); });

  // fresh tab, fresh scroll — panes share the page scroll position otherwise
  $effect(() => { tab; window.scrollTo(0, 0); });
</script>

<div class="m-shell">
  <div class="m-pane" class:hidden={tab !== 'home'}><MobileHome {d} {garden} /></div>
  <div class="m-pane" class:hidden={tab !== 'search'}><MobileSearch /></div>
  <div class="m-pane" class:hidden={tab !== 'holdings'}><MobileHoldings /></div>
  <div class="m-pane" class:hidden={tab !== 'log'}><MobileLog {d} {refresh} /></div>
</div>

<MobileTabBar bind:tab />

{#if $detail}
  <MobileStockSheet />
{/if}

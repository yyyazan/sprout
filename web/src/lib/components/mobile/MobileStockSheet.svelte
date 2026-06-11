<script>
  // Full-screen stock sheet for the phone — renders the same StockPanel widget
  // grid the desktop uses, above the tab bar. One history entry is pushed per
  // sheet session so the iOS back-swipe dismisses the sheet instead of leaving
  // the app; opening a related stock swaps content without stacking entries.
  import StockPanel from '../StockPanel.svelte';
  import { detail, closeStock } from '$lib/stores.js';
  import { pushState } from '$app/navigation';

  let pushed = false;

  $effect(() => {
    if ($detail && !pushed) {
      pushed = true;
      pushState('', { mobileSheet: true });   // SvelteKit-aware shallow push
    }
  });

  $effect(() => {
    const onPop = () => {
      if (pushed) { pushed = false; closeStock(); }
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  });

  // lock the page behind the sheet while it's up
  $effect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  });

  // ✕ / esc route through history so the pushed entry is consumed
  function close() {
    if (pushed) history.back();
    else closeStock();
  }
</script>

<div class="m-sheet" role="dialog" aria-modal="true" aria-label="{$detail?.ticker} stock view">
  <div class="m-sheet-bar">
    <span class="m-sheet-crumb">{$detail?.ticker}</span>
    <button class="btn btn-sm btn-line" onclick={close}>✕ close</button>
  </div>
  <div class="m-sheet-body">
    {#key $detail?.ticker}
      <StockPanel ticker={$detail.ticker} name={$detail.name} holding={$detail.holding}
        onClose={close} glyph="✕" />
    {/key}
  </div>
</div>

<style>
  .m-sheet { position: fixed; inset: 0; z-index: 200; background: var(--bg);
    overflow-y: auto; -webkit-overflow-scrolling: touch; overscroll-behavior: contain;
    padding: 0 14px calc(24px + env(safe-area-inset-bottom));
    animation: m-sheet-in .18s ease; }
  @keyframes m-sheet-in { from { opacity: 0; transform: translateY(28px); } to { opacity: 1; transform: none; } }

  .m-sheet-bar { position: sticky; top: 0; z-index: 5; display: flex; align-items: center;
    justify-content: space-between; gap: 12px; background: var(--bg); margin: 0 -14px 10px;
    padding: calc(10px + env(safe-area-inset-top)) 14px 10px;
    border-bottom: var(--bw) solid var(--hairline); }
  .m-sheet-crumb { font-family: var(--mono); font-size: 13px; font-weight: 700; letter-spacing: .04em; }

  .m-sheet-body { min-height: 0; }
  /* the sheet bar already carries close — StockPanel's own pill would sit
     redundantly right under it */
  .m-sheet-body :global(.hw-back) { display: none; }

  @media (prefers-reduced-motion: reduce) { .m-sheet { animation: none; } }
</style>

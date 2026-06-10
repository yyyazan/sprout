<script>
  // Full-screen modal shell for the stock view — used on routes that don't have
  // an inline stage (the dashboard renders StockPanel inside its main widget).
  import StockPanel from './StockPanel.svelte';

  let { ticker, name = null, holding = null, onClose } = $props();
</script>

<div class="sd-scrim" role="presentation" onclick={() => onClose?.()}>
  <div class="sd" role="dialog" aria-modal="true" aria-label="{ticker} detail" onclick={(e) => e.stopPropagation()}>
    <StockPanel {ticker} {name} {holding} {onClose} glyph="✕" />
  </div>
</div>

<style>
  .sd-scrim { position: fixed; inset: 0; z-index: 200; display: grid; place-items: center; padding: 28px;
    background: rgba(0, 0, 0, .62); backdrop-filter: blur(3px);
    animation: sd-fade .16s ease; }
  @keyframes sd-fade { from { opacity: 0; } to { opacity: 1; } }
  /* paper sheet — the widget grid floats on it like the dashboard */
  .sd { width: min(1180px, 95vw); height: min(820px, 92vh); display: block;
    background: var(--paper); border: var(--bw) solid var(--ink); border-radius: calc(var(--r) + 4px);
    box-shadow: 8px 8px 0 var(--ink); box-sizing: border-box; overflow-y: auto; padding: 18px;
    animation: sd-rise .2s cubic-bezier(.34, 1.4, .5, 1); }
  @keyframes sd-rise { from { transform: translateY(14px) scale(.985); opacity: 0; } to { transform: none; opacity: 1; } }

  @media (max-width: 900px) {
    .sd { height: auto; max-height: 92vh; overflow: auto; }
  }
</style>

<script>
  // iOS-style bottom tab bar for the phone dashboard. Fixed to the viewport
  // bottom, padded for the home indicator (safe-area). Active tab = solid ink
  // inversion, same state language as .nav-link.active.
  let { tab = $bindable('home') } = $props();

  const TABS = [
    { key: 'home', glyph: '❖', label: 'home' },
    { key: 'search', glyph: '⌕', label: 'search' },
    { key: 'holdings', glyph: '☰', label: 'holdings' },
    { key: 'log', glyph: '⊞', label: 'log' },
  ];
</script>

<nav class="m-tabbar" aria-label="dashboard sections">
  {#each TABS as t (t.key)}
    <button class="m-tab" class:on={tab === t.key} onclick={() => (tab = t.key)}
      aria-current={tab === t.key ? 'page' : undefined}>
      <span class="m-tab-glyph" aria-hidden="true">{t.glyph}</span>
      <span class="m-tab-label">{t.label}</span>
    </button>
  {/each}
</nav>

<style>
  .m-tabbar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 100;
    display: grid; grid-template-columns: repeat(4, 1fr);
    background: var(--paper); border-top: var(--bw) solid var(--ink);
    padding-bottom: env(safe-area-inset-bottom); }
  .m-tab { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
    height: 54px; padding: 0; border: 0; background: transparent; cursor: pointer;
    color: var(--muted); font: inherit;
    transition: background .12s ease, color .12s ease; }
  .m-tab-glyph { font-size: 17px; line-height: 1; }
  .m-tab-label { font-family: var(--sans); font-size: 9px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; }
  .m-tab.on { background: var(--ink); color: var(--paper); }
  @media (prefers-reduced-motion: reduce) { .m-tab { transition: none; } }
</style>

<script>
  // Floating dock — iOS stock-dock geometry (64px inset capsule, glass blur,
  // near-full-height active bubble) in the neo-brutalist language: 1px ink
  // border, solid-ink pill, paper text, mono labels.
  //
  // Interactions:
  //  · tap a tab — pill slides over on a hard spring (overshoot, no blur-morph)
  //  · HOLD + SLIDE anywhere on the dock — the pill rides the finger 1:1
  //    (no easing while live, brutalist-direct), the tab under it activates in
  //    real time, and on release the pill snaps onto the column.
  let { tab = $bindable('home') } = $props();

  const TABS = [
    { key: 'home', glyph: '❖', label: 'home' },
    { key: 'search', glyph: '⌕', label: 'search' },
    { key: 'holdings', glyph: '☰', label: 'holdings' },
    { key: 'log', glyph: '⊞', label: 'log' },
  ];
  const idx = $derived(Math.max(0, TABS.findIndex((t) => t.key === tab)));

  const PAD = 4;            // capsule inner padding = pill inset
  const SLOP = 6;           // px of travel before a press becomes a slide

  let navEl;
  let pressed = false;
  let pressX = 0;
  let dragging = $state(false);
  let dragX = $state(0);    // pill offset in px while sliding

  function slideTo(clientX) {
    const r = navEl.getBoundingClientRect();
    const inner = r.width - PAD * 2;
    const col = inner / TABS.length;
    dragX = Math.min(Math.max(clientX - r.left - PAD - col / 2, 0), inner - col);
    // live activation: the tab under the pill switches as you slide
    const i = Math.min(TABS.length - 1, Math.max(0, Math.round(dragX / col)));
    if (TABS[i].key !== tab) tab = TABS[i].key;
  }

  function onDown(e) {
    pressed = true;
    pressX = e.clientX;
    navEl.setPointerCapture?.(e.pointerId);
  }
  function onMove(e) {
    if (!pressed) return;
    if (!dragging && Math.abs(e.clientX - pressX) < SLOP) return;
    dragging = true;
    slideTo(e.clientX);
  }
  function onUp() {
    pressed = false;
    dragging = false;   // pill snaps from dragX onto the column (spring)
  }
</script>

<nav class="m-dock" aria-label="dashboard sections" bind:this={navEl}
  onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} onpointercancel={onUp}>
  <!-- active bubble: column-snapped at rest, finger-locked while sliding -->
  <span class="m-dock-pill" class:live={dragging} aria-hidden="true"
    style={dragging ? `transform: translateX(${dragX}px) scale(1.04)` : `transform: translateX(${idx * 100}%)`}></span>
  {#each TABS as t (t.key)}
    <button class="m-tab" class:on={tab === t.key} onclick={() => (tab = t.key)}
      aria-current={tab === t.key ? 'page' : undefined}>
      <span class="m-tab-glyph" aria-hidden="true">{t.glyph}</span>
      <span class="m-tab-label">{t.label}</span>
    </button>
  {/each}
</nav>

<style>
  /* iOS stock dock dimensions: 64px capsule, 16px side insets, 12px above the
     home indicator, pill inset 4px (near-full-height bubble). */
  .m-dock { position: fixed; left: 16px; right: 16px; bottom: calc(12px + env(safe-area-inset-bottom));
    z-index: 100; box-sizing: border-box; height: 64px; padding: 4px;
    display: grid; grid-template-columns: repeat(4, 1fr); align-items: stretch;
    /* iOS glass under a brutalist ink line: translucent paper + blur, 1px border */
    background: color-mix(in srgb, var(--paper) 72%, transparent);
    -webkit-backdrop-filter: blur(16px) saturate(1.4);
    backdrop-filter: blur(16px) saturate(1.4);
    border: var(--bw) solid var(--ink); border-radius: 999px;
    /* the dock owns its gestures — no page scroll / back-swipe from here */
    touch-action: none; -webkit-user-select: none; user-select: none; }

  .m-dock-pill { position: absolute; top: 4px; bottom: 4px; left: 4px;
    width: calc((100% - 8px) / 4);
    background: var(--ink); border-radius: 999px;
    transition: transform .38s cubic-bezier(.34, 1.56, .5, 1); }
  /* live slide: zero easing — the pill is bolted to the finger */
  .m-dock-pill.live { transition: none; }

  .m-tab { position: relative; z-index: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 3px;
    padding: 0; border: 0; background: transparent; cursor: pointer;
    color: var(--muted); font: inherit; -webkit-user-select: none; user-select: none;
    -webkit-touch-callout: none;
    transition: color .18s ease, transform .12s ease; }
  .m-tab:active { transform: scale(.94); }
  .m-tab.on { color: var(--paper); }

  .m-tab-glyph { font-size: 20px; line-height: 1; }
  .m-tab.on .m-tab-glyph { animation: m-dock-pop .38s cubic-bezier(.34, 1.56, .5, 1); }
  @keyframes m-dock-pop {
    0% { transform: scale(1); }
    45% { transform: scale(1.22) translateY(-1.5px); }
    100% { transform: scale(1); }
  }

  .m-tab-label { font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; }

  @media (prefers-reduced-motion: reduce) {
    .m-dock-pill, .m-tab { transition: none; }
    .m-tab.on .m-tab-glyph { animation: none; }
  }
</style>

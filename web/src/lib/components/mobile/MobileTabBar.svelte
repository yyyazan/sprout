<script>
  // Floating dock — three .btn-shaped tabs in a bordered capsule. Same button
  // system as everywhere else: idle = muted text, on = solid ink with paper
  // text. Icon and label sit on one line at the .btn cut (13/600). Solid
  // surface, ink hairline, no glass.
  //
  // Interactions:
  //  · tap a tab — the ink pill slides over on a spring
  //  · HOLD + SLIDE anywhere on the dock — the pill rides the finger 1:1, the
  //    tab under it activates in real time, and on release it snaps to the column
  let { tab = $bindable('home') } = $props();

  // three sections; search lives in the Home strip, not the dock
  const TABS = [
    { key: 'home', label: 'Home' },
    { key: 'holdings', label: 'Holdings' },
    { key: 'log', label: 'Log' },
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
    style={dragging ? `transform: translateX(${dragX}px)` : `transform: translateX(${idx * 100}%)`}></span>
  {#each TABS as t (t.key)}
    <button class="m-tab" class:on={tab === t.key} onclick={() => (tab = t.key)}
      aria-current={tab === t.key ? 'page' : undefined}>
      <!-- one 24-box, 1.8 stroke, currentColor — inverts to paper when active -->
      {#if t.key === 'home'}
        <!-- sprout: stem + two leaves -->
        <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 21 V11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          <path d="M12 13 C 8.5 13, 6 10.8, 5.6 6.8 C 9.6 7, 11.7 9.4, 12 13 Z" fill="currentColor" />
          <path d="M12 11 C 15.5 11, 18 8.8, 18.4 4.8 C 14.4 5, 12.3 7.4, 12 11 Z" fill="currentColor" />
        </svg>
      {:else if t.key === 'holdings'}
        <!-- three bars of different height: an allocation -->
        <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
          stroke-width="1.8" stroke-linecap="round">
          <path d="M5 20 V13" /><path d="M12 20 V5" /><path d="M19 20 V9" />
        </svg>
      {:else}
        <!-- a list: three rules, each with its bullet -->
        <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
          stroke-width="1.8" stroke-linecap="round">
          <path d="M5 7 h.01" /><path d="M10 7 h9" />
          <path d="M5 12 h.01" /><path d="M10 12 h9" />
          <path d="M5 17 h.01" /><path d="M10 17 h9" />
        </svg>
      {/if}
      <span>{t.label}</span>
    </button>
  {/each}
</nav>

<style>
  /* capsule: 16px side margins (iOS content margin), floats 8px above the home
     indicator; 52px tall so the 44px pill inside clears Apple's minimum target */
  .m-dock { position: fixed; left: 16px; right: 16px; bottom: calc(8px + env(safe-area-inset-bottom));
    z-index: 100; box-sizing: border-box; height: 52px; padding: 3px;
    display: grid; grid-template-columns: repeat(3, 1fr); align-items: stretch;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: 999px;
    box-shadow: var(--sh);
    /* the dock owns its gestures — no page scroll / back-swipe from here */
    touch-action: none; -webkit-user-select: none; user-select: none; }

  /* the .btn.on state as a sliding element */
  .m-dock-pill { position: absolute; top: 3px; bottom: 3px; left: 3px;
    width: calc((100% - 6px) / 3);
    background: var(--ink); border-radius: 999px;
    transition: transform .32s cubic-bezier(.34, 1.4, .5, 1); }
  /* live slide: zero easing — the pill is bolted to the finger */
  .m-dock-pill.live { transition: none; }

  /* a .btn without the border: the capsule is the border, the pill is the state */
  .m-tab { position: relative; z-index: 1; display: inline-flex; align-items: center; justify-content: center; gap: 7px;
    padding: 0; border: 0; border-radius: 999px; background: transparent; cursor: pointer;
    color: var(--muted); font-family: var(--sans); font-size: 13px; font-weight: 600; line-height: 1.2;
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none;
    transition: color .18s ease; }
  .m-tab.on { color: var(--paper); }

  .m-tab-glyph { width: 18px; height: 18px; display: block; }

  @media (prefers-reduced-motion: reduce) {
    .m-dock-pill, .m-tab { transition: none; }
  }
</style>

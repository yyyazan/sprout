<script>
  // Bottom tab bar — borderless, flush to the screen edge (no floating capsule,
  // no side margins), icon stacked over label. The active tab gets a small
  // ink pill hugging just its icon (not the whole column) that slides between
  // tabs; sizing it in px (not the old 100%/3 trick) means the bar's own
  // width has to be measured, so a ResizeObserver keeps it live across rotation.
  //
  // Interactions (unchanged from the old capsule):
  //  · tap a tab — the pill slides over on a spring
  //  · HOLD + SLIDE anywhere on the bar — the pill rides the finger 1:1, the
  //    tab under it activates in real time, and on release it snaps to the column
  import { onMount } from 'svelte';
  let { tab = $bindable('home') } = $props();

  const TABS = [
    { key: 'home', label: 'Home' },
    { key: 'holdings', label: 'Holdings' },
    { key: 'log', label: 'Log' },
  ];

  const PILL_W = 52;        // fixed — hugs the icon, not the column
  const PILL_H = 30;
  const SLOP = 6;            // px of travel before a press becomes a slide

  let navEl;
  let navW = $state(0);
  onMount(() => {
    const measure = () => { navW = navEl?.getBoundingClientRect().width ?? 0; };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(navEl);
    return () => ro.disconnect();
  });

  const idx = $derived(Math.max(0, TABS.findIndex((t) => t.key === tab)));
  const colW = $derived(navW / TABS.length);
  const restX = $derived(idx * colW + (colW - PILL_W) / 2);

  let pressed = false;
  let pressX = 0;
  let dragging = $state(false);
  let dragX = $state(0);

  // setPointerCapture on the nav (below) redirects the compat click event to
  // the nav too, so a plain tap never reaches the button's own onclick — tab
  // switching has to be decided here, from the pointer's own x, for both a
  // still tap (onUp) and a drag crossing a column (onMove). onclick stays on
  // the button only for keyboard activation, which never touches capture.
  function tabAt(clientX) {
    const r = navEl.getBoundingClientRect();
    const col = r.width / TABS.length;
    const i = Math.min(TABS.length - 1, Math.max(0, Math.floor((clientX - r.left) / col)));
    return TABS[i].key;
  }
  function slideTo(clientX) {
    const r = navEl.getBoundingClientRect();
    dragX = Math.min(Math.max(clientX - r.left - PILL_W / 2, 0), r.width - PILL_W);
    const t = tabAt(clientX);
    if (t !== tab) tab = t;
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
  function onUp(e) {
    if (pressed && !dragging) tab = tabAt(e.clientX);
    pressed = false;
    dragging = false;   // pill snaps from dragX onto the column (spring)
  }
  function onCancel() {
    // interrupted (e.g. scroll took over) — reset without picking a tab
    pressed = false;
    dragging = false;
  }
</script>

<nav class="m-dock" aria-label="dashboard sections" bind:this={navEl}
  onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} onpointercancel={onCancel}>
  <span class="m-dock-pill" class:live={dragging} aria-hidden="true"
    style="transform: translateX({dragging ? dragX : restX}px)">
    <!-- a fresh element per idx replays the pop keyframe below — remounting
         beats a manual class + timeout for "run once on change" -->
    {#key idx}
      <span class="m-dock-pill-fill"></span>
    {/key}
  </span>
  {#each TABS as t (t.key)}
    <button class="m-tab" class:on={tab === t.key} onclick={() => (tab = t.key)}
      aria-current={tab === t.key ? 'page' : undefined}>
      <span class="m-tab-ico">
        {#if t.key === 'home'}
          <!-- house -->
          <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 11 12 4 20 11 V19 A2 2 0 0 1 18 21 H6 A2 2 0 0 1 4 19 Z" />
            <path d="M9.5 21 V14 H14.5 V21" />
          </svg>
        {:else if t.key === 'holdings'}
          <!-- pie chart: the ring's own vocabulary, one size down -->
          <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
            <path d="M22 12A10 10 0 0 0 12 2v10Z" />
          </svg>
        {:else}
          <!-- swap: buy/sell arrows — the same shape the trade tiles use -->
          <svg class="m-tab-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 18 V6 M4.5 9.5 8 6 11.5 9.5" />
            <path d="M16 6 V18 M12.5 14.5 16 18 19.5 14.5" />
          </svg>
        {/if}
      </span>
      <span class="m-tab-label">{t.label}</span>
    </button>
  {/each}
</nav>

<style>
  /* full-bleed, flush to the bottom edge — no side margins, no gap, no border
     box; a hairline top edge is the only separation from scrolled content */
  .m-dock { position: fixed; left: 0; right: 0; bottom: 0; z-index: 100;
    display: flex; height: 56px; padding-bottom: env(safe-area-inset-bottom);
    background: var(--surface); border-top: var(--bw) solid var(--hairline);
    /* the dock owns its gestures — no page scroll / back-swipe from here */
    touch-action: none; -webkit-user-select: none; user-select: none; }

  /* the tight pill: sized to the icon alone, not the column. A quiet ink
     wash, not a solid block — the same --hover-strength language the rest of
     the app uses for "something is selected here", just permanent instead of
     on press. The fill is a separate absolutely-positioned child so its own
     pop keyframe (below) never fights this element's translateX transition. */
  .m-dock-pill { position: absolute; top: 6px; left: 0; width: 52px; height: 30px;
    pointer-events: none; transition: transform .32s cubic-bezier(.34, 1.4, .5, 1); }
  .m-dock-pill.live { transition: none; }

  .m-dock-pill-fill { position: absolute; inset: 0; border-radius: 999px;
    background: color-mix(in srgb, var(--ink) 11%, transparent);
    animation: m-pill-pop .34s cubic-bezier(.34, 1.4, .5, 1); }

  /* a small liquid overshoot on arrival — the one flourish this control gets,
     since it's tapped on nearly every screen */
  @keyframes m-pill-pop {
    0%   { transform: scaleX(.75); opacity: .5; }
    55%  { transform: scaleX(1.12); opacity: 1; }
    100% { transform: scaleX(1); opacity: 1; }
  }

  .m-tab { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 3px;
    padding: 0; border: 0; background: transparent; cursor: pointer;
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }

  .m-tab-ico { width: 52px; height: 30px; display: flex; align-items: center; justify-content: center;
    color: var(--muted); transition: color .18s ease; }
  .m-tab.on .m-tab-ico { color: var(--ink); }

  .m-tab-glyph { width: 21px; height: 21px; display: block; }

  .m-tab-label { font-family: var(--sans); font-size: 10.5px; font-weight: 600; line-height: 1;
    color: var(--muted); transition: color .18s ease; }
  .m-tab.on .m-tab-label { color: var(--ink); }

  @media (prefers-reduced-motion: reduce) {
    .m-dock-pill, .m-tab-ico, .m-tab-label { transition: none; }
    .m-dock-pill-fill { animation: none; }
  }
</style>

<script module>
  import { writable, get } from 'svelte/store';
  // one row open at a time, like iOS: opening a row closes the last one
  const openRow = writable(null);
</script>

<script>
  // Swipe left to reveal a row's actions (iOS Mail / Stocks). Only a leftward
  // horizontal swipe is claimed; a right swipe or a vertical one passes
  // through to the phone pager or the scroll. While a row is open, the next
  // touch anywhere else closes it and is used up, so no tap lands under it.
  // enabled=false renders the row bare (hover devices keep hover actions).
  //
  // actions: [{ label, onclick, tone?: 'loss' }], left to right.
  // --sw-bleed (inherited) widens the row into the page gutter so the actions
  // reach the screen edge; --sw-r rounds it.
  import { onDestroy } from 'svelte';

  let { actions = [], enabled = true, children } = $props();

  const ACT_W = 76;
  const SLOP = 8;
  const width = $derived(actions.length * ACT_W);
  const me = {};

  let actsEl = $state();
  let x = $state(0);
  let live = $state(false);
  const open = $derived($openRow === me);

  // at rest the row sits open or shut; a live finger overrides
  $effect(() => { if (!live) x = open ? -width : 0; });

  let x0 = null, y0 = 0, base = 0, axis = null, lastX = 0, lastT = 0, vx = 0;

  function onStart(e) {
    if (e.touches.length !== 1) { x0 = null; return; }
    const t = e.touches[0];
    x0 = lastX = t.clientX;
    y0 = t.clientY;
    lastT = e.timeStamp;
    base = open ? -width : 0;
    axis = null;
    vx = 0;
  }
  function onMove(e) {
    if (x0 == null) return;
    const t = e.touches[0];
    const dx = t.clientX - x0, dy = t.clientY - y0;
    if (axis == null) {
      if (Math.hypot(dx, dy) < SLOP) return;
      axis = Math.abs(dx) > Math.abs(dy) * 1.3 && (dx < 0 || base < 0) ? 'x' : 'pass';
      if (axis === 'x') live = true;
    }
    if (axis !== 'x') return;
    if (e.cancelable) e.preventDefault();
    e.stopPropagation(); // the pager must not page under a row swipe
    if (e.timeStamp > lastT) vx = (t.clientX - lastX) / (e.timeStamp - lastT);
    lastX = t.clientX;
    lastT = e.timeStamp;
    const nx = Math.min(0, base + dx);
    x = nx < -width ? -width + (nx + width) * 0.3 : nx; // rubber band past the actions
  }
  function onEnd() {
    if (axis === 'x') {
      const keep = vx < -0.3 || (vx <= 0.3 && x < -width / 2);
      live = false;
      if (keep) openRow.set(me);
      else if (open) openRow.set(null);
      x = keep ? -width : 0;
    }
    x0 = null;
    axis = null;
  }

  function swipe(node) {
    node.addEventListener('touchstart', onStart, { passive: true });
    node.addEventListener('touchmove', onMove, { passive: false });
    node.addEventListener('touchend', onEnd);
    node.addEventListener('touchcancel', onEnd);
    return {
      destroy() {
        node.removeEventListener('touchstart', onStart);
        node.removeEventListener('touchmove', onMove);
        node.removeEventListener('touchend', onEnd);
        node.removeEventListener('touchcancel', onEnd);
      },
    };
  }

  // the tap that closes an open row doesn't also press what's under it: its
  // touchend is cancelled (no click, no focus), and a stray click is eaten
  function swallowNextTap() {
    const end = (e) => { if (e.cancelable) e.preventDefault(); };
    const eat = (e) => { e.preventDefault(); e.stopPropagation(); done(); };
    const done = () => {
      window.removeEventListener('touchend', end, true);
      window.removeEventListener('click', eat, true);
      window.removeEventListener('touchstart', done, true);
      clearTimeout(timer);
    };
    window.addEventListener('touchend', end, { capture: true, passive: false });
    window.addEventListener('click', eat, true);
    window.addEventListener('touchstart', done, true); // next gesture: fresh start
    const timer = setTimeout(done, 1500);
  }

  $effect(() => {
    if (!open) return;
    const onTouch = (e) => {
      if (actsEl?.contains(e.target)) return;
      openRow.set(null);
      e.stopPropagation();
      swallowNextTap();
    };
    document.addEventListener('touchstart', onTouch, true);
    return () => document.removeEventListener('touchstart', onTouch, true);
  });

  onDestroy(() => { if (get(openRow) === me) openRow.set(null); });

  function run(a) {
    openRow.set(null);
    a.onclick?.();
  }
</script>

{#if enabled}
  <div class="sw" use:swipe>
    <!-- keyboard / VoiceOver reach the actions directly; focusing one opens the row -->
    <div class="sw-acts" class:shown={live || open} bind:this={actsEl} style="width:{width}px"
      onfocusin={() => openRow.set(me)}>
      {#each actions as a (a.label)}
        <button type="button" class="sw-act" class:loss={a.tone === 'loss'} onclick={() => run(a)}>{a.label}</button>
      {/each}
    </div>
    <div class="sw-fg" class:live style="transform:translateX({x}px)">
      {@render children()}
    </div>
  </div>
{:else}
  {@render children()}
{/if}

<style>
  .sw { position: relative; overflow: hidden; border-radius: var(--sw-r, 0);
    margin: 0 calc(-1 * var(--sw-bleed, 0px)); }
  .sw-fg { position: relative; z-index: 1; padding: 0 var(--sw-bleed, 0px); background: var(--surface);
    transition: transform .28s cubic-bezier(.22, .61, .36, 1); }
  .sw-fg.live { transition: none; }

  /* behind the row, flush right: neutral first, destructive last in loss.
     Transparent at rest (they'd fringe through the rounded clip's
     anti-aliasing), shown the moment a swipe starts, hidden only once the
     row has slid shut. Still focusable while transparent. */
  .sw-acts { position: absolute; top: 0; right: 0; bottom: 0; display: flex;
    opacity: 0; transition: opacity 0s linear .28s; }
  .sw-acts.shown { opacity: 1; transition: none; }
  .sw-act { flex: 1 1 0; min-width: 0; padding: 0 6px; border: 0; border-radius: 0; cursor: pointer;
    background: color-mix(in srgb, var(--ink) 16%, var(--surface)); color: var(--ink);
    font: inherit; font-size: var(--fs-body); font-weight: 600; -webkit-tap-highlight-color: transparent; }
  .sw-act.loss { background: var(--loss); color: var(--paper); }
  .sw-act:active { filter: brightness(.88); }

  @media (prefers-reduced-motion: reduce) { .sw-fg { transition: none; } }
</style>

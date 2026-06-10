<script>
  // RingGauge — THE ring. One geometry for every donut in the app (dividends,
  // allocation, analyst ratings): a closed ring of filled annular sectors with
  // rounded corners and small gaps, a faint track behind, and a swappable core
  // readout (idle content at rest, the hovered segment's content on hover).
  //
  // segments: [{ key, color, value, tag, hero, per?, sub?, pick? }]
  //   value drives the arc span; tag/hero/per/sub fill the core on hover;
  //   pick() makes the sector clickable.
  // idle: { tag, hero, per?, sub? } — the core at rest.
  let { segments = [], idle = {}, heroSize = 30, size = '168px', minH = '132px' } = $props();

  // ── geometry (viewBox 0..120) — ported from the original Dividend Wraith ──
  const CX = 60, CY = 60, R = 47, SW = 10;
  const RI = R - SW / 2, RO = R + SW / 2;
  const CR = 2.5;
  const RAD = Math.PI / 180;
  const P = (ang, r) => `${(CX + r * Math.sin(ang * RAD)).toFixed(2)},${(CY - r * Math.cos(ang * RAD)).toFixed(2)}`;

  // filled annular sector with rounded corners (sweep clockwise from 12 o'clock)
  const barPath = (a0, a1) => {
    const arcLen = (a1 - a0) * RAD * RO;
    const cr = Math.max(0.1, Math.min(CR, (SW / 2) * 0.9, (arcLen / 2) * 0.9));
    const aO = cr / RO / RAD;
    const aI = cr / RI / RAD;
    const big = a1 - a0 > 180 ? 1 : 0;
    return [
      'M', P(a0 + aO, RO),
      'A', RO, RO, 0, big, 1, P(a1 - aO, RO),
      'Q', P(a1, RO), P(a1, RO - cr),
      'L', P(a1, RI + cr),
      'Q', P(a1, RI), P(a1 - aI, RI),
      'A', RI, RI, 0, big, 0, P(a0 + aI, RI),
      'Q', P(a0, RI), P(a0, RI + cr),
      'L', P(a0, RO - cr),
      'Q', P(a0, RO), P(a0 + aO, RO),
      'Z',
    ].join(' ');
  };
  // track = two half-ring sectors (a single 360° path can't arc-flag cleanly)
  const trackPath = barPath(0, 179.9) + ' ' + barPath(180, 359.9);

  const segs = $derived.by(() => {
    const list = segments.filter((s) => (s.value ?? 0) > 0);
    const total = list.reduce((sum, s) => sum + s.value, 0) || 1;
    const n = list.length;
    const gap = n > 1 ? 3 : 0;
    const usable = 360 - gap * n;
    let a = 0;
    return list.map((s, i) => {
      const span = Math.min(359.9, (s.value / total) * usable);
      const seg = { ...s, d: barPath(a, a + span), i };
      a += span + gap;
      return seg;
    });
  });

  let hovered = $state(null); // segment key, or null
  const active = $derived(hovered ? segs.find((s) => s.key === hovered) : null);
  const core = $derived(active ?? idle);
</script>

<div class="rgx" style="--rg-size:{size}; --rg-minh:{minH}; --rg-hero:{heroSize}px" role="img" aria-label={idle.tag ?? 'gauge'}>
  <div class="rgx-stage" onpointerleave={() => (hovered = null)}>
    <svg viewBox="0 0 120 120" class="rgx-svg">
      <path d={trackPath} class="rgx-track" />
      {#each segs as s (s.key)}
        <path d={s.d} fill={s.color} class="rgx-seg" class:dim={hovered && hovered !== s.key}
          class:clickable={!!s.pick} style="--i:{s.i}"
          onpointerenter={() => (hovered = s.key)}
          onclick={() => s.pick?.()}
          role={s.pick ? 'button' : undefined}>
          <title>{s.tag} — {s.hero}{s.per ?? ''}</title>
        </path>
      {/each}
    </svg>

    <div class="rgx-core">
      {#if core.tag}
        <div class="rgx-tag">
          {#if active}<span class="rgx-dot" style="background:{active.color}"></span>{/if}{core.tag}
        </div>
      {/if}
      {#if core.hero != null}
        <div class="rgx-hero" style={core.heroColor ? `color:${core.heroColor}` : ''}>{core.hero}{#if core.per}<span class="rgx-per">{core.per}</span>{/if}</div>
      {/if}
      {#if core.sub}<div class="rgx-sub">{core.sub}</div>{/if}
    </div>
  </div>
</div>

<style>
  .rgx { display: grid; place-items: center; height: 100%; min-height: var(--rg-minh); padding: 2px; min-width: 0; }
  .rgx-stage { position: relative; height: 100%; aspect-ratio: 1 / 1; max-height: var(--rg-size); }
  .rgx-svg { display: block; width: 100%; height: 100%; overflow: visible; }

  .rgx-track { fill: color-mix(in srgb, var(--ink) 9%, transparent); }
  .rgx-seg { transition: filter .16s ease; }
  .rgx-seg.clickable { cursor: pointer; }
  .rgx-seg.dim { filter: opacity(.26); }

  /* staggered fade-in on load */
  .rgx-seg { opacity: 0; animation: rgx-in .5s ease forwards; animation-delay: calc(var(--i) * .07s); }
  @keyframes rgx-in { to { opacity: 1; } }

  .rgx-core { position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 2px; text-align: center; pointer-events: none; }
  .rgx-tag { display: flex; align-items: center; gap: 5px; font-family: var(--sans); font-size: 9px;
    font-weight: 700; text-transform: uppercase; letter-spacing: .12em; color: var(--muted);
    max-width: 92px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rgx-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; }
  .rgx-hero { font-family: var(--mono); font-size: var(--rg-hero); font-weight: 700; line-height: 1.05;
    color: var(--ink); font-variant-numeric: tabular-nums; letter-spacing: -.02em; max-width: 96px; }
  .rgx-per { font-size: 12px; font-weight: 700; color: var(--muted); margin-left: 1px; }
  .rgx-sub { font-family: var(--mono); font-size: 9.5px; font-weight: 700; color: var(--muted);
    font-variant-numeric: tabular-nums; white-space: nowrap; margin-top: 2px; }

  @media (prefers-reduced-motion: reduce) {
    .rgx-seg { animation: none; opacity: 1; }
  }
</style>

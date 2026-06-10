<script>
  // ─────────────────────────────────────────────────────────────────────────
  // Sprout · design master — THE source of truth for design decisions.
  //
  // Direction (decided 2026-06-11): NEO-BRUTALIST. Border-only chrome on a shared
  // canvas, one pill button system, ink inversion as the selected state, color
  // reserved for data. Dark is the default theme; light is the paper original.
  // Refine the language HERE first; settled tokens graduate to app.css and the
  // live components adopt them.
  // ─────────────────────────────────────────────────────────────────────────
  import RingGauge from '$lib/components/RingGauge.svelte';
  import { theme, toggleTheme } from '$lib/theme.js';

  let pill = $state('1D');
  const PILLS = ['1D', '5D', '1M', '1Y', 'MAX'];
  let seg = $state('Value');

  const CORE = [
    { name: '--paper / --bg', usage: 'page + widget background (they are the SAME — border-only chrome)' },
    { name: '--ink', usage: 'text, borders, the selected state, hover shadows' },
    { name: '--muted', usage: 'secondary text, idle controls, labels' },
    { name: '--hairline', usage: 'internal rules inside widgets (never between widgets)' },
    { name: '--hover', usage: 'row/item hover wash where a border is too loud' },
  ];
  const ACCENTS = [
    { name: '--brand', v: '#0fb39a', usage: 'the jade — portfolio line, brand moments' },
    { name: '--gain', v: '#00c060', usage: 'up moves only' },
    { name: '--loss', v: '#ff4d4d', usage: 'down moves only' },
    { name: '--pink', v: '#ff90e8', usage: 'accent deck — rings, rare highlights' },
    { name: '--yellow', v: '#ffc900', usage: 'accent deck — cash panel, hold rating' },
    { name: '--blue', v: '#5b8def', usage: 'accent deck' },
    { name: '--purple', v: '#c994e8', usage: 'accent deck' },
    { name: '--coral', v: '#ff6e5e', usage: 'accent deck' },
  ];

  const RING_DEMO = [
    { key: 'a', color: '#0fb39a', value: 42, tag: 'NVDA', hero: '42.0', per: '%', sub: 'demo segment' },
    { key: 'b', color: '#ff90e8', value: 28, tag: 'AAPL', hero: '28.0', per: '%', sub: 'demo segment' },
    { key: 'c', color: '#ffc900', value: 18, tag: 'GOOG', hero: '18.0', per: '%', sub: 'demo segment' },
    { key: 'd', color: '#8a8478', value: 12, tag: 'other', hero: '12.0', per: '%', sub: 'demo segment' },
  ];
</script>

<div class="dm">
  <!-- ── masthead ── -->
  <header class="dm-head">
    <div>
      <h1 class="dm-title">sprout design</h1>
      <p class="dm-sub">master document · the law · last ratified jun 2026</p>
    </div>
    <button class="btn btn-line" onclick={toggleTheme}>theme: {$theme} — flip</button>
  </header>

  <!-- ── principles ── -->
  <section class="w dm-sec">
    <div class="w-h">principles</div>
    <ol class="dm-principles">
      <li><b>Border-only chrome.</b> Widgets share the page background; a 1px ink border is the only thing that separates a widget from the canvas. No fills, no resting shadows.</li>
      <li><b>One pill.</b> Every control is the same pill: plain text at rest → 1px ink outline on hover → solid ink (paper text) when selected or pressed. No other button shapes exist.</li>
      <li><b>Ink inversion is the selected state.</b> Active nav, picked range, pressed row — all flip to solid ink. Nothing else signals selection.</li>
      <li><b>Color is data.</b> Green/red are reserved for moves, jade for the portfolio, the accent deck for ring segments. Chrome is never colored.</li>
      <li><b>Widgets on a strict grid.</b> 4 columns, 16px gaps, standard spans (4×0.5 header, 4×2 chart, 2×1, 1×1). Bare (border-less) widgets are allowed for rings and centred figures.</li>
      <li><b>Motion is restrained.</b> 0.12s state transitions, staggered ring fade-ins, the stage's 0.18s rise. No sweeps, no glows, no parallax.</li>
    </ol>
  </section>

  <!-- ── tokens ── -->
  <section class="w dm-sec">
    <div class="w-h">tokens · core (theme-dependent — flip the theme above)</div>
    <div class="dm-rows">
      {#each CORE as t (t.name)}
        <div class="dm-row">
          <span class="dm-chip" style="background:var({t.name.split(' ')[0]})"></span>
          <code class="dm-code">{t.name}</code>
          <span class="dm-usage">{t.usage}</span>
        </div>
      {/each}
    </div>
    <div class="w-h dm-gap">tokens · accents (identical in both themes)</div>
    <div class="dm-rows">
      {#each ACCENTS as t (t.name)}
        <div class="dm-row">
          <span class="dm-chip" style="background:{t.v}"></span>
          <code class="dm-code">{t.name}</code>
          <span class="dm-usage">{t.usage}</span>
        </div>
      {/each}
    </div>
    <div class="w-h dm-gap">tokens · form</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">--bw: 1px</code><span class="dm-usage">every border — widgets, pills, hairline rules</span></div>
      <div class="dm-row"><code class="dm-code">--r: 4px</code><span class="dm-usage">widget corners; controls are full pills (999px)</span></div>
      <div class="dm-row"><code class="dm-code">--sh: none</code><span class="dm-usage">NOTHING casts a shadow at rest</span></div>
      <div class="dm-row"><code class="dm-code">--sh-pop: 4px 4px 0 ink</code><span class="dm-usage">interactive CARDS only, on hover, with translate(-2px,-2px)</span></div>
    </div>
  </section>

  <!-- ── type ── -->
  <section class="w dm-sec">
    <div class="w-h">type · Archivo (structure) + IBM Plex Mono (figures)</div>
    <div class="dm-type">
      <p class="t-display">Archivo 700 — the voice</p>
      <p class="t-body">Archivo 400/600 carries labels, names, and prose. Lowercase headers, uppercase micro-labels with .12em tracking.</p>
      <p class="t-mono">$3,711.75 · +42.8% · IBM Plex Mono 600 carries every figure, always tabular-nums.</p>
      <p class="dm-note">Space Grotesk/Mono remain loaded as the one-line revert path (swap --sans/--mono in app.css).</p>
    </div>
  </section>

  <!-- ── buttons ── -->
  <section class="w dm-sec">
    <div class="w-h">buttons · one system, three states</div>
    <div class="dm-btnrow">
      <button class="btn">idle is text</button>
      <button class="btn" style="border-color:var(--ink)">hover = outline</button>
      <button class="btn on">selected = ink</button>
      <button class="btn btn-line">.btn-line — standalone action</button>
      <button class="btn btn-sm btn-mono">.btn-sm .btn-mono</button>
      <button class="btn btn-quiet">.btn-quiet</button>
    </div>
    <div class="dm-btnrow">
      {#each PILLS as p (p)}
        <button class="btn btn-sm btn-mono" class:on={pill === p} onclick={() => (pill = p)}>{p}</button>
      {/each}
      <span class="dm-divider"></span>
      {#each ['Value', 'Return'] as s (s)}
        <button class="btn btn-sm btn-mono" class:on={seg === s} onclick={() => (seg = s)}>{s}</button>
      {/each}
    </div>
    <p class="dm-note">Used by: nav (home/log) · search · D/W window · chart ranges · Value/Return ·
      chart toolbar (Area/Compare/Indicators) · + Watch (.btn-line, watching = .on) · ← portfolio (.btn-quiet).
      Interactive CARDS (related stocks) are the one exception: hover lifts with translate + --sh-pop.</p>
  </section>

  <!-- ── widget anatomy ── -->
  <section class="w dm-sec">
    <div class="w-h">widget anatomy</div>
    <div class="dm-widgets">
      <div class="w dm-demo-w">
        <div class="w-h">bordered widget</div>
        <p class="dm-usage">1px ink border, bg = page, 4px corners, 12–16px padding. Label: 10px uppercase muted, .12em tracking.</p>
      </div>
      <div class="dm-demo-w dm-bare">
        <div class="w-h">bare widget</div>
        <p class="dm-usage">No border at all — for rings and centred hero figures. Sits in the same grid cell sizes.</p>
      </div>
    </div>
  </section>

  <!-- ── the ring ── -->
  <section class="w dm-sec">
    <div class="w-h">RingGauge · the only donut</div>
    <div class="dm-ringrow">
      <div class="dm-ringcell">
        <RingGauge segments={RING_DEMO} idle={{ tag: 'demo', hero: '100', per: '%', sub: 'hover a segment' }} />
      </div>
      <p class="dm-usage">One geometry for dividends, allocation, and analyst ratings: closed ring of filled
        annular sectors (rounded corners, 3° gaps) over a faint track; core swaps to the hovered segment;
        staggered fade-in. Never draw a donut any other way.</p>
    </div>
  </section>

  <!-- ── charts ── -->
  <section class="w dm-sec">
    <div class="w-h">charts</div>
    <p class="dm-usage">lightweight-charts can't read CSS vars — both chart components hold a theme-keyed PAL
      (ink/grid/muted/spy) and re-skin via applyOptions when the theme flips. Portfolio line is --brand;
      SPY is the muted dotted line; volume bars are gain/loss at 42% alpha; prev-close is a dashed muted line.</p>
  </section>
</div>

<style>
  .dm { max-width: 880px; margin: 0 auto; padding: 28px 28px 80px; display: flex; flex-direction: column; gap: 16px; }
  .dm-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; padding: 8px 2px 10px; }
  .dm-title { margin: 0; font-family: var(--sans); font-size: 34px; font-weight: 800; letter-spacing: -.02em; text-transform: lowercase; }
  .dm-sub { margin: 4px 0 0; font-family: var(--mono); font-size: 11px; color: var(--muted); }

  .w { background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); }
  .dm-sec { padding: 14px 18px 16px; display: flex; flex-direction: column; gap: 10px; }
  .w-h { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: var(--muted); }
  .dm-gap { margin-top: 8px; }

  .dm-principles { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 8px;
    font-family: var(--sans); font-size: 13.5px; line-height: 1.55; }
  .dm-principles b { font-weight: 700; }

  .dm-rows { display: flex; flex-direction: column; }
  .dm-row { display: flex; align-items: center; gap: 12px; padding: 7px 0;
    border-bottom: var(--bw) solid var(--hairline); }
  .dm-row:last-child { border-bottom: 0; }
  .dm-chip { width: 22px; height: 22px; flex: 0 0 auto; border-radius: 6px; border: var(--bw) solid var(--ink); }
  .dm-code { font-family: var(--mono); font-size: 12px; font-weight: 600; min-width: 170px; }
  .dm-usage { font-family: var(--sans); font-size: 12.5px; color: var(--muted); line-height: 1.5; margin: 0; }

  .dm-type { display: flex; flex-direction: column; gap: 8px; }
  .t-display { margin: 0; font-family: var(--sans); font-size: 30px; font-weight: 700; letter-spacing: -.02em; }
  .t-body { margin: 0; font-family: var(--sans); font-size: 14px; line-height: 1.6; }
  .t-mono { margin: 0; font-family: var(--mono); font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .dm-note { margin: 2px 0 0; font-family: var(--mono); font-size: 10.5px; color: var(--muted); line-height: 1.6; }

  .dm-btnrow { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
  .dm-divider { width: 1px; height: 20px; background: var(--hairline); margin: 0 8px; }

  .dm-widgets { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .dm-demo-w { padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
  .dm-bare { border: 0; background: transparent; }

  .dm-ringrow { display: grid; grid-template-columns: 200px 1fr; gap: 20px; align-items: center; }
  .dm-ringcell { height: 180px; }

  @media (max-width: 700px) {
    .dm-widgets, .dm-ringrow { grid-template-columns: 1fr; }
  }
</style>

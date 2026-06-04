<script>
  // ─────────────────────────────────────────────────────────────────────────
  // Sprout · Neo-Brutalist design language — living style guide.
  //
  // ★ SOURCE OF TRUTH. This route is the canonical design master for Sprout —
  // the de-facto reference every page is migrated against. Refine the language
  // HERE first; styles are scoped to this component so nothing leaks to the live
  // app. Once a token/component is settled, it graduates into app.css and the
  // real components adopt the classes. (No separate doc — this page is it.)
  //
  // Direction: refined neo-brutalist. Jade teal is the BRAND (primary actions, hero
  // accents) on the ink + paper core; a playful deck of accents (pink/yellow/teal/
  // blue/purple/coral) backs it for blocks, charts and the card suits. Thick ink
  // borders, HARD offset shadows (zero blur), chunky confident type. WIP — palette
  // mix is being tuned; jade + core are locked.
  // ─────────────────────────────────────────────────────────────────────────

  import FeedbackButton from '$lib/components/FeedbackButton.svelte';
  // Demo actions for the master: resolve ok/!ok after a beat to drive working→success/error.
  const demoOk = () => new Promise((res) => setTimeout(() => res({ ok: true }), 900));
  const demoFail = () => new Promise((res) => setTimeout(() => res({ ok: false }), 900));

  // Segmented period switcher — interactive; selection recolours to ink.
  const PERIODS = ['1M', '3M', '1Y', 'ALL'];
  let period = $state('1M');

  // Accent deck reused for two playful effects below.
  const ACCENTS = ['#ff90e8', '#ffc900', '#23a094', '#5b8def', '#c994e8', '#ff6e5e'];

  // Sidebar hover gets a random accent-coloured hard shadow each time you enter a link.
  function randAccentShadow(e) {
    e.currentTarget.style.setProperty('--hovsh', ACCENTS[Math.floor(Math.random() * ACCENTS.length)]);
  }

  // ── Sample data (mirrors the real API shapes) ──────────────────────────────
  const ALLOC = {
    labels: ['NVDA', 'AAPL', 'MSFT', 'SPY', 'Cash', 'Other'],
    values: [21400, 16800, 12300, 9600, 7200, 5100]
  };
  const ALLOC_TOTAL = ALLOC.values.reduce((a, b) => a + b, 0);

  const PNL = {
    tickers: ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'PYPL'],
    values: [4820, 1960, 740, -1130, -2240]
  };

  const POSITIONS = [
    { ticker: 'NVDA', shares: 142, cost: 88.4, price: 150.7, pnl: 8826, ret: 70.5, w: 27.1 },
    { ticker: 'AAPL', shares: 96, cost: 142.1, price: 175.0, pnl: 3158, ret: 23.1, w: 21.3 },
    { ticker: 'MSFT', shares: 30, cost: 360.0, price: 410.2, pnl: 1506, ret: 13.9, w: 15.6 },
    { ticker: 'TSLA', shares: 40, cost: 250.0, price: 221.7, pnl: -1132, ret: -11.3, w: 12.2 },
    { ticker: 'PYPL', shares: 70, cost: 92.0, price: 60.0, pnl: -2240, ret: -34.8, w: 9.1 }
  ];

  const CARDS = [
    { rank: 'A', suit: 'sp', sym: '♠', ticker: 'NVDA', name: 'NVIDIA Corp', pct: 27.1, up: true },
    { rank: 'K', suit: 'ht', sym: '♥', ticker: 'AAPL', name: 'Apple Inc.', pct: 21.3, up: true },
    { rank: 'Q', suit: 'dm', sym: '♦', ticker: 'MSFT', name: 'Microsoft', pct: 15.6, up: true },
    { rank: 'J', suit: 'cl', sym: '♣', ticker: 'TSLA', name: 'Tesla Inc.', pct: 12.2, up: false },
    { joker: true, cash: 7204.50 }
  ];

  // ── Brutalist donut geometry (flat segments, ink separators) ───────────────
  // Categorical ramp from the accent deck. Provisional; real chart theming (06)
  // lands later with Lightweight Charts.
  const R = 33.6, SW = 18, C = 2 * Math.PI * R;
  const DONUT_COLORS = ['#ff90e8', '#ffc900', '#23a094', '#5b8def', '#c994e8', '#1a1a1a'];
  let donutArcs = $derived.by(() => {
    let acc = 0;
    return ALLOC.values.map((v, i) => {
      const frac = v / ALLOC_TOTAL;
      const seg = { len: frac * C, offset: -acc * C, color: DONUT_COLORS[i % DONUT_COLORS.length] };
      acc += frac;
      return seg;
    });
  });

  // ── Brutalist P&L bars ─────────────────────────────────────────────────────
  const PNL_MAX = Math.max(...PNL.values.map((v) => Math.abs(v)));
  let pnlRows = $derived(
    PNL.tickers.map((t, i) => {
      const v = PNL.values[i];
      return { ticker: t, value: v, pct: (Math.abs(v) / PNL_MAX) * 50, gain: v >= 0 };
    })
  );

  // ── Flat equity-curve mock (brutalist area, stepped feel) ──────────────────
  const CURVE = [18, 22, 20, 28, 34, 31, 42, 39, 48, 55, 51, 62, 70, 66, 78];
  let curvePath = $derived.by(() => {
    const w = 600, h = 180, max = 85, min = 10;
    const pts = CURVE.map((v, i) => {
      const x = (i / (CURVE.length - 1)) * w;
      const y = h - ((v - min) / (max - min)) * h;
      return [x, y];
    });
    const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
    const area = `${line} L${w} ${h} L0 ${h} Z`;
    return { line, area };
  });

  function money(v) {
    return '$' + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  function signed(v) {
    return (v >= 0 ? '+' : '−') + '$' + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
  <link
    href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="nb">
  <main class="nb-wrap">
    <!-- ── Hero / manifesto ────────────────────────────────────────────── -->
    <section class="nb-hero">
      <h1>Jade leads,<br />the deck plays along.</h1>
      <p>
        Jade teal is the brand on an ink + paper core — then a playful deck of accents
        (pink, yellow, teal, blue, purple, coral) backs it up. Thick ink borders, hard
        offset shadows (zero blur), chunky confident type. Playful, never sloppy. Every number stays legible.
      </p>
      <div class="nb-hero-chips">
        <span class="nb-chip" style="--c:var(--brand)">jade brand</span>
        <span class="nb-chip" style="--c:#ffc900">accent deck</span>
        <span class="nb-chip" style="--c:#5b8def">hard shadow</span>
        <span class="nb-chip" style="--c:#ff6e5e">honest data</span>
      </div>
    </section>

    <!-- ── Foundations: colour ─────────────────────────────────────────── -->
    <section id="tokens">
      <h2 class="nb-h2">01 · Foundations</h2>
      <p class="nb-lead"><b>Jade + ink + paper</b> carry the identity. <b>Semantic</b> gain/loss are fixed. And the <b>accent deck</b> is back — pink, yellow, teal, blue, purple, coral — for blocks, charts and card suits. (WIP: tell me which accents to keep and where.)</p>

      <div class="nb-pal">
        <span class="nb-pal-tag">Core — structure</span>
        <div class="nb-swatches">
          <div class="nb-sw" style="--c:#1a1a1a; --t:#fff"><b>Ink</b><code>#1a1a1a</code></div>
          <div class="nb-sw" style="--c:#f5f1e8; --t:#1a1a1a"><b>Paper</b><code>#f5f1e8</code></div>
          <div class="nb-sw" style="--c:#ffffff; --t:#1a1a1a"><b>Surface</b><code>#ffffff</code></div>
        </div>
      </div>

      <div class="nb-pal">
        <span class="nb-pal-tag">Brand — identity</span>
        <div class="nb-swatches">
          <div class="nb-sw" style="--c:#0fb39a; --t:#1a1a1a"><b>Jade</b><code>#0fb39a</code></div>
          <div class="nb-sw" style="--c:#0a7d6b; --t:#fff"><b>Jade deep</b><code>#0a7d6b</code></div>
        </div>
      </div>

      <div class="nb-pal">
        <span class="nb-pal-tag">Semantic — earned by meaning</span>
        <div class="nb-swatches">
          <div class="nb-sw" style="--c:#00c060; --t:#1a1a1a"><b>Gain</b><code>#00c060</code></div>
          <div class="nb-sw" style="--c:#ff4d4d; --t:#1a1a1a"><b>Loss</b><code>#ff4d4d</code></div>
        </div>
      </div>

      <div class="nb-pal">
        <span class="nb-pal-tag">Accents — the playful deck (blocks · charts · suits)</span>
        <div class="nb-swatches">
          <div class="nb-sw" style="--c:#ff90e8; --t:#1a1a1a"><b>Pink</b><code>#ff90e8</code></div>
          <div class="nb-sw" style="--c:#ffc900; --t:#1a1a1a"><b>Yellow</b><code>#ffc900</code></div>
          <div class="nb-sw" style="--c:#23a094; --t:#fff"><b>Teal</b><code>#23a094</code></div>
          <div class="nb-sw" style="--c:#5b8def; --t:#fff"><b>Blue</b><code>#5b8def</code></div>
          <div class="nb-sw" style="--c:#c994e8; --t:#1a1a1a"><b>Purple</b><code>#c994e8</code></div>
          <div class="nb-sw" style="--c:#ff6e5e; --t:#1a1a1a"><b>Coral</b><code>#ff6e5e</code></div>
        </div>
      </div>
    </section>

    <!-- ── Type ─────────────────────────────────────────────────────────── -->
    <section id="type">
      <h2 class="nb-h2">02 · Type</h2>
      <p class="nb-lead"><b>Space Grotesk</b> for everything structural; <b>Space Mono</b> for figures so columns line up.</p>

      <div class="nb-panel nb-typespec">
        <div class="nb-type-row"><span class="nb-type-meta">Display / 700</span><span style="font-size:46px; font-weight:700; letter-spacing:-.02em">Portfolio Value</span></div>
        <div class="nb-type-row"><span class="nb-type-meta">Heading / 700</span><span style="font-size:28px; font-weight:700">$128,402.18</span></div>
        <div class="nb-type-row"><span class="nb-type-meta">Label / 700 caps</span><span style="font-size:12px; font-weight:700; letter-spacing:.12em; text-transform:uppercase">Net worth</span></div>
        <div class="nb-type-row"><span class="nb-type-meta">Body / 400</span><span style="font-size:15px">Equity plus available cash, marked to the latest close.</span></div>
        <div class="nb-type-row"><span class="nb-type-meta">Mono / figures</span><span style="font-family:'Space Mono',monospace; font-size:18px">+$4,820.00 · −34.8% · 142.0000</span></div>
      </div>
    </section>

    <!-- ── Elevation ────────────────────────────────────────────────────── -->
    <section id="elevation">
      <h2 class="nb-h2">03 · Elevation</h2>
      <p class="nb-lead">No blur, ever. Depth = a solid ink shadow offset down-right. Interactivity = the surface lifts toward you, shadow grows.</p>

      <div class="nb-elev-grid">
        <div class="nb-elev nb-e1"><b>Flat</b><span>border only</span></div>
        <div class="nb-elev nb-e2"><b>Raised</b><span>4px 4px 0</span></div>
        <div class="nb-elev nb-e3"><b>Pop</b><span>7px 7px 0</span></div>
        <button class="nb-elev nb-e-int"><b>Interactive</b><span>hover me ↗</span></button>
      </div>
    </section>

    <!-- ── Controls ─────────────────────────────────────────────────────── -->
    <section id="buttons">
      <h2 class="nb-h2">04 · Controls</h2>
      <div class="nb-panel">
        <div class="nb-row">
          <button class="nb-btn nb-btn-primary">Add trade</button>
          <button class="nb-btn nb-btn-yellow">Export</button>
          <button class="nb-btn nb-btn-surface">Cancel</button>
          <button class="nb-btn nb-btn-loss">Delete</button>
          <button class="nb-btn nb-btn-ghost">Ghost</button>
        </div>
        <div class="nb-row" style="margin-top:18px">
          <div class="nb-seg">
            {#each PERIODS as p}
              <button class:is-on={period === p} onclick={() => (period = p)}>{p}</button>
            {/each}
          </div>
          <input class="nb-input" placeholder="Search ticker…" />
          <span class="nb-badge" style="--c:#00c060">▲ GAIN</span>
          <span class="nb-badge" style="--c:#ff4d4d">▼ LOSS</span>
        </div>
      </div>

      <p class="nb-lead" style="margin-top:26px">
        <b>Self-reporting actions.</b> No toast popping up elsewhere — the button <em>is</em> the
        notification. Click it: the label morphs into working dots, then green cards fan out like a
        dealt hand with a <span style="font-weight:700">✓</span>; on failure it shakes, a red fan
        snaps out, and the glyph turns to <span style="font-weight:700">✕</span>. Then it resets.
      </p>
      <div class="nb-panel nb-fb-grid">
        <div class="nb-fb-cell">
          <FeedbackButton label="Add trade" action={demoOk} />
          <span class="nb-fb-name"><b>success</b> · green cards fan out, ✓</span>
        </div>
        <div class="nb-fb-cell">
          <FeedbackButton label="Add trade" action={demoFail} />
          <span class="nb-fb-name"><b>error</b> · horizontal shake + red fan, ✕</span>
        </div>
      </div>
    </section>

    <!-- ── KPI cards ────────────────────────────────────────────────────── -->
    <section id="kpis">
      <h2 class="nb-h2">05 · KPI cards</h2>
      <p class="nb-lead">Each metric is a flat block. The jade hero anchors it; the accent deck colours the rest. (WIP — tell me which cards keep colour.)</p>

      <div class="nb-kpi-grid">
        <div class="nb-kpi" style="--fill:var(--brand)">
          <span class="nb-kpi-label">Portfolio value</span>
          <span class="nb-kpi-val">$128,402</span>
          <span class="nb-kpi-sub">equity + cash</span>
        </div>
        <div class="nb-kpi" style="--fill:var(--gain)">
          <span class="nb-kpi-label">Total P&amp;L</span>
          <span class="nb-kpi-val">+$31,884</span>
          <span class="nb-kpi-sub">▲ unrealized + realized</span>
        </div>
        <div class="nb-kpi" style="--fill:var(--pink)">
          <span class="nb-kpi-label">Free cash</span>
          <span class="nb-kpi-val">$7,204</span>
          <span class="nb-kpi-sub">available to deploy</span>
        </div>

        <!-- Progress / goal card -->
        <div class="nb-kpi nb-goal" style="--fill:var(--surface)">
          <span class="nb-kpi-label">2026 goal</span>
          <span class="nb-goal-val">$128,402 <em>/ $150,000</em></span>
          <div class="nb-progress"><div class="nb-progress-fill" style="width:85.6%"></div></div>
          <span class="nb-kpi-sub">85.6% there</span>
        </div>
      </div>
    </section>

    <!-- ── Charts & data ────────────────────────────────────────────────── -->
    <section id="data">
      <h2 class="nb-h2">06 · Charts &amp; data</h2>
      <p class="nb-lead">Charts get the same frame as everything else. Flat fills, ink axes, mono ticks. (Lightweight Charts will be themed to match: ink crosshair, flat area, no gradient.)</p>

      <div class="nb-data-grid">
        <!-- Equity curve -->
        <div class="nb-panel nb-chart">
          <div class="nb-chart-head"><b>Portfolio value</b><span class="nb-mono">+$4,820 · 30d</span></div>
          <svg viewBox="0 0 600 180" class="nb-chart-svg" preserveAspectRatio="none">
            <line x1="0" y1="60" x2="600" y2="60" class="nb-grid" />
            <line x1="0" y1="120" x2="600" y2="120" class="nb-grid" />
            <path d={curvePath.area} fill="#ff90e8" />
            <path d={curvePath.line} fill="none" stroke="#1a1a1a" stroke-width="3" stroke-linejoin="round" />
          </svg>
        </div>

        <!-- Allocation donut + legend -->
        <div class="nb-panel nb-alloc">
          <div class="nb-chart-head"><b>Allocation</b></div>
          <svg class="nb-donut" viewBox="0 0 100 100">
            <g transform="rotate(-90 50 50)">
              {#each donutArcs as a}
                <circle cx="50" cy="50" r={R} fill="none" stroke={a.color} stroke-width={SW}
                  stroke-dasharray="{a.len} {C - a.len}" stroke-dashoffset={a.offset} />
              {/each}
              <circle cx="50" cy="50" r={R + SW / 2} fill="none" stroke="#1a1a1a" stroke-width="2" />
              <circle cx="50" cy="50" r={R - SW / 2} fill="none" stroke="#1a1a1a" stroke-width="2" />
            </g>
          </svg>
          <div class="nb-legend">
            {#each ALLOC.labels as label, i}
              <div class="nb-legend-row">
                <span class="nb-legend-dot" style="background:{DONUT_COLORS[i % DONUT_COLORS.length]}"></span>
                <span class="nb-legend-name">{label}</span>
                <span class="nb-mono nb-legend-pct">{((ALLOC.values[i] / ALLOC_TOTAL) * 100).toFixed(1)}%</span>
              </div>
            {/each}
          </div>
        </div>

        <!-- Diverging P&L bars -->
        <div class="nb-panel nb-pnl">
          <div class="nb-chart-head"><b>Unrealized P&amp;L</b><span class="nb-mono">by ticker</span></div>
          <div class="nb-pnl-bars">
            {#each pnlRows as r}
              <div class="nb-pnl-row">
                <span class="nb-pnl-ticker">{r.ticker}</span>
                <div class="nb-pnl-track">
                  <span class="nb-pnl-zero"></span>
                  <span class="nb-pnl-bar" class:loss={!r.gain}
                    style="width:{r.pct}%; {r.gain ? 'left:50%' : 'right:50%'}"></span>
                  <span class="nb-mono nb-pnl-val" class:left={!r.gain}
                    style="{r.gain ? `left:calc(50% + ${r.pct}% + 8px)` : `right:calc(50% + ${r.pct}% + 8px)`}">{signed(r.value)}</span>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>
    </section>

    <!-- ── Positions table ──────────────────────────────────────────────── -->
    <section id="table">
      <h2 class="nb-h2">07 · Positions table</h2>
      <p class="nb-lead">Dense, mono-aligned, ink-ruled. Gains and losses get a flat colour cell, not just coloured text.</p>

      <div class="nb-panel nb-table-wrap">
        <table class="nb-table">
          <thead>
            <tr>
              <th class="l">Ticker</th><th>Shares</th><th>Cost</th><th>Price</th>
              <th>Unreal. $</th><th>Return %</th><th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {#each POSITIONS as p}
              <tr>
                <td class="l"><span class="nb-ticker-chip">{p.ticker}</span></td>
                <td class="nb-mono">{p.shares.toFixed(4)}</td>
                <td class="nb-mono">${p.cost.toFixed(2)}</td>
                <td class="nb-mono">${p.price.toFixed(2)}</td>
                <td class="nb-mono"><span class="nb-cell" class:up={p.pnl >= 0} class:down={p.pnl < 0}>{signed(p.pnl)}</span></td>
                <td class="nb-mono"><span class="nb-cell" class:up={p.ret >= 0} class:down={p.ret < 0}>{p.ret >= 0 ? '+' : '−'}{Math.abs(p.ret).toFixed(1)}%</span></td>
                <td class="nb-mono">{p.w.toFixed(1)}%</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── Sidebar ──────────────────────────────────────────────────────── -->
    <section id="nav">
      <h2 class="nb-h2">08 · Sidebar</h2>
      <div class="nb-sidebar-demo">
        <aside class="nb-sidebar">
          <div class="nb-sidebar-brand">sprout</div>
          <button class="nb-navlink is-active" onmouseenter={randAccentShadow}><span class="nb-navglyph">◆</span> Dashboard</button>
          <button class="nb-navlink" onmouseenter={randAccentShadow}><span class="nb-navglyph">↗</span> Investments</button>
          <button class="nb-navlink" onmouseenter={randAccentShadow}><span class="nb-navglyph">↓</span> Log</button>
          <div class="nb-sidebar-foot">jade + deck</div>
        </aside>
        <div class="nb-sidebar-note">
          <p>Active item is a filled ink block — unmistakable, no guessing which page you're on. Hover lifts the link with the house hard-shadow.</p>
        </div>
      </div>
    </section>

    <!-- ── Card hand (re-skin) ──────────────────────────────────────────── -->
    <section id="cards">
      <h2 class="nb-h2">09 · Card hand</h2>
      <p class="nb-lead">The holographic deck becomes a flat brutalist deck: thick ink border, hard shadow, a saturated suit block, chunky ticker, mono percentage. Holo foil → a flat diagonal shine swipe on hover.</p>

      <div class="nb-hand">
        {#each CARDS as c, i}
          <div class="nb-card nb-suit-{c.joker ? 'jk' : c.suit}" style="--i:{i}">
            {#if c.joker}
              <div class="nb-card-corner tl">★</div>
              <div class="nb-card-corner br">★</div>
              <div class="nb-card-body">
                <div class="nb-card-suitblock">JOKER</div>
                <div class="nb-card-ticker">CASH</div>
                <div class="nb-mono nb-card-pct">{money(c.cash)}</div>
                <div class="nb-card-pctlabel">free cash</div>
              </div>
            {:else}
              <div class="nb-card-corner tl">{c.rank}<span>{c.sym}</span></div>
              <div class="nb-card-corner br">{c.rank}<span>{c.sym}</span></div>
              <div class="nb-card-body">
                <div class="nb-card-suitblock">{c.sym}</div>
                <div class="nb-card-ticker">{c.ticker}</div>
                <div class="nb-card-name">{c.name}</div>
                <div class="nb-mono nb-card-pct" class:down={!c.up}>{c.pct.toFixed(1)}%</div>
                <div class="nb-card-pctlabel">of portfolio</div>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </section>

    <footer class="nb-foot">
      <span>sprout · neo-brutalist · jade · canonical design master at <code>/design</code></span>
      <span>this doc governs migration — refine here, then port the live pages →</span>
    </footer>
  </main>
</div>

<style>
  /* ═══════════════════════════════════════════════════════════════════════
     TOKENS — graduate this block into app.css @theme on approval.
     ═══════════════════════════════════════════════════════════════════════ */
  .nb {
    /* core — structure (kept from v0.2) */
    --ink: #1a1a1a;
    --paper: #f5f1e8;
    --surface: #ffffff;
    /* brand — identity (kept from v0.2) */
    --brand: #0fb39a;        /* jade teal */
    --brand-deep: #0a7d6b;   /* hover / text-on-light */
    /* accents — the playful deck, back by request */
    --pink: #ff90e8;
    --yellow: #ffc900;
    --teal: #23a094;
    --blue: #5b8def;
    --purple: #c994e8;
    --coral: #ff6e5e;
    /* semantic — stark, high-saturation so gains/losses jump. Both carry INK text,
       so loss is kept bright enough for black to contrast crisply. */
    --gain: #00c060;
    --loss: #ff4d4d;

    --bw: 2.5px;                          /* border weight */
    --sh: 4px 4px 0 var(--ink);           /* raised */
    --sh-pop: 7px 7px 0 var(--ink);       /* pop */
    --r: 6px;                             /* slight radius — refined, not razor */

    --sans: 'Space Grotesk', 'Helvetica Neue', Arial, system-ui, sans-serif;
    --mono: 'Space Mono', ui-monospace, 'SF Mono', Menlo, monospace;

    /* Full-screen takeover so the legacy app chrome doesn't bleed in. */
    position: fixed;
    inset: 0;
    z-index: 50;
    overflow-y: auto;
    background: var(--paper);
    color: var(--ink);
    font-family: var(--sans);
    -webkit-font-smoothing: antialiased;
  }
  .nb *, .nb *::before, .nb *::after { box-sizing: border-box; }
  .nb-mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }

  /* ── Layout ──────────────────────────────────────────────────────────── */
  .nb-wrap { max-width: 1080px; margin: 0 auto; padding: 44px 26px 90px; }
  .nb section { margin-top: 64px; }
  .nb-h2 {
    font-size: 13px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
    display: inline-block; padding: 6px 12px; margin: 0 0 6px;
    background: var(--ink); color: var(--surface); border-radius: 4px;
  }
  .nb-lead { font-size: 15px; max-width: 60ch; margin: 10px 0 22px; line-height: 1.5; }
  .nb-lead b { font-weight: 700; }
  .nb-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }

  /* ── Hero ────────────────────────────────────────────────────────────── */
  .nb-hero {
    margin-top: 24px; padding: 40px 36px;
    background: var(--pink); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh-pop);
  }
  .nb-hero h1 { margin: 0; font-size: clamp(34px, 6vw, 64px); font-weight: 700; line-height: 1.02; letter-spacing: -.03em; }
  .nb-hero p { max-width: 56ch; margin: 18px 0 0; font-size: 16px; line-height: 1.5; }
  .nb-hero-chips { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
  .nb-chip {
    font-size: 13px; font-weight: 700; padding: 7px 14px; color: var(--ink);
    background: var(--c, var(--surface)); border: var(--bw) solid var(--ink); border-radius: 999px; box-shadow: var(--sh);
  }

  /* ── Colour swatches ─────────────────────────────────────────────────── */
  .nb-pal { margin-bottom: 22px; }
  .nb-pal-tag {
    display: inline-block; font-family: var(--mono); font-size: 11px; font-weight: 700;
    letter-spacing: .04em; color: #8a8478; margin-bottom: 10px;
  }
  .nb-swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 14px; }
  .nb-sw {
    background: var(--c); color: var(--t); padding: 18px 14px; min-height: 96px;
    display: flex; flex-direction: column; justify-content: flex-end; gap: 2px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh);
  }
  .nb-sw b { font-size: 15px; font-weight: 700; }
  .nb-sw code { font-family: var(--mono); font-size: 11px; opacity: .85; }

  /* ── Generic panel ───────────────────────────────────────────────────── */
  .nb-panel {
    background: var(--surface); border: var(--bw) solid var(--ink);
    border-radius: var(--r); box-shadow: var(--sh); padding: 22px;
  }

  /* ── Type spec ───────────────────────────────────────────────────────── */
  .nb-typespec { display: flex; flex-direction: column; gap: 18px; }
  .nb-type-row { display: flex; align-items: baseline; gap: 18px; border-bottom: 1.5px dashed #d9d3c4; padding-bottom: 16px; }
  .nb-type-row:last-child { border-bottom: 0; padding-bottom: 0; }
  .nb-type-meta { flex: 0 0 130px; font-family: var(--mono); font-size: 11px; color: #8a8478; }

  /* ── Elevation ───────────────────────────────────────────────────────── */
  .nb-elev-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 22px; }
  .nb-elev {
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    min-height: 110px; padding: 18px; display: flex; flex-direction: column; justify-content: flex-end;
    font: inherit; color: inherit; text-align: left;
  }
  .nb-elev b { font-size: 16px; font-weight: 700; }
  .nb-elev span { font-family: var(--mono); font-size: 11px; color: #8a8478; }
  .nb-e2 { box-shadow: var(--sh); }
  .nb-e3 { box-shadow: var(--sh-pop); }
  .nb-e-int { background: var(--yellow); box-shadow: var(--sh); cursor: pointer; transition: transform .12s, box-shadow .12s; }
  .nb-e-int:hover { transform: translate(-3px, -3px); box-shadow: var(--sh-pop); }
  .nb-e-int:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--ink); }

  /* ── Buttons / controls ──────────────────────────────────────────────── */
  .nb-btn {
    font-family: var(--sans); font-size: 14px; font-weight: 700; cursor: pointer;
    padding: 11px 20px; border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); transition: transform .1s, box-shadow .1s;
  }
  .nb-btn:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 var(--ink); }
  .nb-btn:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--ink); }
  .nb-btn-primary { background: var(--brand); }
  .nb-btn-yellow { background: var(--yellow); }
  .nb-btn-surface { background: var(--surface); }
  .nb-btn-loss { background: var(--loss); }
  .nb-btn-ghost { background: transparent; box-shadow: none; }
  .nb-btn-ghost:hover { background: var(--ink); color: var(--surface); transform: none; box-shadow: none; }

  .nb-seg { display: inline-flex; border: var(--bw) solid var(--ink); border-radius: var(--r); overflow: hidden; box-shadow: var(--sh); }
  .nb-seg button {
    font-family: var(--mono); font-size: 13px; font-weight: 700; cursor: pointer;
    padding: 9px 15px; background: var(--surface); border: 0; border-right: var(--bw) solid var(--ink);
  }
  .nb-seg button:last-child { border-right: 0; }
  .nb-seg button.is-on { background: var(--ink); color: var(--surface); }
  .nb-input {
    font-family: var(--sans); font-size: 14px; padding: 10px 14px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); background: var(--surface); box-shadow: var(--sh); min-width: 200px;
  }
  .nb-input:focus { outline: none; background: #fffdf5; }
  .nb-badge {
    font-family: var(--mono); font-size: 12px; font-weight: 700; padding: 6px 12px; color: var(--t, var(--ink));
    background: var(--c); border: var(--bw) solid var(--ink); border-radius: var(--r);
  }

  /* self-reporting button playground */
  .nb-fb-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 26px 22px; }
  .nb-fb-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }
  .nb-fb-name { font-family: var(--mono); font-size: 11px; color: #8a8478; }
  .nb-fb-name b { color: var(--ink); font-weight: 700; }

  /* ── KPI cards ───────────────────────────────────────────────────────── */
  .nb-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
  .nb-kpi {
    background: var(--fill); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); padding: 20px; display: flex; flex-direction: column; gap: 8px; min-height: 130px;
  }
  .nb-kpi-label { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
  .nb-kpi-val { font-family: var(--mono); font-size: 30px; font-weight: 700; line-height: 1; margin-top: auto; }
  .nb-kpi-sub { font-size: 12px; opacity: .75; }
  .nb-goal-val { font-family: var(--mono); font-size: 18px; font-weight: 700; margin-top: auto; }
  .nb-goal-val em { font-style: normal; opacity: .55; }
  .nb-progress { height: 14px; background: var(--paper); border: var(--bw) solid var(--ink); border-radius: 999px; overflow: hidden; margin: 4px 0 2px; }
  .nb-progress-fill { height: 100%; background: var(--teal); border-right: var(--bw) solid var(--ink); }

  /* ── Charts ──────────────────────────────────────────────────────────── */
  .nb-data-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }
  .nb-data-grid .nb-pnl { grid-column: 1 / -1; }
  .nb-chart-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
  .nb-chart-head b { font-size: 16px; font-weight: 700; }
  .nb-chart-head span { font-size: 12px; color: #8a8478; }
  .nb-chart-svg { width: 100%; height: 180px; display: block; }
  .nb-grid { stroke: #e7e1d3; stroke-width: 1.5; }

  .nb-alloc { display: flex; flex-direction: column; }
  .nb-donut { width: 150px; height: 150px; display: block; margin: 0 auto 14px; }
  .nb-legend { display: flex; flex-direction: column; gap: 7px; }
  .nb-legend-row { display: grid; grid-template-columns: 16px 1fr auto; align-items: center; gap: 10px; font-size: 13px; }
  .nb-legend-dot { width: 14px; height: 14px; border: 2px solid var(--ink); border-radius: 3px; }
  .nb-legend-name { font-weight: 600; }
  .nb-legend-pct { font-size: 13px; }

  .nb-pnl-bars { display: flex; flex-direction: column; gap: 10px; }
  .nb-pnl-row { display: grid; grid-template-columns: 56px 1fr; align-items: center; gap: 12px; }
  .nb-pnl-ticker { font-weight: 700; font-size: 13px; text-align: right; }
  .nb-pnl-track { position: relative; height: 26px; }
  .nb-pnl-zero { position: absolute; left: 50%; top: 0; bottom: 0; width: 2.5px; background: var(--ink); }
  .nb-pnl-bar { position: absolute; top: 3px; bottom: 3px; background: var(--gain); border: 2px solid var(--ink); border-radius: 3px; min-width: 4px; }
  .nb-pnl-bar.loss { background: var(--loss); }
  .nb-pnl-val { position: absolute; top: 50%; transform: translateY(-50%); font-size: 12px; font-weight: 700; white-space: nowrap; }
  .nb-pnl-val.left { transform: translate(-100%, -50%); }

  /* ── Table ───────────────────────────────────────────────────────────── */
  .nb-table-wrap { padding: 0; overflow: hidden; }
  .nb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .nb-table th, .nb-table td { padding: 12px 16px; text-align: right; white-space: nowrap; }
  .nb-table th.l, .nb-table td.l { text-align: left; }
  .nb-table thead th {
    font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    background: var(--ink); color: var(--surface); cursor: pointer;
  }
  .nb-table tbody tr { border-bottom: 2px solid var(--ink); }
  .nb-table tbody tr:last-child { border-bottom: 0; }
  .nb-table tbody tr:hover { background: #fffdf3; }
  .nb-ticker-chip { font-weight: 700; padding: 3px 9px; background: var(--yellow); border: 2px solid var(--ink); border-radius: 4px; }
  .nb-cell { padding: 3px 8px; border: 2px solid var(--ink); border-radius: 4px; font-weight: 700; }
  .nb-cell.up { background: var(--gain); }
  .nb-cell.down { background: var(--loss); }

  /* ── Sidebar demo ────────────────────────────────────────────────────── */
  .nb-sidebar-demo { display: grid; grid-template-columns: 230px 1fr; gap: 24px; align-items: start; }
  .nb-sidebar {
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); padding: 16px; display: flex; flex-direction: column; gap: 8px;
  }
  .nb-sidebar-brand { font-size: 20px; font-weight: 700; padding: 4px 8px 14px; }
  .nb-navlink {
    display: flex; align-items: center; gap: 12px; width: 100%; padding: 11px 12px;
    font-family: inherit; font-size: 14px; font-weight: 600; text-align: left; color: var(--ink);
    background: none; border: var(--bw) solid transparent; border-radius: var(--r); cursor: pointer; transition: all .12s;
  }
  /* hover lifts the link with a RANDOM accent-coloured hard shadow (set per-enter in JS) */
  .nb-navlink:hover { border-color: var(--ink); transform: translate(-2px, -2px); box-shadow: 4px 4px 0 var(--hovsh, var(--ink)); background: var(--surface); }
  .nb-navlink.is-active { background: var(--ink); color: var(--surface); }   /* selected page stays ink, never brand */
  .nb-navlink.is-active:hover { background: var(--ink); color: var(--surface); }   /* …even on hover — only its shadow goes colourful */
  .nb-navglyph { font-size: 15px; }
  .nb-sidebar-foot { margin-top: 12px; padding: 8px; font-family: var(--mono); font-size: 10px; color: #8a8478; }
  .nb-sidebar-note { padding-top: 8px; }
  .nb-sidebar-note p { font-size: 15px; line-height: 1.5; max-width: 46ch; }

  /* ── Card hand ───────────────────────────────────────────────────────── */
  .nb-hand { display: flex; flex-wrap: wrap; gap: 18px; padding: 8px 0; }
  .nb-card {
    position: relative; width: 152px; height: 214px; padding: 12px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: 10px; box-shadow: var(--sh);
    cursor: pointer; transition: transform .14s, box-shadow .14s; overflow: hidden;
  }
  .nb-card:hover { transform: translate(-3px, -6px) rotate(-1.5deg); box-shadow: var(--sh-pop); }
  /* flat diagonal "shine" swipe replaces the holo foil */
  .nb-card::after {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(115deg, transparent 40%, rgba(255,255,255,.55) 50%, transparent 60%);
    transform: translateX(-120%); transition: transform .5s ease;
  }
  .nb-card:hover::after { transform: translateX(120%); }
  .nb-suit-sp { --suit: var(--blue); }
  .nb-suit-ht { --suit: var(--coral); }
  .nb-suit-dm { --suit: var(--teal); }
  .nb-suit-cl { --suit: var(--yellow); }
  .nb-suit-jk { --suit: var(--purple); }
  .nb-card-corner { position: absolute; font-weight: 700; font-size: 16px; line-height: .9; display: flex; flex-direction: column; align-items: center; }
  .nb-card-corner span { font-size: 13px; }
  .nb-card-corner.tl { top: 9px; left: 10px; }
  .nb-card-corner.br { bottom: 9px; right: 10px; transform: rotate(180deg); }
  .nb-card-body { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; text-align: center; }
  .nb-card-suitblock {
    width: 46px; height: 46px; display: flex; align-items: center; justify-content: center;
    font-size: 24px; font-weight: 700; background: var(--suit); border: var(--bw) solid var(--ink); border-radius: 8px; margin-bottom: 8px;
  }
  .nb-suit-jk .nb-card-suitblock, .nb-suit-cl .nb-card-suitblock { font-size: 13px; letter-spacing: .04em; }
  .nb-card-ticker { font-size: 19px; font-weight: 700; }
  .nb-card-name { font-family: var(--mono); font-size: 8.5px; color: #8a8478; max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .nb-card-pct { font-size: 22px; font-weight: 700; margin-top: 8px; color: var(--gain); }
  .nb-card-pct.down { color: var(--loss); }
  .nb-card-pctlabel { font-family: var(--mono); font-size: 8px; text-transform: uppercase; letter-spacing: .08em; color: #a3a3a8; }

  /* ── Footer ──────────────────────────────────────────────────────────── */
  .nb-foot {
    margin-top: 72px; padding-top: 22px; border-top: var(--bw) solid var(--ink);
    display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px;
    font-family: var(--mono); font-size: 12px; color: #8a8478;
  }
  .nb-foot code { background: var(--ink); color: var(--surface); padding: 2px 6px; border-radius: 3px; }

  /* ── Responsive ──────────────────────────────────────────────────────── */
  @media (max-width: 760px) {
    .nb-data-grid { grid-template-columns: 1fr; }
    .nb-data-grid .nb-pnl { grid-column: auto; }
    .nb-sidebar-demo { grid-template-columns: 1fr; }
  }
  @media (prefers-reduced-motion: reduce) {
    .nb-card, .nb-card::after, .nb-btn, .nb-elev, .nb-navlink { transition: none; }
  }
</style>

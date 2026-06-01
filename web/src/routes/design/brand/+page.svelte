<script>
  // ─────────────────────────────────────────────────────────────────────────
  // Brand explorer — a companion to the design master (/design).
  //
  // Same real composition (hero · button · active nav · KPI w/ gain-loss · donut)
  // rendered under each candidate palette, so a brand can be judged IN CONTEXT
  // rather than from hex. Pick one here, then it graduates into the master tokens.
  //
  // Structural colours (ink #1a1a1a, paper #f5f1e8) are fixed — we already love
  // them. Each candidate only varies: --brand, --on (text on brand), gain, loss,
  // and the categorical donut ramp.
  // ─────────────────────────────────────────────────────────────────────────

  const ALLOC = [21400, 16800, 12300, 9600, 7200, 5100];
  const ALLOC_LABELS = ['NVDA', 'AAPL', 'MSFT', 'SPY', 'Cash', 'Other'];
  const TOTAL = ALLOC.reduce((a, b) => a + b, 0);

  // Still green (Sprout equity) but pushed to the teal/lime edges so the brand
  // is its OWN hue — NOT the gain green. Gain is fixed across all four as a
  // quieter sea-green (#2e8b57) and loss a clay-red (#d2503a), so every row
  // shows brand vs. gain side by side and you can confirm they don't collide.
  const GAIN = '#2e8b57';
  const LOSS = '#d2503a';

  const CANDIDATES = [
    {
      key: 'jade', name: 'Jade teal',
      brand: '#0fb39a', on: '#1a1a1a', gain: GAIN, loss: LOSS,
      ramp: ['#0fb39a', '#3fc7b2', '#72d6c6', '#0a8576', '#bfe0d8', '#cbb78f'],
      note: 'Coolest of the four — cyan-leaning green. Reads fresh and clearly NOT the warm gain-green sitting next to it.'
    },
    {
      key: 'spring', name: 'Spring green',
      brand: '#1fcf8f', on: '#1a1a1a', gain: GAIN, loss: LOSS,
      ramp: ['#1fcf8f', '#52dca8', '#85e8c2', '#13a06d', '#bff0dd', '#cbb78f'],
      note: 'The midpoint — equal parts teal and grass. Brightest, liveliest “growing” feel; gain stays the quieter sea-green.'
    },
    {
      key: 'limegreen', name: 'Lime-green',
      brand: '#7cc62a', on: '#1a1a1a', gain: GAIN, loss: LOSS,
      ramp: ['#7cc62a', '#9ad356', '#b8e084', '#5c9417', '#d8ecb0', '#cbb78f'],
      note: 'Warm yellow-green — energetic, distinctive, still unmistakably a plant colour. Furthest from gain-green on the wheel.'
    },
    {
      key: 'brightlime', name: 'Bright lime',
      brand: '#a6d916', on: '#1a1a1a', gain: GAIN, loss: LOSS,
      ramp: ['#a6d916', '#bce24a', '#d2ec80', '#7fae0f', '#e6f3b0', '#cbb78f'],
      note: 'Limier and louder — chartreuse energy but still green, not neon. Most ownable / most “statement”.'
    }
  ];

  const R = 33.6, SW = 18, C = 2 * Math.PI * R;
  function arcs(ramp) {
    let acc = 0;
    return ALLOC.map((v, i) => {
      const frac = v / TOTAL;
      const seg = { len: frac * C, offset: -acc * C, color: ramp[i % ramp.length] };
      acc += frac;
      return seg;
    });
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

<div class="be">
  <header class="be-top">
    <div class="be-top-left">
      <span class="be-logo">sprout</span>
      <span class="be-tag">BRAND EXPLORER</span>
    </div>
    <a class="be-back" href="/design">← back to design master</a>
  </header>

  <main class="be-wrap">
    <h1 class="be-h1">Still green — just not <em>gain</em>-green.</h1>
    <p class="be-lead">
      Four brands across the <b>teal → spring → lime</b> edge of green. Ink + paper are fixed, and so
      is the semantic pair: <b style="color:#2e8b57">gain</b> is a quieter sea-green, <b style="color:#d2503a">loss</b>
      a clay-red — held constant in every row so you can see the brand sit <em>next to</em> gain and confirm
      they read as different colours. Pick one; then it graduates into the master and we tune the secondaries.
    </p>

    {#each CANDIDATES as c}
      <section
        class="be-cand"
        style="--brand:{c.brand}; --on:{c.on}; --gain:{c.gain}; --loss:{c.loss};"
      >
        <div class="be-cand-head">
          <div class="be-cand-name">
            <span class="be-chip" style="background:{c.brand}"></span>
            <h2>{c.name}</h2>
            <code>{c.brand}</code>
          </div>
          <p class="be-cand-note">{c.note}</p>
        </div>

        <div class="be-demo">
          <!-- hero block -->
          <div class="be-hero">
            <div class="be-hero-title">good evening, yazan</div>
            <div class="be-hero-sub">your garden is up <b>+6.4%</b> this month</div>
          </div>

          <!-- controls + nav -->
          <div class="be-stack">
            <button class="be-btn">Add trade</button>
            <div class="be-nav">
              <span class="be-navlink is-active">◆ Dashboard</span>
              <span class="be-navlink">↗ Investments</span>
            </div>
          </div>

          <!-- KPI + gain/loss -->
          <div class="be-kpi">
            <span class="be-kpi-label">Total P&amp;L</span>
            <span class="be-kpi-val be-gain">+$31,884</span>
            <div class="be-tags">
              <span class="be-tag-up">▲ +$4,820</span>
              <span class="be-tag-down">▼ −34.8%</span>
            </div>
          </div>

          <!-- donut + legend -->
          <div class="be-alloc">
            <svg class="be-donut" viewBox="0 0 100 100">
              <g transform="rotate(-90 50 50)">
                {#each arcs(c.ramp) as a}
                  <circle cx="50" cy="50" r={R} fill="none" stroke={a.color} stroke-width={SW}
                    stroke-dasharray="{a.len} {C - a.len}" stroke-dashoffset={a.offset} />
                {/each}
                <circle cx="50" cy="50" r={R + SW / 2} fill="none" stroke="#1a1a1a" stroke-width="2" />
                <circle cx="50" cy="50" r={R - SW / 2} fill="none" stroke="#1a1a1a" stroke-width="2" />
              </g>
            </svg>
            <div class="be-legend">
              {#each ALLOC_LABELS as label, i}
                <span class="be-legend-row">
                  <span class="be-legend-dot" style="background:{c.ramp[i % c.ramp.length]}"></span>{label}
                </span>
              {/each}
            </div>
          </div>
        </div>
      </section>
    {/each}

    <footer class="be-foot">
      <span>sprout · brand explorer · companion to <code>/design</code></span>
      <a class="be-back" href="/design">← back to design master</a>
    </footer>
  </main>
</div>

<style>
  .be {
    --ink: #1a1a1a;
    --paper: #f5f1e8;
    --surface: #ffffff;
    --bw: 2.5px;
    --sh: 4px 4px 0 var(--ink);
    --sh-pop: 7px 7px 0 var(--ink);
    --r: 6px;
    --sans: 'Space Grotesk', 'Helvetica Neue', Arial, system-ui, sans-serif;
    --mono: 'Space Mono', ui-monospace, Menlo, monospace;

    position: fixed; inset: 0; z-index: 50; overflow-y: auto;
    background: var(--paper); color: var(--ink);
    font-family: var(--sans); -webkit-font-smoothing: antialiased;
  }
  .be *, .be *::before, .be *::after { box-sizing: border-box; }

  .be-top {
    position: sticky; top: 0; z-index: 5;
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 14px 26px; background: var(--surface); border-bottom: var(--bw) solid var(--ink);
  }
  .be-top-left { display: flex; align-items: center; gap: 12px; }
  .be-logo { font-size: 22px; font-weight: 700; }
  .be-tag {
    font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .14em;
    padding: 3px 8px; background: var(--ink); color: var(--surface); border-radius: 3px;
  }
  .be-back { font-size: 13px; font-weight: 600; color: var(--ink); text-decoration: none; border-bottom: 2px solid var(--ink); }

  .be-wrap { max-width: 1040px; margin: 0 auto; padding: 36px 26px 90px; }
  .be-h1 { font-size: clamp(30px, 5vw, 48px); font-weight: 700; letter-spacing: -.02em; margin: 0; }
  .be-lead { font-size: 15px; line-height: 1.55; max-width: 64ch; margin: 14px 0 8px; }
  .be-lead b { font-weight: 700; }

  /* candidate row */
  .be-cand { margin-top: 40px; padding-top: 28px; border-top: var(--bw) solid var(--ink); }
  .be-cand-head { margin-bottom: 18px; }
  .be-cand-name { display: flex; align-items: center; gap: 12px; }
  .be-chip { width: 26px; height: 26px; border: var(--bw) solid var(--ink); border-radius: 5px; box-shadow: 2px 2px 0 var(--ink); }
  .be-cand-name h2 { font-size: 22px; font-weight: 700; margin: 0; }
  .be-cand-name code { font-family: var(--mono); font-size: 13px; color: #8a8478; }
  .be-cand-note { font-size: 14px; line-height: 1.5; max-width: 70ch; margin: 8px 0 0; }

  .be-demo { display: grid; grid-template-columns: 1.3fr 1fr 1fr 1.1fr; gap: 18px; align-items: stretch; }

  /* hero */
  .be-hero {
    background: var(--brand); color: var(--on);
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh-pop);
    padding: 20px; display: flex; flex-direction: column; justify-content: center; min-height: 150px;
  }
  .be-hero-title { font-size: 24px; font-weight: 700; letter-spacing: -.015em; line-height: 1.05; }
  .be-hero-sub {
    margin-top: 10px; font-size: 12px; font-weight: 600; align-self: flex-start;
    background: var(--surface); color: var(--ink); padding: 4px 10px;
    border: var(--bw) solid var(--ink); border-radius: 999px;
  }
  .be-hero-sub b { color: var(--gain); }

  /* controls */
  .be-stack { display: flex; flex-direction: column; gap: 12px; }
  .be-btn {
    font-family: var(--sans); font-size: 14px; font-weight: 700; cursor: pointer; text-align: left;
    padding: 12px 18px; background: var(--brand); color: var(--on);
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh);
  }
  .be-nav {
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); padding: 8px; display: flex; flex-direction: column; gap: 6px; flex: 1;
  }
  .be-navlink { font-size: 13px; font-weight: 600; padding: 9px 11px; border-radius: 5px; }
  .be-navlink.is-active { background: var(--brand); color: var(--on); }

  /* kpi */
  .be-kpi {
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); padding: 18px; display: flex; flex-direction: column; gap: 10px;
  }
  .be-kpi-label { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
  .be-kpi-val { font-family: var(--mono); font-size: 26px; font-weight: 700; line-height: 1; }
  .be-gain { color: var(--gain); }
  .be-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; }
  .be-tag-up, .be-tag-down {
    font-family: var(--mono); font-size: 11px; font-weight: 700; padding: 5px 9px;
    border: 2px solid var(--ink); border-radius: 5px; color: var(--ink);
  }
  .be-tag-up { background: var(--gain); }
  .be-tag-down { background: var(--loss); }

  /* alloc */
  .be-alloc {
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); padding: 16px; display: flex; align-items: center; gap: 14px;
  }
  .be-donut { width: 96px; height: 96px; flex: 0 0 auto; }
  .be-legend { display: flex; flex-direction: column; gap: 5px; font-size: 12px; font-weight: 600; }
  .be-legend-row { display: flex; align-items: center; gap: 8px; }
  .be-legend-dot { width: 12px; height: 12px; border: 2px solid var(--ink); border-radius: 3px; }

  .be-foot {
    margin-top: 60px; padding-top: 22px; border-top: var(--bw) solid var(--ink);
    display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center;
    font-family: var(--mono); font-size: 12px; color: #8a8478;
  }
  .be-foot code { background: var(--ink); color: var(--surface); padding: 2px 6px; border-radius: 3px; }

  @media (max-width: 900px) {
    .be-demo { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 560px) {
    .be-demo { grid-template-columns: 1fr; }
  }
</style>

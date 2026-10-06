<script>
  // Sprout · design master. Tokens/patterns at the top, real live components
  // below (pulled from the actual dashboard payload) — edit widgets here.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { theme, toggleTheme } from '$lib/theme.js';
  import { moves, portfolioDayMove, allTimeReturn, cardToHolding } from '$lib/stores.js';
  import RingGauge from '$lib/components/RingGauge.svelte';
  import BalanceCard from '$lib/components/BalanceCard.svelte';
  import PnlCard from '$lib/components/PnlCard.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import TradeTicket from '$lib/components/TradeTicket.svelte';
  import EarningsCard from '$lib/components/EarningsCard.svelte';
  import MarketPulse from '$lib/components/MarketPulse.svelte';
  import DividendRing from '$lib/components/DividendRing.svelte';
  import AllocationRing from '$lib/components/AllocationRing.svelte';
  import DashboardStage from '$lib/components/DashboardStage.svelte';
  import StockPanel from '$lib/components/StockPanel.svelte';
  import ActivityLog from '$lib/components/ActivityLog.svelte';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import TickerBadge from '$lib/components/TickerBadge.svelte';

  let d = $state(null);
  let trades = $state([]);
  let txns = $state([]);
  let realized = $state([]);
  let closed = $state([]);

  async function refresh() {
    try { d = await api.dashboard(); } catch { /* stays null — sections show their own empty state */ }
  }
  onMount(() => {
    refresh();
    Promise.all([api.trades(), api.transactions(), api.realized(), api.closed()])
      .then(([t, x, r, c]) => { trades = t; txns = x; realized = r; closed = c; })
      .catch(() => {});
  });

  const dayMove = $derived(d ? portfolioDayMove(d.cards, $moves) : { gain: null, pct: null });
  const allTime = $derived(allTimeReturn(d?.twr));
  const demoCard = $derived(d?.cards?.find((c) => !c.is_joker) ?? null);
  const demoTicker = $derived(demoCard?.ticker ?? 'AAPL');
  const demoHolding = $derived(demoCard ? cardToHolding(demoCard) : null);

  let pill = $state('1D');
  const PILLS = ['1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', '2Y', '5Y', '10Y', 'ALL'];
  let seg = $state('Value');

  const CORE = [
    { name: '--paper / --bg', usage: 'page + widget bg (same — border-only chrome)' },
    { name: '--ink', usage: 'text, borders, selected state, hover shadows' },
    { name: '--muted', usage: 'secondary text, idle controls, labels' },
    { name: '--hairline', usage: 'internal rules inside widgets, never between them' },
    { name: '--hover', usage: 'row/item hover wash where a border is too loud' },
  ];
  const ACCENTS = [
    { name: '--brand', v: '#0fb39a', usage: 'jade — portfolio line, brand moments' },
    { name: '--gain', v: '#00c060', usage: 'up moves only' },
    { name: '--loss', v: '#ff4d4d', usage: 'down moves only' },
    { name: '--gain-ink', v: '#3ddc8a', usage: 'gain text on a gain tint (pct pills) — lifted to pass AA' },
    { name: '--loss-ink', v: '#ff8585', usage: 'loss text on a loss tint (pct pills)' },
    { name: '--pink', v: '#ff90e8', usage: 'accent deck — rings, rare highlights' },
    { name: '--yellow', v: '#ffc900', usage: 'accent deck — cash panel, hold rating' },
    { name: '--blue', v: '#5b8def', usage: 'accent deck' },
    { name: '--purple', v: '#c994e8', usage: 'accent deck' },
    { name: '--coral', v: '#ff6e5e', usage: 'accent deck' },
  ];

  const RING_DEMO = [
    { key: 'a', color: '#0fb39a', value: 42, tag: 'NVDA', hero: '42.0', per: '%', sub: 'Demo segment' },
    { key: 'b', color: '#ff90e8', value: 28, tag: 'AAPL', hero: '28.0', per: '%', sub: 'Demo segment' },
    { key: 'c', color: '#ffc900', value: 18, tag: 'GOOG', hero: '18.0', per: '%', sub: 'Demo segment' },
    { key: 'd', color: '#8a8478', value: 12, tag: 'Other', hero: '12.0', per: '%', sub: 'Demo segment' },
  ];

  const JUMP = [
    ['principles', 'Principles'], ['tokens', 'Tokens'], ['type', 'Type'], ['buttons', 'Buttons'],
    ['charts', 'Charts'], ['loading', 'Loading'], ['ring', 'Ring'], ['rings-live', 'Live rings'], ['stage', 'Stage'], ['cards', 'Rail cards'],
    ['sidebar', 'Sidebar'], ['stock', 'Stock view'], ['log', 'Log'], ['mobile', 'Mobile'],
  ];

  const SPARK_DEMO = [219, 217, 216, 214, 208, 213, 209, 228, 217, 221, 217, 224, 228, 230, 225, 223, 218, 218, 211, 212, 214, 219];
</script>

<div class="dm">
  <header class="dm-head">
    <div>
      <h1 class="dm-title">sprout design</h1>
      <p class="dm-sub">The law. Change it here first.</p>
    </div>
    <button class="btn btn-line" onclick={toggleTheme}>Switch to {$theme === 'dark' ? 'light' : 'dark'}</button>
  </header>

  <nav class="dm-jump">
    {#each JUMP as [id, label] (id)}
      <a href="#{id}" class="btn btn-sm">{label}</a>
    {/each}
  </nav>

  <!-- ── principles ── -->
  <section class="w dm-sec" id="principles">
    <div class="w-h">Principles</div>
    <ol class="dm-principles">
      <li><b>Border-only chrome.</b> Widget bg = page bg; a 1px ink border is the only separation. No fills, no resting shadows.</li>
      <li><b>One pill.</b> Text idle → 1px ink outline hover → solid ink when selected/pressed. No other button shapes.</li>
      <li><b>Ink inversion is the selected state.</b> Active nav, picked range, pressed row — nothing else signals selection.</li>
      <li><b>Color is data.</b> Gain/loss for moves, jade for the portfolio, the accent deck for rings. Chrome is never colored.</li>
      <li><b>Strict grid.</b> 4 columns, 16px gaps. Bare (border-less) widgets allowed for rings, centred figures, and a data list paired with a bare widget (12-month forecast beside the ratings ring).</li>
      <li><b>Motion stays restrained.</b> 0.12s transitions, staggered ring fade-ins. No sweeps, no glows, no parallax.</li>
    </ol>
  </section>

  <!-- ── tokens ── -->
  <section class="w dm-sec" id="tokens">
    <div class="w-h">Core tokens (theme-dependent, flip above)</div>
    <div class="dm-rows">
      {#each CORE as t (t.name)}
        <div class="dm-row">
          <span class="dm-chip" style="background:var({t.name.split(' ')[0]})"></span>
          <code class="dm-code">{t.name}</code>
          <span class="dm-usage">{t.usage}</span>
        </div>
      {/each}
    </div>
    <div class="w-h dm-gap">Accent tokens (gain/loss darken on light paper)</div>
    <div class="dm-rows">
      {#each ACCENTS as t (t.name)}
        <div class="dm-row">
          <span class="dm-chip" style="background:{t.v}"></span>
          <code class="dm-code">{t.name}</code>
          <span class="dm-usage">{t.usage}</span>
        </div>
      {/each}
    </div>
    <div class="w-h dm-gap">Form tokens</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">--bw: 1px</code><span class="dm-usage">every border — widgets, pills, hairlines</span></div>
      <div class="dm-row"><code class="dm-code">--r: 4px</code><span class="dm-usage">widget corners, inputs (search strip included), drop zones; buttons are full pills (999px)</span></div>
      <div class="dm-row"><code class="dm-code">--sh: none</code><span class="dm-usage">nothing casts a shadow at rest</span></div>
      <div class="dm-row"><code class="dm-code">--sh-pop: 4px 4px 0 ink</code><span class="dm-usage">interactive cards on hover, and a row held mid-drag</span></div>
      <div class="dm-row"><code class="dm-code">--card-pad: 14px 16px</code><span class="dm-usage">rail card padding — set on the container</span></div>
    </div>
  </section>

  <!-- ── type ── -->
  <section class="w dm-sec" id="type">
    <div class="w-h">Type: Archivo, one family</div>
    <div class="dm-type">
      <p class="t-display">Archivo 700 — the voice</p>
      <p class="t-body">One face for everything. Figures are the same face with tabular digits (--num), so weight carries hierarchy, not a second family.</p>
    </div>
    <div class="w-h dm-gap">Card scale: four sizes, two weights, two inks</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">--fs-title 13 / 600</code><span class="dm-sample kpi-label" style="margin:0">Portfolio value</span><span class="dm-usage">ink, sentence case — the card's name</span></div>
      <div class="dm-row"><code class="dm-code">--fs-hero 24 / 600</code><span class="dm-sample kpi-value">$7,797.21</span><span class="dm-usage">num, ink — the total</span></div>
      <div class="dm-row"><code class="dm-code">--fs-body 12 / 500</code><span class="dm-sample"><span class="bal-k">Equities</span><span class="bal-v">$7,778.34</span></span><span class="dm-usage">key muted, value ink — the breakdown</span></div>
      <div class="dm-row"><code class="dm-code">--fs-meta 11 / 500</code><span class="dm-sample bal-day-when">today</span><span class="dm-usage">muted — when, where, source</span></div>
    </div>
    <div class="w-h dm-gap">Rules</div>
    <ol class="dm-principles">
      <li><b>Caps means ticker.</b> NVDA, SPY. Every other label is a sentence. Letter-spacing 0 outside badges.</li>
      <li><b>Headline is the total, rows are its breakdown.</b> Title → figure → key/value rows. Every KPI card.</li>
      <li><b>No dots.</b> Alignment separates. A muted span for the date. Slash only means "of" ($808 / $1,000).</li>
      <li><b>Minus is −.</b> U+2212 on every signed figure and axis, never the hyphen. Plus is always shown.</li>
      <li><b>Hairlines only between repeated rows.</b> Never between a headline and its own breakdown.</li>
      <li><b>One padding.</b> --card-pad — 14×16 in the rail, set on the container, never on the card.</li>
      <li><b>Pressable cards lift.</b> .pressable → --sh-pop on hover. The only card hover there is.</li>
    </ol>
    <div class="w-h dm-gap">Ticker badges</div>
    <div class="dm-btnrow">
      <TickerBadge sym="AAPL" size="sm" />
      <TickerBadge sym="NVDA" size="md" />
    </div>
    <p class="dm-note">sm / md — md carries a darker, saturated brick of the same hue straight down behind it.</p>
  </section>

  <!-- ── buttons ── -->
  <section class="w dm-sec" id="buttons">
    <div class="w-h">Buttons: one system, three states</div>
    <div class="dm-btnrow">
      <button class="btn">idle is text</button>
      <button class="btn" style="border-color:var(--ink)">hover = outline</button>
      <button class="btn on">selected = ink</button>
      <button class="btn btn-line">.btn-line</button>
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
    <div class="dm-btnrow">
      <button class="btn btn-sm btn-danger">.btn-danger</button>
      <span class="dm-usage">destructive confirm only (delete a list). Loss is the color of gone.</span>
    </div>
    <p class="dm-note">Cards are the one exception: hover lifts with --sh-pop instead of ink inversion.</p>
    <div class="w-h dm-gap">Icons</div>
    <p class="dm-usage">SVG on a 24 box, 1.8 stroke, round caps: profile, theme (sun/moon), search. No Unicode glyphs as icons (☀ ☾ ⌕ render per font). Icon buttons are 28px rings with the pill states: hairline, ink outline on hover, ink fill pressed.</p>
  </section>

  <!-- ── charts ── -->
  <section class="w dm-sec" id="charts">
    <div class="w-h">Charts: one palette, lib/chartTheme.js</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">chartPalette(theme)</code><span class="dm-usage">INK, GRID, MUTED, SPY, GAIN, LOSS per theme. Mirrors app.css by hand (canvas can't read vars).</span></div>
      <div class="dm-row"><code class="dm-code">baseChartOptions(pal)</code><span class="dm-usage">Archivo 11 axes in muted, no scale borders, no vertical grid, magnet crosshair (ink solid, grid dotted). Hosts override scaleMargins only.</span></div>
      <div class="dm-row"><code class="dm-code">areaStyle()</code><span class="dm-usage">BRAND line, fill 16% → 0. Portfolio value, portfolio return, stock price. One style.</span></div>
      <div class="dm-row"><code class="dm-code">compare</code><span class="dm-usage">accent-deck lines, Percentage scale rebased to the window start.</span></div>
      <div class="dm-row"><code class="dm-code">volume</code><span class="dm-usage">gain/loss at 42%.</span></div>
      <div class="dm-row"><code class="dm-code">prev close</code><span class="dm-usage">muted, dashed, axis label on.</span></div>
      <div class="dm-row"><code class="dm-code">fills</code><span class="dm-usage">buy = gain arrow below the bar, sell = loss arrow above. One per bar and side. Indicators → My trades.</span></div>
    </div>
    <div class="w-h dm-gap">Both charts are one shell: components/chart/*, lib/chartKit</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">.chart-widget</code><span class="dm-usage">440 tall, 14×16 pad (340 ≤900, 300 ≤700). Home and the stock view use the same box.</span></div>
      <div class="dm-row"><code class="dm-code">ChartFrame</code><span class="dm-usage">menus, readout, right control → compare chips → plot → ranges.</span></div>
      <div class="dm-row"><code class="dm-code">readout</code><span class="dm-usage">window move: 18/600 figure, 12/500 muted label, one secondary. Hover = start to that bar. Own line under 720px of chart.</span></div>
      <div class="dm-row"><code class="dm-code">ChartTip</code><span class="dm-usage">ink chip: value, date, fills. Drag = the span, oldest first either direction, gain/loss chip + band.</span></div>
      <div class="dm-row"><code class="dm-code">ChartPointer</code><span class="dm-usage">hover, click-drag measure, touch hold-scrub, horizontal-wheel pan.</span></div>
    </div>
  </section>

  <!-- ── loading + view changes ── -->
  <section class="w dm-sec" id="loading">
    <div class="w-h">Loading: skeletons, never placeholders</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">.skel</code><span class="dm-usage">breathing ink-10% bar. The card chrome and layout stay real; only unknown content becomes a bar. Text we already know stays text.</span></div>
      <div class="dm-row"><code class="dm-code">.skel-t</code><span class="dm-usage">a text line: one line box tall (1lh). Put it inside the real text's class so the row keeps its height.</span></div>
      <div class="dm-row"><code class="dm-code">charts</code><span class="dm-usage">one block over the plot. Never a line shape; it reads as a price.</span></div>
      <div class="dm-row"><code class="dm-code">no fake data</code><span class="dm-usage">unknown numbers are bars, not zeros or mocks. Mocks only when a fetch fails ("Demo data").</span></div>
      <div class="dm-row"><code class="dm-code">.arrive</code><span class="dm-usage">content that lands after a skeleton fades in, 220ms opacity. Nothing slides. A cache hit just appears.</span></div>
    </div>
    <div class="w-h dm-gap">View changes</div>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">swap in place</code><span class="dm-usage">stage views change with no enter animation.</span></div>
      <div class="dm-row"><code class="dm-code">portfolio stays mounted</code><span class="dm-usage">under the stock view and search. Back is instant and keeps range, metric, compares.</span></div>
      <div class="dm-row"><code class="dm-code">scroll</code><span class="dm-usage">a stock opens at the top. Back restores where the portfolio was.</span></div>
      <div class="dm-row"><code class="dm-code">stockCache</code><span class="dm-usage">5 min shared cache; peek() paints the first frame, over 30s old refetches in place. use:prefetch warms a ticker after a 120ms hover.</span></div>
    </div>
  </section>

  <!-- ── ring primitive ── -->
  <section class="w dm-sec" id="ring">
    <div class="w-h">RingGauge, the only donut</div>
    <div class="dm-ringrow">
      <div class="dm-ringcell">
        <RingGauge segments={RING_DEMO} idle={{ tag: 'Demo', hero: '100', per: '%', sub: 'Hover a segment' }} />
      </div>
      <p class="dm-usage">Rounded annular sectors, 3° gaps, faint track, hover-swaps the core, staggered fade-in.
        Backs dividends, allocation, analyst ratings. Never draw a donut another way.</p>
    </div>
  </section>

  <!-- ── dividend / allocation rings, live ── -->
  <section class="dm-live" id="rings-live">
    <div class="dm-label">Dividend and allocation rings</div>
    <div class="dm-ring2">
      <div class="dm-ring2-cell"><DividendRing data={d?.dividends ?? null} holdings={d?.cards ?? []} /></div>
      <div class="dm-ring2-cell"><AllocationRing holdings={(d?.cards ?? []).filter((c) => !c.is_joker)} /></div>
    </div>
  </section>

  <!-- ── stage: portfolio chart + strip ── -->
  <section class="dm-live" id="stage">
    <div class="dm-label">Stage: Drivers title card over the portfolio chart</div>
    {#if d}
      <DashboardStage equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested} drivers={d.drivers}
        total={d.kpis.portfolio_value} dayGain={dayMove.gain} dayPct={dayMove.pct} />
    {:else}
      <p class="dm-usage">Loading…</p>
    {/if}
    <p class="dm-note">Search is one .strip everywhere: the stage, the phone home, the Log filter, the ⌘K modal on other routes. An input, so an --r box with an ink border, not a pill. Results are the shared .ss-* rows with md badges.</p>
  </section>

  <!-- ── rail cards, live ── -->
  <section class="dm-live" id="cards">
    <div class="dm-label">Rail cards</div>
    <div class="dm-cardgrid">
      {#if d}
        <div class="dm-duo">
          <BalanceCard total={d.kpis.portfolio_value} equities={d.kpis.equities}
            dayGain={dayMove.gain} dayPct={dayMove.pct} ret={allTime.ret} vsSpy={allTime.vsSpy} />
          <PnlCard total={d.kpis.total_pnl} realized={d.kpis.realized_pnl} unrealized={d.kpis.unrealized_pnl} />
        </div>
        <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
          goalLabel="Monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target} onSaved={refresh} />
      {/if}
      <TradeTicket onSaved={refresh} />
      <EarningsCard />
      <MarketPulse />
    </div>
    <p class="dm-note">TradeTicket and CashGoalCard write real rows (/api/trades, /api/transactions).
      Their rising entry panels are paper/ink now, not a solid yellow/green/red sheet — border-only
      chrome like every other widget, a top hairline for the seam. Deposit/Withdraw and Buy/Sell
      are the one deliberate spot color is semantic instead of chrome (gain = deposit/buy, loss =
      withdraw/sell), carried by the toggle pill alone; save is a plain .btn. Amount/ticker/shares/
      date/price are each their own --r-radius field — no more fused segmented bar, no fixed hex,
      no mono. The trade token is the coin's sibling: same darker edge (the face mixed 60% to black,
      like the md badge brick), one glint, and the shine sweep on card hover.</p>
  </section>

  <!-- ── sidebar: lists + drag and drop (the live one is on the left) ── -->
  <section class="w dm-sec" id="sidebar">
    <div class="w-h">Sidebar</div>
    <p class="dm-usage">Holdings, then the user's lists. The live rail is on the left of this page.</p>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">order</code><span class="dm-usage">Holdings stay heaviest first and never reorder. Lists keep the user's order, rows and lists alike.</span></div>
      <div class="dm-row"><code class="dm-code">head</code><span class="dm-usage">name 13/600, count meta muted, chevron hanging in the gutter so the name sits on the badge edge. Rename and delete show on hover (ActivityLog's row actions); delete confirms in place with .btn-danger.</span></div>
      <div class="dm-row"><code class="dm-code">row</code><span class="dm-usage">badge over value and weight (holdings) or name (lists), month sparkline, price over the D/W/M pill. Same row in every section.</span></div>
      <div class="dm-row"><code class="dm-code">drag</code><span class="dm-usage">press and move 5px. A holding copies into a list; a list row moves (within or across lists); a list head reorders the lists. Esc cancels. Touch: hold 380ms, then drag. Moving first is a scroll, so the rail still scrolls on a tablet. One engine for rail and phone: lib/listDrag.svelte.js.</span></div>
      <div class="dm-row"><code class="dm-code">preview</code><span class="dm-usage">live: rows slide apart (160ms flip), a dashed ink slot marks the landing, the lifted copy holds the pressable-card lift. A copied holding keeps its place, outlined dashed.</span></div>
      <div class="dm-row"><code class="dm-code">targets</code><span class="dm-usage">no dead space: a gap belongs to the list below it, anything past the last list appends to it, a collapsed list takes the drop at its end. The rail scrolls while the cursor rides its edge.</span></div>
      <div class="dm-row"><code class="dm-code">zones</code><span class="dm-usage">dashed hairline tiles under the rail. + New list at rest; New list and Remove while a list row is dragged. Over: solid ink, Remove in loss. The lift shrinks to its badge so the label stays readable.</span></div>
      <div class="dm-row"><code class="dm-code">data</code><span class="dm-usage">/api/lists. Every drag PUTs the whole layout and swaps in the hydrated reply. Collapsed sections are per viewer (localStorage).</span></div>
    </div>
    <div class="dm-rail-demo" aria-hidden="true">
      <div class="dm-rd-col">
        <span class="dm-usage">landing slot, lifted row</span>
        <div class="dm-rd-slot"></div>
        <div class="dm-rd-lift"><TickerBadge sym="MU" /><span class="dm-rd-px">$1,070.48</span></div>
      </div>
      <div class="dm-rd-col">
        <span class="dm-usage">zones while dragging</span>
        <div class="dm-rd-zones">
          <span class="dm-rd-zone dm-rd-over">New list</span>
          <span class="dm-rd-zone">Remove</span>
        </div>
        <div class="dm-rd-zones"><span class="dm-rd-zone">+ New list</span></div>
      </div>
    </div>
  </section>

  <!-- ── stock view, live ── -->
  <section class="dm-live" id="stock">
    <div class="dm-label">Stock view</div>
    <StockPanel ticker={demoTicker} name={demoCard?.company_name ?? demoTicker} holding={demoHolding} showClose={false} />
    <p class="dm-note">12-month forecast: bare, beside the bare ratings ring. Headline is the average target (hero + pct-pill vs now), then low to high as a range on a price axis that always spans today: below now is loss, above is gain, now is a 1px ink tick labelled above (the label slides from left- to right-aligned with its x), the average is an ink dot ringed in paper. Low and High sit at the ends with their pills. Replaced the three ink bars.</p>
    <p class="dm-note">Non-held tickers carry the list picker (was + Watch): the pill names the list, or the count, and goes ink when the ticker is in any. The popover is ProfileMenu's panel; checked lists are ink-filled boxes.</p>
  </section>

  <!-- ── activity log, live ── -->
  <section class="dm-live" id="log">
    <div class="dm-label">Activity log</div>
    <ActivityLog {trades} {txns} {realized} {closed} />
    <p class="dm-note">Previously held is one row per ticker sold out of entirely, newest exit first: return (pct-pill) over everything bought, P&amp;L trailing, the same figures the stock view shows. A row is a button; ink hairline on hover. Phone drops avg buy / sell.</p>
  </section>

  <!-- ── mobile ── -->
  <section class="w dm-sec" id="mobile">
    <div class="w-h">Mobile</div>
    <p class="dm-usage">Same components, three panes: Home, Holdings, Log. Search is the strip on Home, not a tab.
      The stock view is a full-screen sheet. Nothing here has its own type — it uses the four sizes above.</p>
    <div class="dm-rows">
      <div class="dm-row"><code class="dm-code">dock</code><span class="dm-usage">56px bar, edge-to-edge and flush to the bottom — no capsule, no margins, just a hairline top edge. Icon over label (21 / 10.5·600); the active tab gets a 52×30 pill (11% ink wash, not a solid block) that hugs the icon alone, slides between tabs, and pops in with a small liquid overshoot each time it lands. Swipe anywhere in a pane to move a tab over.</span></div>
      <div class="dm-row"><code class="dm-code">header</code><span class="dm-usage">greeting 28/700 lowercase, 18px under the status bar; theme + profile as 30px rings on the right, the profile a 24-box person icon.</span></div>
      <div class="dm-row"><code class="dm-code">strip</code><span class="dm-usage">the desktop .strip. Idle = button; live = input + Cancel, results take the pane over.</span></div>
      <div class="dm-row"><code class="dm-code">rows</code><span class="dm-usage">48–56px touch rows, hairline between, press tint. Badge, name (body muted), figure (num).</span></div>
      <div class="dm-row"><code class="dm-code">lists</code><span class="dm-usage">Holdings pane, under the holdings: the sidebar's lists and drag rules. Hold a row or a list name to lift it; a swipe still scrolls or pages. Mid-drag, New list and Remove cover the dock and the pane scrolls at its edges. Tap a name to fold it. New list asks for the name first, since iOS only raises the keyboard inside the tap.</span></div>
      <div class="dm-row"><code class="dm-code">swipe</code><span class="dm-usage">SwipeRow. Swipe a row left for its actions, iOS style: Log trades and transactions get Edit and Delete, list rows Remove, list names Rename and Delete. Neutral action first (16% ink), destructive last in loss. Only left swipes are claimed, so a right swipe still pages back; rows without actions (holdings) page both ways. One row open at a time; the next touch anywhere shuts it and does nothing else. Deletes still confirm in place, list-row Remove doesn't. Hover devices keep the hover icons instead.</span></div>
      <div class="dm-row"><code class="dm-code">scroll</code><span class="dm-usage">no overscroll-behavior on html/body — it kills the iOS bounce. The shell clips x.</span></div>
    </div>
    <div class="dm-mobile-demo">
      <div class="dm-dock" aria-hidden="true">
        <span class="dm-dock-pill"></span>
        <span class="dm-dock-tab on">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 11 12 4 20 11 V19 A2 2 0 0 1 18 21 H6 A2 2 0 0 1 4 19 Z" /><path d="M9.5 21 V14 H14.5 V21" />
          </svg>
          <span>Home</span>
        </span>
        <span class="dm-dock-tab">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.21 15.89A10 10 0 1 1 8 2.83" /><path d="M22 12A10 10 0 0 0 12 2v10Z" />
          </svg>
          <span>Holdings</span>
        </span>
        <span class="dm-dock-tab">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 18 V6 M4.5 9.5 8 6 11.5 9.5" /><path d="M16 6 V18 M12.5 14.5 16 18 19.5 14.5" />
          </svg>
          <span>Log</span>
        </span>
      </div>
      <div class="dm-glance">
        <div class="dm-glance-head"><span class="w-h">Holdings, past month</span><span class="btn btn-sm btn-quiet">See all</span></div>
        <div class="dm-glance-row">
          <TickerBadge sym="NVDA" />
          <span class="dm-glance-name">NVIDIA Corporation</span>
          <span class="dm-glance-move down"><Sparkline values={SPARK_DEMO} /><span class="dm-glance-pct">−0.07%</span></span>
        </div>
        <div class="dm-glance-row">
          <TickerBadge sym="AAPL" />
          <span class="dm-glance-name">Apple Inc.</span>
          <span class="dm-glance-move up"><Sparkline values={[...SPARK_DEMO].reverse()} /><span class="dm-glance-pct">+8.70%</span></span>
        </div>
        <p class="dm-usage">Top 5 by weight, 21 closes + spot from /api/momentum. Sparkline = one 1.5 path in the row's gain/loss ink. No axes.</p>
      </div>
    </div>
  </section>

  <!-- ── widget anatomy ── -->
  <section class="w dm-sec">
    <div class="w-h">Widget anatomy</div>
    <div class="dm-widgets">
      <div class="w dm-demo-w">
        <div class="w-h">Bordered widget</div>
        <p class="dm-usage">1px ink border, bg = page, 4px corners.</p>
      </div>
      <div class="dm-demo-w dm-bare">
        <div class="w-h">Bare widget</div>
        <p class="dm-usage">No border — rings, centred hero figures, or a data list paired with one.</p>
      </div>
    </div>
  </section>
</div>

<style>
  /* sidebar section: the drag states, static (they only exist mid-drag) */
  .dm-rail-demo { display: grid; grid-template-columns: repeat(2, minmax(0, 240px)); gap: 24px; margin-top: 4px; }
  .dm-rd-col { display: flex; flex-direction: column; gap: 8px; }
  .dm-rd-slot { height: 44px; border: var(--bw) dashed var(--ink); border-radius: var(--r); background: var(--hover); }
  .dm-rd-lift { display: flex; align-items: center; justify-content: space-between; padding: 10px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh-pop); }
  .dm-rd-px { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; font-variant-numeric: tabular-nums; }
  .dm-rd-zones { display: flex; gap: 8px; }
  .dm-rd-zone { flex: 1; min-height: 34px; display: grid; place-items: center; border: var(--bw) dashed var(--muted);
    border-radius: var(--r); font-size: var(--fs-body); font-weight: 500; color: var(--ink); }
  .dm-rd-over { border-style: solid; border-color: var(--ink); background: var(--hover); }

  /* mobile section: a static dock (the real one is position: fixed) and a glance row */
  .dm-mobile-demo { display: grid; grid-template-columns: 343px minmax(0, 1fr); gap: 24px; align-items: start; margin-top: 4px; }
  .dm-dock { position: relative; height: 56px; box-sizing: border-box; display: flex;
    border-top: var(--bw) solid var(--hairline); background: var(--surface); }
  .dm-dock-pill { position: absolute; top: 6px; left: calc((100% / 3 - 52px) / 2); width: 52px; height: 30px;
    background: color-mix(in srgb, var(--ink) 11%, transparent); border-radius: 999px; }
  .dm-dock-tab { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 3px;
    color: var(--muted); font-size: 10.5px; font-weight: 600; line-height: 1; }
  .dm-dock-tab.on { color: var(--ink); }
  .dm-dock-tab.on svg { color: var(--ink); }
  .dm-dock-tab svg { width: 21px; height: 21px; display: block; color: var(--muted); }
  .dm-glance { display: flex; flex-direction: column; }
  .dm-glance-head { display: flex; align-items: center; justify-content: space-between; padding: 4px 0 2px; }
  .dm-glance-row { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; min-height: 48px; padding: 8px 0;
    border-bottom: var(--bw) solid var(--hairline); }
  .dm-glance-name { min-width: 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dm-glance-move { display: flex; align-items: center; gap: 10px; }
  .dm-glance-pct { min-width: 64px; text-align: right; font-family: var(--num); font-size: var(--fs-body); font-weight: 500; font-variant-numeric: tabular-nums; }
  .dm-glance-move.up { color: var(--gain-ink); }
  .dm-glance-move.down { color: var(--loss-ink); }
  @media (max-width: 760px) { .dm-mobile-demo { grid-template-columns: 1fr; } }

  .dm { max-width: 1120px; margin: 0 auto; padding: 28px 28px 80px; display: flex; flex-direction: column; gap: 16px; }
  .dm-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; padding: 8px 2px 10px; }
  .dm-title { margin: 0; font-family: var(--sans); font-size: 34px; font-weight: 800; letter-spacing: -.02em; text-transform: lowercase; }
  .dm-sub { margin: 4px 0 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  .dm-jump { display: flex; flex-wrap: wrap; gap: 6px; padding-bottom: 4px; border-bottom: var(--bw) solid var(--hairline); }

  .w { background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); }
  .dm-sec { padding: 14px 18px 16px; display: flex; flex-direction: column; gap: 10px; }
  .w-h { font-size: var(--fs-title); font-weight: 600; line-height: 1.2; color: var(--ink); }
  .dm-gap { margin-top: 8px; }

  .dm-principles { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 8px;
    font-size: 13px; line-height: 1.55; }
  .dm-principles b { font-weight: 700; }

  .dm-rows { display: flex; flex-direction: column; }
  .dm-row { display: flex; align-items: center; gap: 12px; padding: 7px 0;
    border-bottom: var(--bw) solid var(--hairline); }
  .dm-row:last-child { border-bottom: 0; }
  .dm-chip { width: 22px; height: 22px; flex: 0 0 auto; border-radius: 6px; border: var(--bw) solid var(--ink); }
  .dm-code { font-family: var(--mono); font-size: 12px; font-weight: 600; min-width: 170px; }
  .dm-usage { font-size: var(--fs-body); font-weight: 500; color: var(--muted); line-height: 1.5; margin: 0; }

  .dm-type { display: flex; flex-direction: column; gap: 8px; }
  .t-display { margin: 0; font-family: var(--sans); font-size: 30px; font-weight: 700; letter-spacing: -.02em; }
  .t-body { margin: 0; font-family: var(--sans); font-size: 14px; line-height: 1.6; }
  .dm-note { margin: 2px 0 0; font-size: var(--fs-meta); font-weight: 500; color: var(--muted); line-height: 1.6; }

  .dm-btnrow { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
  .dm-divider { width: 1px; height: 20px; background: var(--hairline); margin: 0 8px; }

  .dm-widgets { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .dm-demo-w { padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
  .dm-bare { border: 0; background: transparent; }

  .dm-ringrow { display: grid; grid-template-columns: 200px 1fr; gap: 20px; align-items: center; }
  .dm-ringcell { height: 180px; }

  /* ── live sections: no outer card — the real widgets carry their own chrome ── */
  .dm-live { display: flex; flex-direction: column; gap: 10px; }
  .dm-label { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }

  .dm-ring2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .dm-ring2-cell { height: 190px; }

  /* same width + padding as the dashboard rail, so the gallery is the real thing */
  .dm-cardgrid { --card-pad: 14px 16px; display: grid; grid-template-columns: repeat(auto-fill, minmax(312px, 1fr)); gap: 16px; align-items: start; }
  .dm-duo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
  .dm-duo > :global(.glass-card) { min-height: 152px; }
  .dm-sample { min-width: 150px; display: inline-flex; align-items: baseline; gap: 6px; }

  @media (max-width: 700px) {
    .dm-widgets, .dm-ringrow, .dm-ring2, .dm-cardgrid, .dm-rail-demo { grid-template-columns: 1fr; }
  }
</style>

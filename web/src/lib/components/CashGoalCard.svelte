<script>
  // Combined Cash + monthly-goal tile (1×1, in the dashboard rail). Cash is the headline
  // figure; the savings goal rides underneath as a slim progress line — denser than
  // two separate single-figure cards, which read half-empty side by side.
  // A little gold coin sits top-right (deposit affordance). Clicking the tile floats a
  // yellow panel up from the bottom (rises to 60% of the card) — feature in progress.
  import { formatValue } from '$lib/format.js';
  import { api } from '$lib/api.js';

  const today = () => new Date().toISOString().slice(0, 10);

  let { cash, portfolioValue, goalLabel = 'Monthly goal', goalCurrent, goalTarget, onSaved } = $props();

  const cashPct = $derived(portfolioValue ? (cash / portfolioValue) * 100 : null);
  const goalPct = $derived(goalTarget ? Math.min(100, (goalCurrent / goalTarget) * 100) : 0);
  const compact = (v) => v == null ? '—' : '$' + Math.round(v).toLocaleString('en-US');

  // Click the tile to toggle the rising entry panel.
  let open = $state(false);
  const toggle = () => (open = !open);

  // Transaction entry — this panel replaces the log tab's txn form.
  // + = deposit, − = withdrawal (maps to txn_type Deposit/Withdrawal).
  let sign = $state('+');
  let amount = $state('');
  let date = $state(today());
  let saving = $state(false);
  let saveError = $state(null);
  let amountEl;

  const flipSign = () => (sign = sign === '+' ? '-' : '+');
  const amountValid = $derived(Number(amount) > 0);

  async function save() {
    if (saving) return;
    if (!amountValid) { saveError = 'Enter a valid amount'; return; } // type error → pale-red bar
    saving = true;
    saveError = null;
    try {
      const res = await api.addTransaction({
        txn_date: date,
        txn_type: sign === '+' ? 'Deposit' : 'Withdrawal',
        amount: Number(amount)
      });
      if (res?.ok) {
        amount = '';
        onSaved?.();
      } else {
        saveError = res?.error || 'Save failed';
      }
    } catch {
      saveError = 'Save failed';
    } finally {
      saving = false;
    }
  }

  // Focus the amount field when the panel opens.
  $effect(() => { if (open && amountEl) amountEl.focus(); });
</script>

<div class="glass-card pressable cashgoal-card" class:open role="button" tabindex="0" aria-expanded={open}
  onclick={toggle}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}>
  <!-- Coin token, heads-on (flat, app-style): a perfect-circle gold face with an ink
       outline, sitting on a darker-gold bottom edge for thickness. Inner rim ring,
       a bold ink "$" struck in the centre, one specular glint top-left. On card hover
       a diagonal light streak sweeps the face, clipped to the circle. -->
  <svg class="cg-coin" viewBox="0 0 120 132" width="32" height="35" aria-hidden="true">
    <defs>
      <clipPath id="cg-face-clip"><circle cx="60" cy="60" r="52" /></clipPath>
      <linearGradient id="cg-shine-grad" x1="0" y1="0" x2="1" y2="0" gradientTransform="rotate(25 0.5 0.5)">
        <stop offset="0.40" stop-color="#fff" stop-opacity="0" />
        <stop offset="0.50" stop-color="#fff" stop-opacity="0.55" />
        <stop offset="0.60" stop-color="#fff" stop-opacity="0" />
      </linearGradient>
    </defs>
    <!-- thickness: darker-gold edge, offset straight down, ink-outlined -->
    <circle cx="60" cy="70" r="52" fill="#b07d14" stroke="#1a1a1a" stroke-width="6" />
    <!-- gold face -->
    <circle cx="60" cy="60" r="52" fill="#FFC900" stroke="#1a1a1a" stroke-width="6" />
    <!-- inner rim ring -->
    <circle cx="60" cy="60" r="40" fill="none" stroke="#D78604" stroke-width="5" />
    <!-- struck "$" -->
    <text x="60" y="62" text-anchor="middle" dominant-baseline="central"
          font-family="ui-monospace, monospace" font-size="46" font-weight="700" fill="#1a1a1a">$</text>
    <!-- specular glint, top-left of the face -->
    <g fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round">
      <path d="M30 38 Q38 28 50 24" />
    </g>
    <!-- shine streak, clipped to the face; swept across by .cg-coin-shine on card hover -->
    <g clip-path="url(#cg-face-clip)">
      <rect class="cg-coin-shine" x="-20" y="-20" width="160" height="160" fill="url(#cg-shine-grad)" />
    </g>
  </svg>

  <!-- persistent "this opens" badge, half-overlapping the coin's corner. Quiet
       hairline at rest; fills ink on hover and spins into an × once the panel
       is open, so the same mark reads as both "add" and "close". -->
  <span class="cg-add" aria-hidden="true"></span>

  <div class="cg-cash">
    <div class="kpi-label">Cash</div>
    <div class="kpi-value">{formatValue(cash, 'money')}</div>
    {#if cashPct != null}
      <div class="kpi-subtitle">{cashPct.toFixed(0)}% of portfolio</div>
    {/if}
  </div>

  <div class="cg-goal">
    <div class="bal-row cg-goal-row">
      <span class="bal-k">{goalLabel}</span>
      <span class="bal-v">{compact(goalCurrent)} / {compact(goalTarget)}</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:{goalPct}%"></div></div>
  </div>

  <!-- Rising entry panel: grows from 0 to its own natural content height when open
       (a CSS-grid 0fr→1fr track, not a fixed/percentage height — percentage heights
       on an absolutely-positioned child don't resolve against an auto-height card,
       which is what left a residual sliver showing even when "closed"). The sign
       toggle sits left; amount + date stack in a single column to its right (a 1×2
       field grid); save is a circle on the far right. Clicks/keys inside are stopped
       so interacting doesn't toggle the tile closed; inert when closed for a11y. -->
  <div class="cg-rise" inert={!open}
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}>
   <div class="cg-clip">
    <div class="cg-rise-inner">
    <div class="cg-body">
      <button type="button" class="cg-sign" class:pos={sign === '+'} class:neg={sign === '-'} onclick={flipSign}
        aria-label={sign === '+' ? 'Deposit — tap to switch to withdraw' : 'Withdraw — tap to switch to deposit'}>{sign === '+' ? 'Deposit' : 'Withdraw'}</button>
      <div class="cg-grid">
        <div class="cg-amount" class:invalid={saveError}>
          <span class="cg-dollar" aria-hidden="true">$</span>
          <input class="cg-amount-input" type="number" step="any" min="0" inputmode="decimal"
            placeholder="0.00" bind:value={amount} bind:this={amountEl}
            oninput={() => { saveError = null; }}
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
            aria-label="Amount in dollars" />
        </div>
        <input class="cg-date-input" type="date" bind:value={date} max={today()} aria-label="Transaction date" />
      </div>
      <button type="button" class="cg-save" onclick={save} disabled={saving}
        aria-label="Save transaction">✓</button>
    </div>
    {#if saveError}<div class="cg-save-err" role="alert">{saveError}</div>{/if}
    </div>
   </div>
  </div>
</div>

<style>
  .cashgoal-card { position: relative; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; overflow: hidden; }
  /* keep the cash figure clear of the coin in the corner */
  .cg-cash { padding-right: 34px; }

  .cg-coin { position: absolute; top: 12px; right: 12px; z-index: 1; overflow: visible;
    transition: transform .2s cubic-bezier(.34, 1.56, .5, 1); }
  .cashgoal-card:hover .cg-coin { transform: translateY(-2px); }

  /* quiet "+" affordance badge, half-overlapping the coin's bottom-right edge.
     The plus is drawn as two CSS bars (not text) so it sits dead-center
     regardless of font metrics; the whole badge spins 45° into an × on open. */
  .cg-add { position: absolute; top: 39px; right: 7px; z-index: 2; pointer-events: none;
    width: 17px; height: 17px; border-radius: 50%;
    background: var(--surface); border: 1.5px solid var(--hairline); color: var(--muted);
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease; }
  .cg-add::before, .cg-add::after { content: ''; position: absolute; top: 50%; left: 50%;
    background: currentColor; transform: translate(-50%, -50%); }
  .cg-add::before { width: 8px; height: 1.5px; }
  .cg-add::after { width: 1.5px; height: 8px; }
  .cashgoal-card:hover .cg-add { border-color: var(--ink); color: var(--ink); }
  .cashgoal-card.open .cg-add { background: var(--ink); border-color: var(--ink); color: var(--paper); transform: rotate(45deg); }

  /* diagonal shine swipe clipped to the coin face,
     triggered by hovering the card. transform-box: view-box so the % resolves in viewBox units. */
  .cg-coin-shine { transform-box: view-box; transform: translateX(-120%); transition: transform .6s ease; }
  .cashgoal-card:hover .cg-coin-shine { transform: translateX(120%); }

  .cg-goal-row { margin-bottom: 6px; }

  /* Cash entry panel: grows from the bottom to its own content height on click.
     A single-row CSS grid (0fr → 1fr) rather than a fixed/percentage height —
     .cashgoal-card is itself auto-height (sized by its content), and a percentage
     height on an absolutely-positioned child doesn't resolve against an auto-height
     containing block, which is what left a residual sliver showing even "closed". */
  .cg-rise {
    position: absolute; left: 0; right: 0; bottom: 0;
    display: grid; grid-template-rows: 0fr;
    z-index: 2; cursor: default;
    transition: grid-template-rows .45s cubic-bezier(.22, 1, .36, 1);
  }
  .cashgoal-card.open .cg-rise { grid-template-rows: 1fr; }
  /* the grid ITEM: bare — no padding/border of its own, so it has nothing to
     hold the 0fr track open (grid track auto-sizing floors at an item's padding
     + border regardless of min-height:0, which only zeros its content minimum —
     that residual floor was the sliver that never fully collapsed). */
  .cg-clip { min-height: 0; overflow: hidden; }
  /* the actual visual sheet — same paper/ink chrome as every other widget, no
     loud fill; a top hairline is the only seam. */
  .cg-rise-inner {
    background: var(--surface);
    border-top: var(--bw) solid var(--ink);
    border-radius: calc(var(--r) * 2) calc(var(--r) * 2) 0 0;
    display: flex; flex-direction: column; justify-content: center; gap: 6px;
    padding: 10px 12px;
  }
  /* the card's hover-lift (translate + --sh-pop) was fighting the panel's own
     height transition on click — it's an active edit surface once open, not a
     hover-preview target, so drop the lift for as long as it's open. */
  .cashgoal-card.open, .cashgoal-card.open:hover { transform: none; box-shadow: var(--sh); }

  /* Body: sign toggle (left, natural pill size) · a 1×2 field grid (amount over
     date, same width) · save (right, a plain circle) — both sit vertically
     centred against the taller grid, not stretched to match it. */
  .cg-body { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }
  .cg-sign { flex: 0 0 auto; padding: 7px 14px; box-sizing: border-box; border: 1.5px solid var(--hairline);
    border-radius: 999px; background: transparent; font-family: var(--sans); font-size: 11.5px;
    font-weight: 600; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .cg-sign.pos { border-color: var(--gain); color: var(--gain); }
  .cg-sign.neg { border-color: var(--loss); color: var(--loss); }
  .cg-sign.pos:active { background: color-mix(in srgb, var(--gain) 16%, transparent); }
  .cg-sign.neg:active { background: color-mix(in srgb, var(--loss) 16%, transparent); }
  .cg-save { flex: 0 0 30px; width: 30px; height: 30px; padding: 0; box-sizing: border-box;
    border-radius: 999px; background: transparent; font-size: 13px; cursor: pointer;
    border: 1.5px solid var(--hairline); color: var(--ink);
    display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, border-color .12s ease, color .12s ease; }
  .cg-save:hover { border-color: var(--ink); }
  .cg-save:active { background: var(--ink); color: var(--paper); }
  .cg-save:disabled { opacity: .4; cursor: default; }

  /* 1×2 grid: amount over date, sharing one column width — the mismatch (a
     flexible amount box next to a fixed, oversized date box) was the asymmetry. */
  .cg-grid { flex: 1 1 auto; min-width: 0; display: grid; grid-template-rows: 28px 28px; gap: 6px; }
  .cg-amount { box-sizing: border-box; min-width: 0; display: flex; align-items: center; gap: 3px; padding: 0 10px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); }
  /* type error on insert → the field turns pale red */
  .cg-amount.invalid { background: color-mix(in srgb, var(--loss) 12%, var(--surface)); border-color: var(--loss); }
  .cg-dollar { flex: 0 0 auto; color: var(--muted); font-family: var(--num); font-size: var(--fs-body); font-weight: 600; }
  .cg-amount-input { flex: 1 1 auto; min-width: 0; width: 100%; padding: 0; border: 0; outline: none; background: transparent;
    font-family: var(--num); font-size: var(--fs-body); font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums;
    -moz-appearance: textfield; appearance: textfield; }
  .cg-amount-input::placeholder { color: var(--muted); }
  .cg-amount-input::-webkit-outer-spin-button, .cg-amount-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  .cg-date-input { box-sizing: border-box; min-width: 0; width: 100%;
    padding: 0 10px; border: var(--bw) solid var(--ink); border-radius: var(--r); background: var(--surface);
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; color: var(--ink); cursor: pointer; }
  .cg-date-input::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .85; }

  .cg-save-err { flex: 0 0 auto; color: var(--loss); font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; text-align: center; }

  @media (prefers-reduced-motion: reduce) {
    .cg-coin { transition: none; }
    .cashgoal-card:hover .cg-coin { transform: none; }
    .cg-coin-shine { transition: none; }
    .cashgoal-card:hover .cg-coin-shine { transform: translateX(-120%); }
    .cg-rise { transition: none; }
    .cg-add { transition: none; }
  }
</style>

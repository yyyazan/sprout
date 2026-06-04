<script>
  // Combined Cash + monthly-goal tile (1×1, under the deck). Cash is the headline
  // figure; the savings goal rides underneath as a slim progress line — denser than
  // two separate single-figure cards, which read half-empty side by side.
  // A little gold coin sits top-right (deposit affordance). Clicking the tile floats a
  // yellow panel up from the bottom (rises to 60% of the card) — feature in progress.
  import { formatValue } from '$lib/format.js';
  import { api } from '$lib/api.js';

  const today = () => new Date().toISOString().slice(0, 10);

  let { cash, portfolioValue, goalLabel = 'monthly goal', goalCurrent, goalTarget, onSaved } = $props();

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

<div class="glass-card cashgoal-card" class:open role="button" tabindex="0" aria-expanded={open}
  onclick={toggle}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}>
  <!-- Designed coin token (flat, app-style): an ink-outlined gold face sitting on a darker-
       gold bottom edge that gives it thickness, with a darker-gold inner rim ring. On card
       hover a diagonal light streak (the same sweep as .portfolio-card's shine) crosses the
       face, clipped to the ellipse. overflow:visible (see .cg-coin) lets the edge spill past
       the viewBox bottom. -->
  <svg class="cg-coin" viewBox="0 0 231 183" width="36" height="29" aria-hidden="true">
    <defs>
      <clipPath id="cg-face-clip">
        <ellipse cx="115.347" cy="91.167" rx="122" ry="82" transform="rotate(26.1617 115.347 91.167)" />
      </clipPath>
      <linearGradient id="cg-shine-grad" x1="0" y1="0" x2="1" y2="0" gradientTransform="rotate(25 0.5 0.5)">
        <stop offset="0.40" stop-color="#fff" stop-opacity="0" />
        <stop offset="0.50" stop-color="#fff" stop-opacity="0.55" />
        <stop offset="0.60" stop-color="#fff" stop-opacity="0" />
      </linearGradient>
    </defs>
    <!-- coin thickness: darker-gold bottom edge, offset straight down, ink-outlined -->
    <ellipse cx="115.347" cy="91.167" rx="122" ry="82" transform="translate(0 12) rotate(26.1617 115.347 91.167)"
             fill="#b07d14" stroke="#1a1a1a" stroke-width="11" stroke-linejoin="round" />
    <!-- gold coin face, ink-outlined -->
    <ellipse cx="115.347" cy="91.167" rx="122" ry="82" transform="rotate(26.1617 115.347 91.167)"
             fill="#FFC900FF" stroke="#1a1a1a" stroke-width="11" stroke-linejoin="round" />
    <!-- inner rim ring on the face -->
    <ellipse cx="115.347" cy="91.167" rx="95" ry="63" transform="rotate(26.1617 115.347 91.167)"
             fill="none" stroke="#D78604FF" stroke-width="8" />
    <!-- stark specular glint: two parallel thin streaks (rounded rectangles), the upper one
         shorter, upper-left of the face and tilted along the coin's axis (light catch) -->
    <g transform="translate(0 9) rotate(26.1617 115.347 91.167)" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round">
      <path d="M52 78 L86 56" />
      <path d="M50 62 L72 48" />
    </g>
    <!-- shine streak, clipped to the face; swept across by .cg-coin-shine on card hover -->
    <g clip-path="url(#cg-face-clip)">
      <rect class="cg-coin-shine" x="-40" y="-40" width="311" height="263" fill="url(#cg-shine-grad)" />
    </g>
  </svg>

  <div class="cg-cash">
    <div class="kpi-label">Cash</div>
    <div class="kpi-value">{formatValue(cash, 'money')}</div>
    {#if cashPct != null}
      <div class="kpi-subtitle">{cashPct.toFixed(0)}% of portfolio</div>
    {/if}
  </div>

  <div class="cg-goal">
    <div class="cg-goal-head">
      <span class="cg-goal-label">{goalLabel}</span>
      <span class="cg-goal-fig">{compact(goalCurrent)} / {compact(goalTarget)} · {goalPct.toFixed(0)}%</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:{goalPct}%"></div></div>
  </div>

  <!-- Yellow entry panel: floats up from the bottom to 60% of the tile when open. Holds the
       transaction entry (sign · amount · save) and a date row. Clicks/keys inside it are
       stopped so interacting doesn't toggle the tile closed; inert when closed for a11y. -->
  <div class="cg-rise" inert={!open}
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}>
    <div class="cg-entry" class:invalid={saveError}>
      <button type="button" class="cg-seg cg-sign" onclick={flipSign}
        aria-label={sign === '+' ? 'Deposit — tap to switch to withdrawal' : 'Withdrawal — tap to switch to deposit'}>{sign === '+' ? '+' : '−'}</button>
      <div class="cg-amount">
        <span class="cg-dollar" aria-hidden="true">$</span>
        <input class="cg-amount-input" type="number" step="any" min="0" inputmode="decimal"
          placeholder="0.00" bind:value={amount} bind:this={amountEl}
          oninput={() => { saveError = null; }}
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } }}
          aria-label="Amount in dollars" />
      </div>
      <button type="button" class="cg-seg cg-save" onclick={save} disabled={saving}
        aria-label="Save transaction">✓</button>
    </div>
    <input class="cg-date-input" type="date" bind:value={date} max={today()} aria-label="Transaction date" />
    {#if saveError}<div class="cg-save-err" role="alert">{saveError}</div>{/if}
  </div>
</div>

<style>
  .cashgoal-card { position: relative; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; overflow: hidden; cursor: pointer; }
  /* tighter than the default 22px figure — the goal block shares the 1×1 below it */
  .cashgoal-card .kpi-value { font-size: 22px; }
  /* keep the cash figure clear of the coin in the corner */
  .cg-cash { padding-right: 34px; }

  .cg-coin { position: absolute; top: 12px; right: 12px; z-index: 1; overflow: visible;
    transition: transform .2s cubic-bezier(.34, 1.56, .5, 1); }
  .cashgoal-card:hover .cg-coin { transform: translateY(-2px); }

  /* diagonal shine swipe — same as .portfolio-card, but clipped to the coin face and
     triggered by hovering the card. transform-box: view-box so the % resolves in viewBox units. */
  .cg-coin-shine { transform-box: view-box; transform: translateX(-120%); transition: transform .6s ease; }
  .cashgoal-card:hover .cg-coin-shine { transform: translateX(120%); }

  .cg-goal-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
  .cg-goal-label { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; color: var(--ink); opacity: .6; }
  .cg-goal-fig { font-family: var(--mono); font-size: 11px; font-weight: 700; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }

  /* Cash entry panel: a yellow bar floats up from the bottom to 60% of the tile on click,
     with a rounded top. Holds the amount-entry control + date row, vertically centred. */
  .cg-rise {
    position: absolute; left: 0; right: 0; bottom: 0; height: 0;
    background: #FFC900;
    border-radius: 16px 16px 0 0;
    z-index: 2; overflow: hidden; cursor: default;
    display: flex; flex-direction: column; justify-content: center; gap: 7px;
    padding: 0 12px;
    transition: height .45s cubic-bezier(.22, 1, .36, 1);
  }
  .cashgoal-card.open .cg-rise { height: 60%; }

  /* Amount entry: one conjoined ink/white bar — [ +/− ] [ $ number ] [ ✓ ].
     Radius + shadow match the bottom allocation ribbon (.alloc-ribbon). */
  .cg-entry { flex: 0 0 auto; display: flex; align-items: stretch; height: 30px;
    background: #fff; border: var(--bw) solid var(--ink); border-radius: var(--r); overflow: hidden; box-shadow: var(--sh); }
  /* type error on insert → the white amount area turns pale red */
  .cg-entry.invalid, .cg-entry.invalid .cg-amount { background: #ffd9d9; }
  .cg-seg { flex: 0 0 30px; width: 30px; padding: 0; border: 0; background: var(--ink); color: #fff;
    font-family: var(--sans); font-size: 17px; font-weight: 800; line-height: 1; cursor: pointer;
    display: flex; align-items: center; justify-content: center; }
  .cg-sign { border-right: var(--bw) solid var(--ink); }
  .cg-save { border-left: var(--bw) solid var(--ink); font-size: 15px; }
  .cg-seg:active { background: #000; }
  .cg-save:disabled { opacity: .4; cursor: default; }
  .cg-amount { flex: 1 1 auto; min-width: 0; display: flex; align-items: center; gap: 3px; padding: 0 10px; background: #fff; }
  .cg-dollar { flex: 0 0 auto; color: var(--ink); opacity: .35; font-family: var(--mono); font-size: 14px; font-weight: 700; }
  .cg-amount-input { flex: 1 1 auto; min-width: 0; width: 100%; padding: 0; border: 0; outline: none; background: transparent;
    font-family: var(--mono); font-size: 14px; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums;
    -moz-appearance: textfield; appearance: textfield; }
  .cg-amount-input::placeholder { color: var(--ink); opacity: .3; }
  .cg-amount-input::-webkit-outer-spin-button, .cg-amount-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  /* Date row: native date input (calendar icon + typed entry), same behaviour as the log tab.
     Radius + shadow match the bottom allocation ribbon (.alloc-ribbon). */
  .cg-date-input { flex: 0 0 auto; box-sizing: border-box; height: 28px; width: 100%;
    padding: 0 12px; border: var(--bw) solid var(--ink); border-radius: var(--r); background: #fff; box-shadow: var(--sh);
    font-family: var(--mono); font-size: 12px; font-weight: 700; color: var(--ink); cursor: pointer; }
  .cg-date-input::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .85; }

  .cg-save-err { flex: 0 0 auto; color: var(--loss, #a3261d); font-family: var(--mono); font-size: 10px; font-weight: 700; text-align: center; }

  @media (prefers-reduced-motion: reduce) {
    .cg-coin { transition: none; }
    .cashgoal-card:hover .cg-coin { transform: none; }
    .cg-coin-shine { transition: none; }
    .cashgoal-card:hover .cg-coin-shine { transform: translateX(-120%); }
    .cg-rise { transition: none; }
  }
</style>

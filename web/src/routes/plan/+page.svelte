<script>
  // Plan — drag a savings rate, watch the next 5 to 30 years redraw. Starts from
  // the real balance; the dashed line is where the rate you actually deposit at
  // leads, so the slider reads against it. Take-home pay (and its future changes),
  // the two assumptions and the HYSA are stored per user; the slider is a what-if
  // and resets to your real rate.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import ChartFrame from '$lib/components/chart/ChartFrame.svelte';
  import PlanChart from '$lib/components/PlanChart.svelte';
  import { project, monthsFrom, usd0, usdSigned0, monthLabel, SIGMA, INFLATION } from '$lib/plan.js';

  const RANGES = ['5Y', '10Y', '20Y', '30Y'];
  const MAX_RATE = 60;

  let data = $state(null);
  let error = $state(null);
  let income = $state(null);
  let returnPct = $state(7);
  let raisePct = $state(1);
  let ratePct = $state(20);
  let range = $state('10Y');
  let hover = $state(null);
  let saveState = $state('');
  // take-home from a month on, e.g. after graduating: [{ month: 'YYYY-MM', income }]
  let steps = $state([]);
  let hysaBalance = $state(0);
  let hysaApy = $state(4);
  let hysaMonthly = $state(0);

  const now = new Date();
  // a change can start next month at the earliest; this month is the take-home field
  const nextMonth = (() => { const d = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; })();

  const years = $derived(parseInt(range));
  const balance = $derived(data?.balance ?? 0);
  // what you've actually been putting in, as a share of take-home
  const actualPct = $derived(
    income > 0 && data?.saved_monthly != null ? Math.max(0, (data.saved_monthly / income) * 100) : null
  );

  const validSteps = $derived(steps.filter((s) => /^\d{4}-\d{2}$/.test(s.month ?? '') && s.month >= nextMonth && +s.income >= 0)
    .map((s) => ({ month: s.month, income: +s.income || 0 })));
  const hysa = $derived({ balance: +hysaBalance || 0, apy: +hysaApy || 0, monthly: +hysaMonthly || 0 });
  const hasHysa = $derived(hysa.balance > 0 || hysa.monthly > 0);
  const inputs = $derived({ balance, income: income || 0, steps: validSteps, hysa,
    returnPct: +returnPct || 0, raisePct: +raisePct || 0, years, start: now });
  const points = $derived(project({ ...inputs, rate: ratePct / 100 }));
  // the slider moves in whole percents, so "at your rate" means the rounded one
  const atActual = $derived(actualPct != null && Math.round(actualPct) === ratePct);
  const baseline = $derived(
    actualPct == null || atActual ? null : project({ ...inputs, rate: actualPct / 100 }).map((p) => p.mid)
  );

  // the readout: the end of the window at rest, the hovered month while scrubbing
  const at = $derived(hover ?? points.length - 1);
  const shown = $derived(points[at]);
  const vsActual = $derived(baseline ? shown.mid - baseline[at] : null);
  const growth = $derived(shown.mid - shown.putIn);
  // the HYSA deposit is more than this month's saving, so it gets the saving
  const capped = $derived(hysa.monthly > 0 && shown.m > 0 && hysa.monthly > (shown.income * ratePct) / 100);
  const growthShare = $derived(shown.mid > 0 ? Math.max(0, growth / shown.mid) * 100 : 0);

  const keys = $derived([
    { label: 'Projected', color: 'var(--brand)' },
    { label: 'Put in', color: 'color-mix(in srgb, var(--ink) 18%, transparent)' },
    ...(hasHysa ? [{ label: 'HYSA', color: 'var(--blue)' }] : []),
    ...(baseline ? [{ label: `At your ${Math.round(actualPct)}%`, color: 'transparent' }] : []),
  ]);

  // income changes inside the window, drawn as markers on the chart
  const marks = $derived(validSteps.map((s) => ({ i: monthsFrom(now, s.month), label: usd0(s.income) }))
    .filter((k) => k.i > 0 && k.i < points.length));

  // HYSA interest at set points: next month, each income change, then whole years
  const checkpoints = $derived.by(() => {
    if (!hasHysa) return [];
    const n = points.length - 1;
    const out = [{ i: 1, label: 'Next month' }];
    for (const k of marks) out.push({ i: k.i, label: monthLabel(points[k.i].date) });
    for (const y of [1, 5, 10, 20, 30]) if (y * 12 <= n) out.push({ i: y * 12, label: `In ${y} year${y > 1 ? 's' : ''}` });
    const seen = new Set();
    return out.sort((a, b) => a.i - b.i).filter((c) => !seen.has(c.i) && seen.add(c.i));
  });

  onMount(async () => {
    try {
      data = await api.plan();
      income = data.income_monthly;
      returnPct = data.return_pct;
      raisePct = data.raise_pct;
      steps = (data.income_steps ?? []).map((s) => ({ ...s }));
      hysaBalance = data.hysa_balance;
      hysaApy = data.hysa_apy;
      hysaMonthly = data.hysa_monthly;
      if (income > 0 && data.saved_monthly != null) {
        ratePct = Math.min(MAX_RATE, Math.max(0, Math.round((data.saved_monthly / income) * 100)));
      }
    } catch (e) {
      error = String(e);
    }
  });

  // inputs save on their own, a beat after the last keystroke
  let timer;
  function queueSave() {
    clearTimeout(timer);
    saveState = '';
    timer = setTimeout(async () => {
      const r = +returnPct, g = +raisePct;
      if (!isFinite(r) || !isFinite(g) || r < -20 || r > 30 || g < -20 || g > 30) {
        saveState = 'Return and raise must be between −20% and 30%';
        return;
      }
      if (hysa.apy > 20) {
        saveState = 'APY must be 20% or less';
        return;
      }
      try {
        // a half-typed change (no month yet) isn't sent; it stays on screen
        const next = await api.setPlan({ income_monthly: income > 0 ? +income : null, return_pct: r, raise_pct: g,
          income_steps: validSteps, hysa_balance: hysa.balance, hysa_apy: hysa.apy, hysa_monthly: hysa.monthly });
        data = { ...data, ...next };
        saveState = 'Saved';
      } catch {
        saveState = 'Couldn’t save';
      }
    }, 600);
  }

  function addStep() {
    // default: a year out, at today's take-home, ready to edit
    const d = new Date(now.getFullYear() + 1, now.getMonth(), 1);
    steps = [...steps, { month: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`, income: income || 0 }];
    queueSave();
  }
  function removeStep(k) {
    steps = steps.filter((_, j) => j !== k);
    queueSave();
  }

  const fill = $derived((ratePct / MAX_RATE) * 100);
  const markAt = $derived(actualPct == null ? null : (Math.min(actualPct, MAX_RATE) / MAX_RATE) * 100);
</script>

<div class="content">
  <div class="page-title">Plan</div>
  {#if error}
    <p style="color:var(--loss)">Failed to load: {error}</p>
  {:else}
    <div class="plan">
      <div class="chart-widget plan-chart">
        <ChartFrame ranges={RANGES} bind:range {keys}>
          {#snippet tools()}
            <div class="pl-read">
              {#if data}
                <span class="pl-v">{usd0(shown.mid)}</span>
                <span class="pl-k">{hover == null ? `in ${years} years` : monthLabel(shown.date)}</span>
                <span class="pl-s">{usd0(shown.lo)} to {usd0(shown.hi)}</span>
              {:else}
                <span class="pl-v"><span class="skel skel-t" style="width:6em"></span></span>
              {/if}
            </div>
          {/snippet}
          {#if data}
            <PlanChart {points} {baseline} {marks} showHysa={hasHysa} bind:hover />
          {:else}
            <div class="skel skel-fill"></div>
          {/if}
        </ChartFrame>
      </div>

      <aside class="plan-rail">
        <div class="glass-card">
          <div class="kpi-label">Savings rate</div>
          <div class="kpi-value">{ratePct}%</div>
          <div class="kpi-subtitle">
            {#if income > 0}{usd0((income * ratePct) / 100)} a month{:else}Add your take-home pay to price this{/if}
          </div>

          <div class="pl-slider" style="--fill:{fill}%">
            <input type="range" min="0" max={MAX_RATE} step="1" bind:value={ratePct} aria-label="Savings rate" />
            {#if markAt != null}
              <button class="pl-mark" style="--at:{markAt}%" onclick={() => (ratePct = Math.min(MAX_RATE, Math.round(actualPct)))}
                title="Your deposits over the last {data.saved_months} months, as a share of take-home">
                <span class="pl-tick"></span>Yours {Math.round(actualPct)}%
              </button>
            {/if}
          </div>

          {#if data}
            <div class="bal-rows pl-rows">
              <div class="bal-row"><span class="bal-k">Put in</span><span class="bal-v">{usd0(shown.putIn)}</span></div>
              <div class="bal-row"><span class="bal-k">Growth</span><span class="bal-v"><span class="dim">{Math.round(growthShare)}%</span> {usd0(growth)}</span></div>
              {#if vsActual != null && Math.abs(vsActual) >= 1}
                <div class="bal-row"><span class="bal-k">Vs your rate</span>
                  <span class="bal-v {vsActual >= 0 ? 'up' : 'down'}">{usdSigned0(vsActual)}</span></div>
              {/if}
            </div>
          {/if}
        </div>

        <div class="glass-card">
          <div class="kpi-label">Assumptions</div>
          <div class="pl-fields">
            <label class="pl-field">
              <span class="bal-k">Take-home a month</span>
              <span class="pl-box pl-lead"><span class="pl-unit">$</span>
                <input type="number" min="0" step="any" inputmode="decimal" placeholder="0"
                  bind:value={income} oninput={queueSave} /></span>
            </label>
            {#if steps.length}
              <span class="pl-then">Then, from</span>
              {#each steps as s, k (k)}
                <div class="pl-step">
                  <span class="pl-box pl-month" class:invalid={!validSteps.some((v) => v.month === s.month)}>
                    <input type="month" min={nextMonth} placeholder="YYYY-MM" bind:value={s.month} oninput={queueSave}
                      aria-label="Month the new take-home starts" /></span>
                  <span class="pl-box pl-lead"><span class="pl-unit">$</span>
                    <input type="number" min="0" step="any" inputmode="decimal" placeholder="0"
                      bind:value={s.income} oninput={queueSave} aria-label="Take-home a month from then" /></span>
                  <button class="btn btn-sm btn-quiet pl-x" onclick={() => removeStep(k)} aria-label="Remove this change">✕</button>
                </div>
              {/each}
            {/if}
            <button class="btn btn-sm btn-line pl-add" onclick={addStep} disabled={steps.length >= 12}>Add income change</button>
            <label class="pl-field">
              <span class="bal-k">Return a year</span>
              <span class="pl-box"><input type="number" step="0.5" inputmode="decimal"
                bind:value={returnPct} oninput={queueSave} /><span class="pl-unit">%</span></span>
            </label>
            <label class="pl-field">
              <span class="bal-k">Raise a year</span>
              <span class="pl-box"><input type="number" step="0.5" inputmode="decimal"
                bind:value={raisePct} oninput={queueSave} /><span class="pl-unit">%</span></span>
            </label>
          </div>

          <div class="bal-rows pl-rows">
            <div class="bal-row"><span class="bal-k">Starting balance</span>
              <span class="bal-v">{#if data}{usd0(data.balance)}{:else}<span class="skel skel-t"></span>{/if}</span></div>
            <div class="bal-row"><span class="bal-k">Deposited a month</span>
              <span class="bal-v">{#if data}{data.saved_monthly == null ? '—' : usd0(data.saved_monthly)}{:else}<span class="skel skel-t"></span>{/if}</span></div>
          </div>

          <p class="pl-note">
            {saveState ? saveState + '. ' : ''}Returns are after inflation, so figures are in today’s dollars.
            The band is the middle 80% of outcomes for a fund that swings about {Math.round(SIGMA * 100)}% a year.
          </p>
        </div>

        <div class="glass-card">
          <div class="kpi-label">HYSA interest</div>
          <div class="kpi-value">{hasHysa ? usd0(shown.interest) : '—'}</div>
          <div class="kpi-subtitle">
            {#if hasHysa}a month on {usd0(shown.hysa)}, {hover == null ? `in ${years} years` : monthLabel(shown.date)}
            {:else}Add a balance or a monthly deposit{/if}
          </div>

          <div class="pl-fields pl-rows">
            <label class="pl-field">
              <span class="bal-k">Balance</span>
              <span class="pl-box pl-lead"><span class="pl-unit">$</span>
                <input type="number" min="0" step="any" inputmode="decimal" placeholder="0"
                  bind:value={hysaBalance} oninput={queueSave} /></span>
            </label>
            <label class="pl-field">
              <span class="bal-k">APY</span>
              <span class="pl-box"><input type="number" min="0" max="20" step="0.05" inputmode="decimal"
                bind:value={hysaApy} oninput={queueSave} /><span class="pl-unit">%</span></span>
            </label>
            <label class="pl-field">
              <span class="bal-k">Into it a month</span>
              <span class="pl-box pl-lead"><span class="pl-unit">$</span>
                <input type="number" min="0" step="any" inputmode="decimal" placeholder="0"
                  bind:value={hysaMonthly} oninput={queueSave} /></span>
            </label>
          </div>

          {#if checkpoints.length}
            <!-- interest a month at set points; pointing at one scrubs the chart there -->
            <div class="bal-rows pl-rows">
              {#each checkpoints as c (c.i)}
                <button class="bal-row pl-cp" class:on={hover === c.i}
                  onpointerenter={() => (hover = c.i)} onpointerleave={() => (hover = null)}
                  onfocus={() => (hover = c.i)} onblur={() => (hover = null)}>
                  <span class="bal-k">{c.label}</span><span class="bal-v">{usd0(points[c.i].interest)}</span>
                </button>
              {/each}
            </div>
          {/if}

          <p class="pl-note">
            {#if capped}At {ratePct}% you save {usd0(shown.income * ratePct / 100)} a month, so that’s all the HYSA gets.{' '}{/if}
            Interest is what the bank pays at that APY. The balance grows by the APY less {INFLATION * 100}% inflation,
            in today’s dollars like the rest. The HYSA comes out of your saving; the rest is invested.
          </p>
        </div>
      </aside>
    </div>
  {/if}
</div>

<style>
  .plan { display: grid; grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr); gap: 16px; align-items: start; }
  /* the rail runs much taller than the chart; keep the chart in view beside it so
     the slider and the HYSA rows can be read against it */
  .plan-chart { min-width: 0; position: sticky; top: 24px; }
  .plan-rail { --card-pad: 14px 16px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }

  /* readout: the chart readout's sizes, with dollars leading */
  .pl-read { display: flex; align-items: baseline; gap: 8px; padding-left: 6px; min-width: 0; white-space: nowrap;
    font-family: var(--num); font-variant-numeric: tabular-nums; }
  .pl-v { font-size: 18px; font-weight: 600; line-height: 1; letter-spacing: -.01em; }
  .pl-k { font-family: var(--sans); font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .pl-s { font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  /* slider: an ink-outlined track filled to the value, round ink thumb */
  .pl-slider { position: relative; margin: 14px 0 4px; padding-bottom: 22px; }
  .pl-slider input { -webkit-appearance: none; appearance: none; display: block; width: 100%; height: 18px;
    margin: 0; background: transparent; cursor: pointer; }
  .pl-slider input::-webkit-slider-runnable-track { height: 8px; border: var(--bw) solid var(--ink); border-radius: 999px;
    background: linear-gradient(90deg, var(--ink) var(--fill), transparent var(--fill)); }
  .pl-slider input::-moz-range-track { height: 8px; border: var(--bw) solid var(--ink); border-radius: 999px;
    background: linear-gradient(90deg, var(--ink) var(--fill), transparent var(--fill)); }
  .pl-slider input::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; margin-top: -6px;
    border-radius: 50%; background: var(--paper); border: var(--bw) solid var(--ink); box-shadow: 0 0 0 transparent;
    transition: box-shadow .12s ease; }
  .pl-slider input::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: var(--paper);
    border: var(--bw) solid var(--ink); }
  .pl-slider input:hover::-webkit-slider-thumb, .pl-slider input:focus-visible::-webkit-slider-thumb { box-shadow: 2px 2px 0 var(--ink); }
  .pl-slider input:focus-visible { outline: none; }

  /* where your real rate sits on the track; click to jump back to it */
  .pl-mark { position: absolute; top: 20px; left: calc(9px + (100% - 18px) * var(--at) / 100%); transform: translateX(-50%);
    display: inline-flex; flex-direction: column; align-items: center; gap: 2px; padding: 0; border: 0; background: none;
    cursor: pointer; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted);
    font-variant-numeric: tabular-nums; white-space: nowrap; }
  .pl-mark:hover { color: var(--ink); }
  .pl-tick { width: 1px; height: 5px; background: currentColor; }

  .pl-rows { margin-top: 12px; }
  .up { color: var(--gain); }
  .down { color: var(--loss); }

  .pl-fields { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }
  .pl-field { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .pl-box { flex: 0 0 120px; box-sizing: border-box; height: 30px; display: flex; align-items: center; gap: 3px; padding: 0 10px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); background: var(--surface); }
  .pl-box:focus-within { box-shadow: 2px 2px 0 var(--ink); }
  .pl-unit { flex: 0 0 auto; color: var(--muted); font-family: var(--num); font-size: var(--fs-body); font-weight: 600; }
  .pl-box input { flex: 1 1 auto; min-width: 0; width: 100%; padding: 0; border: 0; outline: none; background: transparent;
    font-family: var(--num); font-size: var(--fs-body); font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums;
    text-align: right; -moz-appearance: textfield; appearance: textfield; }
  /* a leading $ reads with the number beside it; a trailing % already sits beside it */
  .pl-lead input { text-align: left; }
  .pl-box input::placeholder { color: var(--muted); }
  .pl-box input::-webkit-outer-spin-button, .pl-box input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  /* income changes: month box takes the room, amount the field width, then remove */
  .pl-then { margin-top: 2px; font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .pl-step { display: flex; align-items: center; gap: 6px; }
  .pl-step .pl-month { flex: 1 1 auto; min-width: 0; }
  .pl-step .pl-lead { flex: 0 0 110px; }
  .pl-month input { text-align: left; color-scheme: light dark; cursor: pointer; }
  .pl-month input::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .85; }
  .pl-box.invalid { border-color: var(--loss); }
  .pl-x { flex: 0 0 auto; padding-inline: 7px; }
  .pl-add { align-self: flex-start; }

  /* HYSA checkpoints: rows that scrub the chart, the sidebar rows' hover wash */
  .pl-cp { width: 100%; padding: 2px 6px; margin: 0 -6px; box-sizing: content-box; border: 0; border-radius: 3px;
    background: none; font: inherit; color: inherit; text-align: left; cursor: default; }
  .pl-cp:hover, .pl-cp.on, .pl-cp:focus-visible { background: var(--hover); outline: none; }

  .pl-note { margin: 12px 0 0; font-size: var(--fs-meta); font-weight: 500; line-height: 1.45; color: var(--muted); }

  /* one column: the chart, then the three cards two across */
  @media (max-width: 1100px) {
    .plan { grid-template-columns: minmax(0, 1fr); }
    .plan-chart { position: static; }
    .plan-rail { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; }
  }
  @media (max-width: 700px) {
    .plan-rail { grid-template-columns: minmax(0, 1fr); }
  }
</style>

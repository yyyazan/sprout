<script>
  // The learning path, in order. Checked state persists in localStorage —
  // it's a personal syllabus, not server data. Each item names the Lab module
  // it unlocks or the trap it teaches you to avoid.
  const TOPICS = [
    { id: 'returns', t: 'Returns, volatility & Sharpe', d: 'why raw return is meaningless without the risk taken to get it' },
    { id: 'capm', t: 'CAPM: alpha, beta, R²', d: 'the factors panel, live on your own portfolio — start here' },
    { id: 'pitfalls', t: 'Backtesting pitfalls', d: 'look-ahead, overfitting, survivorship — why most backtests lie' },
    { id: 'factors', t: 'The factor zoo', d: 'Fama-French size/value, momentum, quality — the documented premia' },
    { id: 'options', t: 'Options: payoffs → greeks', d: 'payoff diagrams first (live below), then delta/theta/vega' },
    { id: 'sizing', t: 'Position sizing', d: 'Kelly criterion, vol targeting — edge means nothing if you size wrong' },
    { id: 'execution', t: 'Costs & execution', d: 'spreads, slippage, taxes — the silent strategy killers' },
    { id: 'auto', t: 'Automation, paper first', d: 'signals → orders with a kill switch; never unattended, never real money first' },
  ];
  const KEY = 'sprout-lab-curriculum';

  let done = $state(new Set());
  try { done = new Set(JSON.parse(localStorage.getItem(KEY) ?? '[]')); } catch { /* fresh start */ }

  function toggle(id) {
    const next = new Set(done);
    next.has(id) ? next.delete(id) : next.add(id);
    done = next;
    try { localStorage.setItem(KEY, JSON.stringify([...next])); } catch { /* private mode */ }
  }
</script>

<div class="cu-progress">{done.size}/{TOPICS.length} covered</div>
{#each TOPICS as item, i (item.id)}
  <button class="cu-row" class:done={done.has(item.id)} onclick={() => toggle(item.id)}
    aria-pressed={done.has(item.id)}>
    <span class="cu-box">{done.has(item.id) ? '✕' : ''}</span>
    <span class="cu-idx">{i + 1}</span>
    <span class="cu-body">
      <span class="cu-t">{item.t}</span>
      <span class="cu-d">{item.d}</span>
    </span>
  </button>
{/each}

<style>
  .cu-progress { font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: .1em; }

  .cu-row { display: flex; align-items: flex-start; gap: 10px; width: 100%; padding: 9px 4px;
    background: transparent; border: 0; border-bottom: var(--bw) solid var(--hairline);
    cursor: pointer; text-align: left; }
  .cu-row:last-child { border-bottom: 0; }

  .cu-box { flex: 0 0 16px; width: 16px; height: 16px; margin-top: 1px;
    border: var(--bw) solid var(--ink); border-radius: 3px; display: grid; place-items: center;
    font-family: var(--mono); font-size: 10px; font-weight: 800; color: var(--paper); }
  .cu-row.done .cu-box { background: var(--ink); }

  .cu-idx { flex: 0 0 auto; font-family: var(--mono); font-size: 10px; font-weight: 700;
    color: var(--muted); margin-top: 3px; }

  .cu-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
  .cu-t { font-family: var(--sans); font-size: 12.5px; font-weight: 700; color: var(--ink); }
  .cu-row.done .cu-t { text-decoration: line-through; text-decoration-thickness: 1px; opacity: .55; }
  .cu-d { font-family: var(--sans); font-size: 11px; line-height: 1.4; color: var(--muted); }
</style>

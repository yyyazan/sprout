<script>
  // Dividend ring — monthly dividend income on the shared RingGauge. Segments
  // are this month's payers sized by contribution; hover a payer → the core
  // swaps to that stock.
  //
  // DATA IS MOCKED (mockDividends → divYieldOf): real positions × a deterministic
  // mock yield. SWAP POINT: a real /api/dividends keeps the same {items,...} shape.
  import RingGauge from './RingGauge.svelte';
  import { mockDividends } from '$lib/mockStock.js';

  let { holdings = [], data = null } = $props();

  const COLORS = ['#0fb39a', '#ff90e8', '#ffc900', '#5b8def', '#c994e8', '#ff6e5e'];
  const OTHER = '#8a8478';
  const MAX = 6; // top (MAX-1) payers + one "others" wedge

  const div = $derived(data ?? mockDividends(holdings));
  const m0 = (v) => '$' + Math.round(v ?? 0).toLocaleString('en-US');

  const segments = $derived.by(() => {
    let list = div.items;
    if (list.length > MAX) {
      const head = list.slice(0, MAX - 1);
      const tail = list.slice(MAX - 1);
      list = [...head, {
        t: 'OTHER', name: `${tail.length} more`, other: true, yieldPct: null,
        monthly: tail.reduce((s, d) => s + d.monthly, 0),
      }];
    }
    return list.map((d, i) => ({
      key: d.t,
      color: d.other ? OTHER : COLORS[i % COLORS.length],
      value: d.monthly,
      tag: d.t,
      hero: m0(d.monthly),
      per: '/mo',
      sub: d.other ? d.name : `${d.yieldPct != null ? d.yieldPct.toFixed(1) : '—'}% yld`,
    }));
  });

  const idle = $derived(
    div.monthlyTotal > 0
      ? { tag: 'dividends', hero: m0(div.monthlyTotal), per: '/mo', sub: `${m0(div.annualTotal)}/yr · ${div.yieldOnValue.toFixed(1)}%` }
      : { tag: 'dividends', hero: '$0', per: '/mo', sub: 'none yet' }
  );
</script>

<RingGauge {segments} {idle} />

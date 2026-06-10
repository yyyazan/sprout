<script>
  // Allocation ring — portfolio weights on the shared RingGauge. Top six
  // positions get a segment, the tail folds into "other". Hover swaps the core;
  // click opens the stock view.
  import RingGauge from './RingGauge.svelte';
  import { openStock, cardToHolding } from '$lib/stores.js';

  let { holdings = [] } = $props();   // dashboard cards (non-joker)

  const COLORS = ['#5fb3c4', '#e08a6a', '#0fb39a', '#d8b878', '#9bbf8a', '#c994e8'];
  const OTHER_C = '#8a8478';
  const MAX_SEGS = 6;

  const rows = $derived(
    [...holdings].filter((c) => (c.position_pct ?? 0) > 0)
      .sort((a, b) => (b.position_pct ?? 0) - (a.position_pct ?? 0))
  );

  const segments = $derived.by(() => {
    const top = rows.slice(0, MAX_SEGS);
    const tailPct = rows.slice(MAX_SEGS).reduce((s, c) => s + (c.position_pct ?? 0), 0);
    const segs = top.map((c, i) => ({
      key: c.ticker,
      color: COLORS[i % COLORS.length],
      value: c.position_pct,
      tag: c.ticker,
      hero: (c.position_pct ?? 0).toFixed(1),
      per: '%',
      sub: c.company_name,
      pick: () => openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) }),
    }));
    if (tailPct > 0.05) {
      segs.push({ key: '·other', color: OTHER_C, value: tailPct, tag: 'other',
        hero: tailPct.toFixed(1), per: '%', sub: `${rows.length - MAX_SEGS} more` });
    }
    return segs;
  });

  const idle = $derived.by(() => {
    const top = rows[0];
    return top
      ? { tag: 'allocation', hero: (top.position_pct ?? 0).toFixed(1), per: '%', sub: `top · ${top.ticker}` }
      : { tag: 'allocation', hero: '—', sub: 'no positions' };
  });
</script>

<RingGauge {segments} {idle} />

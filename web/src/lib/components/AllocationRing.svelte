<script>
  // Allocation ring — portfolio weights on the shared RingGauge. Top six
  // positions get a segment, the tail folds into "other". Hover swaps the core;
  // click opens the stock view.
  import RingGauge from './RingGauge.svelte';
  import { openStock, cardToHolding } from '$lib/stores.js';

  let { holdings = [] } = $props();   // dashboard cards (non-joker)

  // 10 distinct hues (existing five + accent deck) so 10 segments never repeat a colour
  const COLORS = ['#5fb3c4', '#e08a6a', '#0fb39a', '#d8b878', '#9bbf8a',
                  '#c994e8', '#ff90e8', '#ffc900', '#5b8def', '#ff6e5e'];
  const OTHER_C = '#8a8478';
  const MAX_SEGS = 10;

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
      segs.push({ key: '·other', color: OTHER_C, value: tailPct, tag: 'Other',
        hero: tailPct.toFixed(1), per: '%', sub: `${rows.length - MAX_SEGS} more` });
    }
    return segs;
  });

  // idle reads diversification at a glance: holdings COUNT as the hero (the 'per'
  // slot is too small for a word, so 'holdings' rides the tag), and the top-3
  // combined weight as the always-meaningful concentration subtitle
  const idle = $derived.by(() => {
    if (!rows.length) return { tag: 'Allocation', hero: '—', sub: 'No positions' };
    const top3 = rows.slice(0, 3).reduce((s, c) => s + (c.position_pct ?? 0), 0);
    return { tag: rows.length === 1 ? 'Holding' : 'Holdings', hero: String(rows.length), sub: `${Math.round(top3)}% in top 3` };
  });
</script>

<RingGauge {segments} {idle} />

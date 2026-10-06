<script>
  // Allocation ring — portfolio weights on the shared RingGauge. Top ten
  // positions get a segment, the tail folds into "other". Hover swaps the core;
  // click opens the stock view. A fund (index or otherwise) is a hollow
  // segment — ink outline, no hue — the same read as its outlined ticker badge,
  // and it doesn't take a palette slot, so the stocks keep a contiguous run of
  // hues. The core carries the index-fund share of the portfolio.
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
    let hue = 0;
    const segs = top.map((c) => {
      const hollow = (c.kind ?? 'stock') !== 'stock';
      return {
        key: c.ticker,
        hollow,
        color: hollow ? 'transparent' : COLORS[hue++ % COLORS.length],
        value: c.position_pct,
        tag: c.ticker,
        hero: (c.position_pct ?? 0).toFixed(1),
        per: '%',
        sub: c.company_name,
        pick: () => openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) }),
      };
    });
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
    const index = rows.filter((c) => c.kind === 'index').reduce((s, c) => s + (c.position_pct ?? 0), 0);
    return {
      tag: rows.length === 1 ? 'Holding' : 'Holdings', hero: String(rows.length),
      sub: `${Math.round(top3)}% in top 3`, sub2: `${Math.round(index)}% index funds`,
    };
  });
</script>

<RingGauge {segments} {idle} />

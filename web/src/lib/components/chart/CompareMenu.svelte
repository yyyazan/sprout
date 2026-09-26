<script>
  // Compare picker for both charts: quick picks + a search box (the same
  // /api/search the palette uses). `list` is the host's [{ sym, label, color }];
  // the host fetches and plots, this only edits the list.
  import ChartMenu from './ChartMenu.svelte';
  import { api } from '$lib/api.js';

  let { list = $bindable([]), exclude = null } = $props();

  const QUICK = [
    { sym: 'SPY', label: 'S&P 500' },
    { sym: 'QQQ', label: 'Nasdaq 100' },
    { sym: 'BTC-USD', label: 'Bitcoin' },
  ];
  const COLORS = ['#5b8def', '#ff90e8', '#ffc900', '#c994e8', '#ff6e5e'];
  const MAX = 4;

  let q = $state('');
  let results = $state([]);
  let loading = $state(false);

  const up = (s) => (s || '').toUpperCase();
  const has = (sym) => list.some((c) => c.sym === up(sym));

  function toggle(sym, label) {
    const s = up(sym);
    if (s === up(exclude)) return;                 // never compare with itself
    if (has(s)) { list = list.filter((c) => c.sym !== s); return; }
    if (list.length >= MAX) return;
    const used = new Set(list.map((c) => c.color));
    list = [...list, { sym: s, label: label ?? s, color: COLORS.find((c) => !used.has(c)) ?? COLORS[0] }];
    q = '';
    results = [];
  }

  // debounced search (180ms, stale-proof)
  let seq = 0, timer = null;
  $effect(() => {
    const query = q.trim();
    if (timer) clearTimeout(timer);
    if (!query) { results = []; loading = false; return; }
    loading = true;
    const mine = ++seq;
    timer = setTimeout(async () => {
      try {
        const r = await api.search(query);
        if (mine === seq) results = (r.results ?? []).slice(0, 6);
      } catch {
        if (mine === seq) results = [];
      } finally {
        if (mine === seq) loading = false;
      }
    }, 180);
  });
</script>

<ChartMenu label="Compare" icon="compare" count={list.length} active={list.length > 0} width={230}>
  <input class="cmp-input" type="text" placeholder="Search any stock or ETF…" bind:value={q}
    autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
  {#if q.trim()}
    {#if loading}
      <div class="cm-note">Searching…</div>
    {:else if results.length === 0}
      <div class="cm-note">No matches</div>
    {:else}
      {#each results as r (r.symbol)}
        <button class="cm-item" class:sel={has(r.symbol)} onclick={() => toggle(r.symbol, r.name)}>
          <span class="cm-check">{has(r.symbol) ? '✓' : ''}</span>
          <span class="cm-name">{r.name}</span><span class="cm-sym">{r.symbol}</span>
        </button>
      {/each}
    {/if}
  {:else}
    {#each QUICK as c (c.sym)}
      <button class="cm-item" class:sel={has(c.sym)} onclick={() => toggle(c.sym, c.label)}>
        <span class="cm-check">{has(c.sym) ? '✓' : ''}</span><span class="cm-name">{c.label}</span><span class="cm-sym">{c.sym}</span>
      </button>
    {/each}
    {#each list.filter((c) => !QUICK.some((x) => x.sym === c.sym)) as c (c.sym)}
      <button class="cm-item sel" onclick={() => toggle(c.sym)}>
        <span class="cm-check">✓</span><span class="cm-name">{c.label}</span><span class="cm-sym">{c.sym}</span>
      </button>
    {/each}
  {/if}
</ChartMenu>

<style>
  .cmp-input { box-sizing: border-box; width: 100%; margin-bottom: 4px; padding: 7px 9px;
    border: var(--bw) solid var(--hairline); border-radius: 6px; outline: none; background: transparent;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink); }
  .cmp-input:focus { border-color: var(--ink); }
  .cmp-input::placeholder { color: var(--muted); }
  /* iOS focus-zoom guard */
  @media (max-width: 700px) { .cmp-input { font-size: 16px; } }
</style>

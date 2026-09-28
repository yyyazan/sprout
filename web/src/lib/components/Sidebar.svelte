<script>
  import { onMount, tick } from 'svelte';
  import { flip } from 'svelte/animate';
  import { page } from '$app/stores';
  import {
    holdings, moves, loadHoldings, startMomentum, openStock, cardToHolding,
    lists, loadLists, createList, renameList, deleteList,
  } from '$lib/stores.js';
  import { ListDrag, previewLists, slotListOf, dropLayout, saveIfMoved } from '$lib/listDrag.svelte.js';
  import { theme, toggleTheme } from '$lib/theme.js';
  import TickerBadge from './TickerBadge.svelte';
  import { prefetch } from '$lib/stockCache.js';
  import Sparkline from './Sparkline.svelte';
  import ProfileMenu from './ProfileMenu.svelte';

  let menuOpen = $state(false);

  const NAV = [
    { label: 'Home', path: '/' },
    { label: 'Log', path: '/trades' },
  ];
  function isActive(pathname, path) {
    return path === '/' ? pathname === '/' : pathname.startsWith(path);
  }
  onMount(() => { loadHoldings(); startMomentum(); loadLists(); });

  const WINS = [['day', 'D'], ['wk', 'W'], ['mo', 'M']];
  let win = $state('mo');   // which move window the pills encode; the sparkline is always the past month

  // Holdings: heaviest first, never reorderable (stable, so live updates don't make rows jump)
  const rows = $derived(
    [...($holdings ?? [])].sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
  );

  // live move (fresh /api/momentum) with the frozen dashboard payload as fallback;
  // the month window only exists live
  const moveOf = (c, w) => {
    const live = $moves[c.ticker];
    if (w === 'mo') return live?.month_pct ?? null;
    const v = live ? (w === 'day' ? live.day_pct : live.week_pct) : (w === 'day' ? c.day_pct : c.week_pct);
    return v ?? 0;
  };
  const itemMove = (it, w) => (w === 'day' ? it.dayPct : w === 'wk' ? it.weekPct : it.monthPct);
  // the sparkline's own direction colors it — first close to spot
  const sparkUp = (sp) => !sp?.length || sp[sp.length - 1] >= sp[0];
  const tone = (n) => (n == null ? '' : n >= 0 ? 'up' : 'down');
  const pct = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
  const px = (n) => n == null ? '—' : '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const wt = (n) => (n ?? 0).toFixed(1) + '%';
  const usd = (n) => {
    if (n == null) return '—';
    const a = Math.abs(n);
    if (a >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'k';
    return '$' + Math.round(n);
  };

  function openTicker(ticker, name) {
    const card = ($holdings ?? []).find((c) => c.ticker === ticker);
    openStock({ ticker, name: card?.company_name ?? name, holding: card ? cardToHolding(card) : null });
  }

  // ── collapsed sections (per viewer) ──
  const COLLAPSE_KEY = 'sprout-rail-collapsed';
  let collapsed = $state((() => {
    try { return JSON.parse(localStorage.getItem(COLLAPSE_KEY)) ?? []; } catch { return []; }
  })());
  const isCollapsed = (k) => collapsed.includes(k);
  function toggleSection(k) {
    collapsed = isCollapsed(k) ? collapsed.filter((x) => x !== k) : [...collapsed, k];
    try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify(collapsed)); } catch {}
  }

  // ── list header actions: rename in place, delete with a confirm ──
  let renaming = $state(null);
  let renameVal = $state('');
  let renameEl = $state();
  let confirmDel = $state(null);

  async function startRename(L) {
    confirmDel = null;
    renaming = L.id;
    renameVal = L.name;
    await tick();
    renameEl?.select();
  }
  function commitRename(L) {
    if (renaming !== L.id) return;
    const name = renameVal.trim();
    renaming = null;
    if (name && name !== L.name) renameList(L.id, name);
  }
  async function newList(tickers = []) {
    const id = await createList('New list', tickers);
    if (id == null) return;
    const L = ($lists ?? []).find((l) => l.id === id);
    if (L) startRename(L);
  }

  // ── drag and drop (lib/listDrag.svelte.js) ──
  // Live preview: rows slide apart, the dragged row leaves a dashed slot where
  // it will land, and a lifted copy follows the pointer. Touch picks a row up
  // after a hold, so the rail still scrolls on a tablet.
  let railEl;
  const dnd = new ListDrag({
    root: () => railEl,
    scroller: () => railEl,
    collapsed: (id) => isCollapsed('l' + id),
    canStart: () => renaming == null,
    onDrop: async (d) => {
      await saveIfMoved(dropLayout($lists ?? [], d));
      if (d.over.zone === 'new') newList([d.ticker]);
    },
  });
  const grab = dnd.grab;
  const drag = $derived(dnd.drag);
  const shown = $derived(previewLists($lists ?? [], drag));
  const slotList = $derived(slotListOf(drag));
  const zoneOn = $derived(drag?.kind === 'item');
</script>

{#snippet rowBody(ticker, sub, spark, price, move)}
  <span class="r-col r-id">
    <TickerBadge sym={ticker} />
    <span class="r-sub">{#each sub as s}<span>{s}</span>{/each}</span>
  </span>
  <span class="r-spark {sparkUp(spark) ? 'up' : 'down'}">
    <Sparkline values={spark ?? []} width={56} height={20} />
  </span>
  <span class="r-col r-fig">
    <span class="r-px">{px(price)}</span>
    <span class="r-day pct-pill {tone(move)}">{pct(move)}</span>
  </span>
{/snippet}

{#snippet chevron(k)}
  <svg class="chev" class:shut={isCollapsed(k)} viewBox="0 0 10 10" aria-hidden="true">
    <path d="M2.5 3.75 5 6.25 7.5 3.75" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
{/snippet}

<aside class="sidebar">
  <div class="brand brand-row">
    <span class="brand-title">sprout</span>
    <div class="brand-actions">
      <div class="profile-wrap">
        <button class="btn-icon" type="button" aria-label="Account" aria-haspopup="menu"
          aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="12" cy="8.5" r="3.6" /><path d="M5 20 c0 -4 3.2 -6.2 7 -6.2 s7 2.2 7 6.2" />
          </svg>
        </button>
        <ProfileMenu open={menuOpen} onClose={() => (menuOpen = false)} />
      </div>
      <button class="btn-icon" onclick={toggleTheme} aria-label="Toggle light/dark theme" title="{$theme === 'dark' ? 'Light' : 'Dark'} mode">
        {#if $theme === 'dark'}
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
          </svg>
        {:else}
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
            <path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10Z" />
          </svg>
        {/if}
      </button>
    </div>
  </div>

  <nav class="nav">
    {#each NAV as item}
      <a href={item.path} class="nav-link" class:active={isActive($page.url.pathname, item.path)}>
        <div class="nav-item"><span class="nav-label">{item.label}</span></div>
      </a>
    {/each}
  </nav>

  <div class="rail" bind:this={railEl}>
    <!-- holdings: fixed order (weight), a copy source for the lists below -->
    <section class="sec">
      <div class="sec-head">
        <button class="sec-toggle" onclick={() => toggleSection('holdings')} aria-expanded={!isCollapsed('holdings')}>
          {@render chevron('holdings')}
          <span class="sec-name">Holdings</span>
          {#if rows.length}<span class="sec-count">{rows.length}</span>{/if}
        </button>
        <div class="sec-win" role="group" aria-label="Move window">
          {#each WINS as [k, label] (k)}
            <button class="btn btn-sm btn-mono" class:on={win === k} onclick={() => (win = k)}>{label}</button>
          {/each}
        </div>
      </div>
      {#if !isCollapsed('holdings')}
        {#if $holdings === null}
          {#each [0, 1, 2, 3, 4, 5] as i (i)}
            <div class="row sk-row" aria-hidden="true">
              <span class="r-col r-id"><span class="skel sk-badge"></span><span class="skel skel-t" style="width:70%"></span></span>
              <span class="skel sk-spark"></span>
              <span class="r-col r-fig"><span class="skel skel-t" style="width:52px"></span><span class="skel sk-pill"></span></span>
            </div>
          {/each}
        {:else if rows.length === 0}
          <div class="rail-empty">No holdings yet.</div>
        {:else}
          {#each rows as c, i (c.ticker)}
            <button class="row" class:src={drag?.from === 'holdings' && drag.ticker === c.ticker}
              style="--i:{Math.min(i, 16)}"
              use:grab={{ kind: 'item', ticker: c.ticker, from: 'holdings' }}
              use:prefetch={c.ticker}
              onclick={() => openTicker(c.ticker, c.company_name)}>
              {@render rowBody(c.ticker, [usd(c.market_value), wt(c.position_pct)], $moves[c.ticker]?.spark,
                $moves[c.ticker]?.spot ?? c.current_price, moveOf(c, win))}
            </button>
          {/each}
        {/if}
      {/if}
    </section>

    {#each shown as L (L.id)}
      {@const k = 'l' + L.id}
      <section class="sec" data-list={L.id} animate:flip={{ duration: 160 }}
        class:target={drag?.kind === 'item' && drag.over?.listId === L.id && isCollapsed(k)}>
        {#if drag?.kind === 'list' && drag.listId === L.id}
          <div class="slot-ph" style="height:{drag.h}px"></div>
        {:else if confirmDel === L.id}
          <div class="sec-head sec-confirm">
            <span class="sec-ask">Delete list?</span>
            <button class="btn btn-sm btn-danger" onclick={() => { confirmDel = null; deleteList(L.id); }}>Delete</button>
            <button class="btn btn-sm btn-quiet" onclick={() => (confirmDel = null)}>Cancel</button>
          </div>
        {:else}
          <div class="sec-head">
            {#if renaming === L.id}
              <input class="sec-rename" bind:this={renameEl} bind:value={renameVal} maxlength="40" aria-label="List name"
                onkeydown={(e) => { if (e.key === 'Enter') commitRename(L); else if (e.key === 'Escape') renaming = null; }}
                onblur={() => commitRename(L)} />
            {:else}
              <button class="sec-toggle sec-grab" aria-expanded={!isCollapsed(k)}
                use:grab={{ kind: 'list', listId: L.id, label: L.name }}
                onclick={() => toggleSection(k)}>
                {@render chevron(k)}
                <span class="sec-name">{L.name}</span>
                {#if L.items.length}<span class="sec-count">{L.items.length}</span>{/if}
              </button>
              <span class="sec-acts">
                <button class="sec-ic" onclick={() => startRename(L)} aria-label="Rename {L.name}">✎</button>
                <button class="sec-ic" onclick={() => { renaming = null; confirmDel = L.id; }} aria-label="Delete {L.name}">✕</button>
              </span>
            {/if}
          </div>
          {#if !isCollapsed(k)}
            {#each L.items as it (it.ticker)}
              <div class="slot" data-slot={it.ticker} animate:flip={{ duration: 160 }}>
                {#if slotList === L.id && it.ticker === drag.ticker}
                  <div class="slot-ph" style="height:{drag.h}px"></div>
                {:else}
                  <button class="row"
                    use:grab={{ kind: 'item', ticker: it.ticker, from: L.id, row: it }}
                    use:prefetch={it.ticker}
                    onclick={() => openTicker(it.ticker, it.name)}>
                    {@render rowBody(it.ticker, [it.name], it.spark, it.price, itemMove(it, win))}
                  </button>
                {/if}
              </div>
            {:else}
              <div class="sec-hint">Drag stocks here</div>
            {/each}
          {/if}
        {/if}
      </section>
    {/each}
  </div>

  <!-- new list at rest; while a row is dragged, the drop targets -->
  <div class="rail-drop">
    <button class="zone" class:live={zoneOn} class:over={drag?.over?.zone === 'new'}
      data-zone={zoneOn ? 'new' : undefined} onclick={() => newList()}>
      {zoneOn ? 'New list' : '+ New list'}
    </button>
    {#if zoneOn && drag.from !== 'holdings'}
      <div class="zone zone-rm live" class:over={drag.over?.zone === 'remove'} data-zone="remove">Remove</div>
    {/if}
  </div>

</aside>

{#if drag?.over?.zone}
  <!-- over a drop zone the lift shrinks to its badge so the zone's label stays readable -->
  <div class="ghost ghost-chip" style="transform:translate({drag.x + 10}px, {drag.y + 10}px)" aria-hidden="true">
    <TickerBadge sym={drag.ticker} />
  </div>
{:else if drag}
  <div class="ghost" style="width:{drag.w}px;transform:translate({drag.x - drag.dx}px, {drag.y - drag.dy}px)" aria-hidden="true">
    {#if drag.kind === 'item'}
      <div class="row">
        {@render rowBody(drag.ticker, [drag.row.name], drag.row.spark, drag.row.price, itemMove(drag.row, win))}
      </div>
    {:else}
      <div class="sec-head"><span class="sec-toggle"><span class="sec-name">{drag.label}</span></span></div>
    {/if}
  </div>
{/if}

<style>
  .brand-row { display: flex; align-items: center; justify-content: space-between; }
  .brand-actions { display: flex; align-items: center; gap: 8px; }
  /* theme + profile: one icon button, the pill states (outline hover, ink pressed) */
  .btn-icon { width: 28px; height: 28px; display: grid; place-items: center; cursor: pointer; padding: 0;
    background: transparent; color: var(--muted); border: var(--bw) solid var(--hairline); border-radius: 999px;
    transition: color .12s ease, border-color .12s ease, background .12s ease; }
  .btn-icon:hover { color: var(--ink); border-color: var(--ink); }
  .btn-icon:active { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .btn-icon svg { width: 16px; height: 16px; display: block; }
  .profile-wrap { position: relative; display: flex; }


  /* scrollable rail — scrollbar chrome hidden. position: relative so row
     offsets resolve against it for drop hit-testing. */
  .rail { position: relative; flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column;
    margin-top: 12px; padding-bottom: 8px; scrollbar-width: none; -ms-overflow-style: none; }
  .rail::-webkit-scrollbar { width: 0; height: 0; display: none; }
  .rail-empty { padding: 10px 11px; font-size: var(--fs-body); color: var(--muted); }
  /* loading rows: the real row grid, bars in place of badge / spark / figures */
  .sk-row, .sk-row:hover, .sk-row:active { cursor: default; animation: none; border-color: transparent; background: transparent; }
  .sk-row .r-id { gap: 6px; }
  .sk-row .r-fig { align-items: flex-end; gap: 6px; }
  .sk-badge { width: 44px; height: 18px; }
  .sk-spark { width: 56px; height: 20px; }
  .sk-pill { width: 44px; height: 16px; border-radius: 999px; }

  .sec { display: flex; flex-direction: column; gap: 2px; }
  .sec + .sec { margin-top: 14px; }

  /* section head: name on the badge edge (row padding 10 + border 1), chevron
     hanging in the gutter left of it; count muted; actions on the right */
  .sec-head { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 6px;
    min-height: 26px; padding-left: 11px; margin-bottom: 2px; }
  .sec-toggle { flex: 1 1 auto; min-width: 0; display: flex; align-items: baseline; gap: 6px; padding: 3px 0;
    background: transparent; border: 0; font: inherit; color: var(--ink); cursor: pointer; text-align: left;
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
  .sec-name { font-size: var(--fs-title); font-weight: 600; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sec-count { font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); font-variant-numeric: tabular-nums; }
  .chev { position: absolute; left: 0; top: 50%; width: 10px; height: 10px; margin-top: -5px; color: var(--muted);
    transition: transform .12s ease; }
  .chev.shut { transform: rotate(-90deg); }
  .sec-toggle:hover .chev, .sec-toggle:hover .sec-count { color: var(--ink); }
  .sec-win { display: inline-flex; gap: 2px; }

  /* list head actions: hidden until the head is hovered — ActivityLog's row actions */
  .sec-acts { display: flex; gap: 2px; opacity: 0; pointer-events: none; transition: opacity .12s ease; }
  .sec-head:hover .sec-acts, .sec-head:focus-within .sec-acts { opacity: 1; pointer-events: auto; }
  .sec-ic { width: 22px; height: 22px; padding: 0; border: 0; border-radius: 999px; background: transparent;
    color: var(--muted); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: background .12s ease, color .12s ease; }
  .sec-ic:hover { background: var(--hairline); color: var(--ink); }
  .sec-rename { flex: 1 1 auto; min-width: 0; height: 26px; box-sizing: border-box; padding: 0 8px; margin-left: -8px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); outline: 0;
    font: inherit; font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .sec-confirm { justify-content: flex-start; }
  .sec-ask { flex: 1 1 auto; font-size: var(--fs-body); font-weight: 500; color: var(--ink); white-space: nowrap; }
  .sec-hint { padding: 10px 11px; border: var(--bw) dashed var(--hairline); border-radius: var(--r);
    font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  /* a collapsed list under the cursor: the head is the whole target */
  .sec.target > .sec-head { background: var(--hover); border-radius: var(--r); }

  /* ── a row: two stat lines. static ink border on hover, full ink inversion
     while pressed. no sweeps, no washes. ── */
  .row { width: 100%; box-sizing: border-box; padding: 8px 10px;
    border: var(--bw) solid transparent; border-radius: var(--r);
    background: transparent; cursor: pointer; text-align: left; font: inherit; color: var(--ink);
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none;
    transition: border-color .12s ease, background .12s ease;
    animation: rise .42s cubic-bezier(.2, .8, .3, 1) backwards; animation-delay: calc(var(--i, 0) * 26ms); }
  .row:hover { border-color: var(--ink); }
  .row:active { background: var(--ink); border-color: var(--ink); }
  .row:active .r-sub, .row:active .r-px { color: var(--paper); }
  /* the holding being copied out keeps its place, outlined as the source */
  .row.src, .row.src:hover { border-style: dashed; border-color: var(--muted); background: transparent; }
  /* the button is still held down while it's dragged — don't let :active invert it */
  .row.src:active .r-sub { color: var(--muted); }
  .row.src:active .r-px { color: var(--ink); }

  /* identity | month sparkline | figures — the sparkline column is fixed so
     every row's line sits on the same axis; the figures column right-aligns */
  .row { display: grid; grid-template-columns: minmax(0, 1fr) 56px auto; align-items: center; gap: 8px; }
  .r-col { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .r-id { align-items: flex-start; }
  .r-fig { align-items: flex-end; }
  .r-sub { display: flex; gap: 6px; min-width: 0; max-width: 100%; font-family: var(--num); font-weight: 500;
    font-size: var(--fs-meta); color: var(--muted); font-variant-numeric: tabular-nums; }
  .r-sub span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  .r-spark { display: flex; justify-content: center; }
  .r-px { font-family: var(--num); font-weight: 500; font-size: var(--fs-body); color: var(--ink); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .r-day { font-family: var(--num); font-weight: 500; font-size: var(--fs-meta); font-variant-numeric: tabular-nums; }
  .r-spark.up { color: var(--gain-ink); }
  .r-spark.down { color: var(--loss-ink); }

  /* the landing slot: where the dragged row / list will drop */
  .slot-ph { box-sizing: border-box; border: var(--bw) dashed var(--ink); border-radius: var(--r); background: var(--hover); }

  /* the lifted copy under the cursor — the pressable-card lift, held */
  .ghost { position: fixed; top: 0; left: 0; z-index: 300; pointer-events: none; box-sizing: border-box;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh-pop); }
  .ghost .row { border-color: transparent; animation: none; }
  .ghost-chip { padding: 4px; }
  .ghost .sec-head { min-height: 30px; }

  /* drop targets under the rail: + New list at rest; New list / Remove while dragging */
  .rail-drop { flex: 0 0 auto; display: flex; gap: 8px; margin-top: 8px; }
  .zone { flex: 1 1 0; min-height: 34px; box-sizing: border-box; display: flex; align-items: center; justify-content: center;
    padding: 0 10px; background: transparent; border: var(--bw) dashed var(--hairline); border-radius: var(--r);
    font: inherit; font-size: var(--fs-body); font-weight: 500; color: var(--muted); cursor: pointer;
    transition: border-color .12s ease, color .12s ease, background .12s ease; }
  .zone:hover, .zone.live { border-color: var(--muted); color: var(--ink); }
  .zone.over { border-style: solid; border-color: var(--ink); background: var(--hover); }
  .zone-rm.over { border-color: var(--loss); color: var(--loss); background: color-mix(in srgb, var(--loss) 10%, transparent); }

  :global(html.list-dragging), :global(html.list-dragging *) { cursor: grabbing !important; user-select: none; }
  :global(html.list-dragging) .row:hover:not(.src) { border-color: transparent; }

  @keyframes rise { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .row { animation: none; }
    .chev { transition: none; }
  }

  /* On mobile the sidebar collapses to a top nav bar — the rail would be huge there. */
  @media (max-width: 700px) {
    .rail, .rail-drop { display: none; }
  }
</style>

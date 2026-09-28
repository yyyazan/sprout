<script>
  // Mobile Holdings pane — the sidebar rail rebuilt for a full phone column:
  // richer rows (price + live move + value + weight), a D/W/M move window, and
  // the user's lists underneath. Lists work like the rail (lib/listDrag):
  // hold a row to pick it up (holdings copy in, list rows move), hold a list's
  // name to reorder the lists. Mid-drag, New list / Remove take over the dock.
  // Swipe a list row left to remove it, a list name left to rename or delete
  // it (SwipeRow).
  import { onMount, flushSync } from 'svelte';
  import { flip } from 'svelte/animate';
  import { holdings, moves, lists, openStock, cardToHolding, createList, renameList, deleteList, setMembership } from '$lib/stores.js';
  import { ListDrag, previewLists, slotListOf, dropLayout, saveIfMoved } from '$lib/listDrag.svelte.js';
  import TickerBadge from '../TickerBadge.svelte';
  import SwipeRow from '../SwipeRow.svelte';

  const WINS = [['day', 'D'], ['wk', 'W'], ['mo', 'M']];
  let win = $state('mo');

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
  const pct = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
  const wt = (n) => (n ?? 0).toFixed(1) + '%';
  const usd = (n) => {
    if (n == null) return '—';
    const a = Math.abs(n);
    if (a >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'k';
    return '$' + Math.round(n);
  };
  const px = (n) => (n == null ? '—' : '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

  function openTicker(ticker, name) {
    const card = ($holdings ?? []).find((c) => c.ticker === ticker);
    openStock({ ticker, name: card?.company_name ?? name, holding: card ? cardToHolding(card) : null });
  }

  // ── folded lists (per viewer) ──
  const COLLAPSE_KEY = 'sprout-phone-collapsed';
  let collapsed = $state((() => {
    try { return JSON.parse(localStorage.getItem(COLLAPSE_KEY)) ?? []; } catch { return []; }
  })());
  const isCollapsed = (id) => collapsed.includes(id);
  function toggle(id) {
    collapsed = isCollapsed(id) ? collapsed.filter((x) => x !== id) : [...collapsed, id];
    try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify(collapsed)); } catch {}
  }

  // ── rename, delete, new list ──
  // iOS only raises the keyboard for a focus() inside the tap itself, so the
  // field renders synchronously (flushSync) and focuses in the same handler.
  let renaming = $state(null);
  let renameVal = $state('');
  let renameEl = $state();
  let confirmDel = $state(null);

  function startRename(L) {
    confirmDel = null;
    renaming = L.id;
    renameVal = L.name;
    flushSync();
    renameEl?.focus();
    renameEl?.select();
  }
  function commitRename(L) {
    if (renaming !== L.id) return;
    const name = renameVal.trim();
    renaming = null;
    if (name && name !== L.name) renameList(L.id, name);
  }

  // { tickers } while the new-list field is up. A row dropped on New list
  // brings its ticker; that list is made even if the name is left blank.
  let naming = $state(null);
  let nameVal = $state('');
  let nameEl = $state();
  let pendingSave = null;

  function startNaming(tickers = []) {
    naming = { tickers };
    nameVal = '';
    flushSync();
    nameEl?.focus();
  }
  async function commitNaming() {
    if (!naming) return;
    const { tickers } = naming;
    naming = null;
    const name = nameVal.trim() || (tickers.length ? 'New list' : '');
    if (!name) return;
    await pendingSave; // the ticker leaves its old list before the new one lands
    createList(name, tickers);
  }

  // ── drag and drop ──
  let rootEl;
  let scroller = null;
  onMount(() => { scroller = rootEl.closest('.m-pane') ?? rootEl; });

  const dnd = new ListDrag({
    root: () => rootEl,
    scroller: () => scroller,
    // the visible band: pane top to whatever covers the bottom (drop bar or dock)
    edges: () => {
      const r = scroller.getBoundingClientRect();
      const cover = (document.querySelector('.mho-drop') ?? document.querySelector('.m-dock'))?.getBoundingClientRect();
      return { top: r.top, bottom: cover ? cover.top : r.bottom };
    },
    collapsed: isCollapsed,
    canStart: () => renaming == null && naming == null,
    onDrop: (d) => {
      pendingSave = saveIfMoved(dropLayout($lists ?? [], d));
      if (d.over.zone === 'new') startNaming([d.ticker]);
    },
  });
  const grab = dnd.grab;
  const drag = $derived(dnd.drag);
  const shown = $derived(previewLists($lists ?? [], drag));
  const slotList = $derived(slotListOf(drag));

  // the ghost and drop bar are position: fixed, which the pager's transformed
  // track would re-anchor to itself — so they mount on <body>
  const toBody = (node) => {
    document.body.appendChild(node);
    return { destroy: () => node.remove() };
  };
</script>

{#snippet rowBody(ticker, name, sub, price, move)}
  <span class="mho-main">
    <span class="mho-line">
      <TickerBadge sym={ticker} />
      <span class="mho-name">{name}</span>
    </span>
    {#if sub}<span class="mho-sub">{#each sub as s}<span>{s}</span>{/each}</span>{/if}
  </span>
  <span class="mho-right">
    <span class="mho-px">{px(price)}</span>
    <span class="pct-pill {(move ?? 0) >= 0 ? 'up' : 'down'}">{pct(move)}</span>
  </span>
{/snippet}

{#snippet chevron(id)}
  <svg class="mho-chev" class:shut={isCollapsed(id)} viewBox="0 0 10 10" aria-hidden="true">
    <path d="M2.5 3.75 5 6.25 7.5 3.75" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
{/snippet}

<div class="mho" bind:this={rootEl}>
  <div class="mho-head">
    <span class="mho-title">Holdings</span>
    <div class="mho-win" role="group" aria-label="move window">
      {#each WINS as [k, label] (k)}
        <button class="btn btn-sm btn-mono" class:on={win === k} onclick={() => (win = k)}>{label}</button>
      {/each}
    </div>
  </div>

  {#if $holdings === null}
    {#each [0, 1, 2, 3, 4, 5] as i (i)}
      <div class="mho-row sk-row" aria-hidden="true">
        <span class="skel sk-badge"></span><span class="skel skel-t" style="width:40%"></span>
        <span class="skel skel-t" style="width:52px;margin-left:auto"></span>
      </div>
    {/each}
  {:else if rows.length === 0}
    <div class="mho-empty">No holdings yet.</div>
  {:else}
    {#each rows as c (c.ticker)}
      <button class="mho-row" class:src={drag?.from === 'holdings' && drag.ticker === c.ticker}
        use:grab={{ kind: 'item', ticker: c.ticker, from: 'holdings' }}
        onclick={() => openTicker(c.ticker, c.company_name)}>
        {@render rowBody(c.ticker, c.company_name, [usd(c.market_value), wt(c.position_pct)],
          $moves[c.ticker]?.spot ?? c.current_price, moveOf(c, win))}
      </button>
    {/each}
  {/if}

  {#each shown as L (L.id)}
    <section class="mho-sec" data-list={L.id} animate:flip={{ duration: 160 }}
      class:target={drag?.kind === 'item' && drag.over?.listId === L.id && isCollapsed(L.id)}>
      {#if drag?.kind === 'list' && drag.listId === L.id}
        <div class="mho-ph" style="height:{drag.h}px"></div>
      {:else if confirmDel === L.id}
        <div class="mho-lhead">
          <span class="mho-ask">Delete list?</span>
          <button class="btn btn-sm btn-danger" onclick={() => { confirmDel = null; deleteList(L.id); }}>Delete</button>
          <button class="btn btn-sm btn-quiet" onclick={() => (confirmDel = null)}>Cancel</button>
        </div>
      {:else}
        {#if renaming === L.id}
          <div class="mho-lhead">
            <input class="mho-field mho-rename" type="text" bind:this={renameEl} bind:value={renameVal}
              maxlength="40" aria-label="List name" enterkeyhint="done"
              onkeydown={(e) => { if (e.key === 'Enter') commitRename(L); else if (e.key === 'Escape') renaming = null; }}
              onblur={() => commitRename(L)} />
          </div>
        {:else}
          <SwipeRow actions={[
            { label: 'Rename', onclick: () => startRename(L) },
            { label: 'Delete', tone: 'loss', onclick: () => (confirmDel = L.id) },
          ]}>
            <div class="mho-lhead">
              <button class="mho-ltoggle" aria-expanded={!isCollapsed(L.id)}
                use:grab={{ kind: 'list', listId: L.id, label: L.name }}
                onclick={() => toggle(L.id)}>
                {@render chevron(L.id)}
                <span class="mho-title mho-lname">{L.name}</span>
                {#if L.items.length}<span class="mho-count">{L.items.length}</span>{/if}
              </button>
            </div>
          </SwipeRow>
        {/if}
        {#if !isCollapsed(L.id)}
          {#each L.items as it (it.ticker)}
            <div class="mho-slot" data-slot={it.ticker} animate:flip={{ duration: 160 }}>
              {#if slotList === L.id && it.ticker === drag.ticker}
                <div class="mho-ph" style="height:{drag.h}px"></div>
              {:else}
                <SwipeRow actions={[{ label: 'Remove', tone: 'loss', onclick: () => setMembership(it.ticker, L.id, false) }]}>
                  <button class="mho-row" use:grab={{ kind: 'item', ticker: it.ticker, from: L.id, row: it }}
                    onclick={() => openTicker(it.ticker, it.name)}>
                    {@render rowBody(it.ticker, it.name, null, it.price, itemMove(it, win))}
                  </button>
                </SwipeRow>
              {/if}
            </div>
          {:else}
            <div class="mho-hint">Hold a stock to drag it here</div>
          {/each}
        {/if}
      {/if}
    </section>
  {/each}

  {#if naming}
    <input class="mho-field mho-newname" type="text" bind:this={nameEl} bind:value={nameVal}
      placeholder="List name" maxlength="40" aria-label="New list name" enterkeyhint="done"
      onkeydown={(e) => { if (e.key === 'Enter') commitNaming(); else if (e.key === 'Escape') { nameVal = ''; commitNaming(); } }}
      onblur={commitNaming} />
  {:else if $lists !== null}
    <button class="mho-new" onclick={() => startNaming()}>+ New list</button>
  {/if}
</div>

{#if drag?.kind === 'item'}
  <div class="mho-drop" use:toBody>
    <div class="mho-zone" class:over={drag.over?.zone === 'new'} data-zone="new">New list</div>
    {#if drag.from !== 'holdings'}
      <div class="mho-zone mho-zone-rm" class:over={drag.over?.zone === 'remove'} data-zone="remove">Remove</div>
    {/if}
  </div>
{/if}

{#if drag?.over?.zone}
  <!-- over a zone the lift shrinks to its badge, held clear above the finger so
       the zone's label stays readable -->
  <div class="mho-ghost mho-ghost-chip" use:toBody aria-hidden="true"
    style="transform:translate({drag.x - 32}px, {drag.y - 76}px)">
    <TickerBadge sym={drag.ticker} />
  </div>
{:else if drag}
  <div class="mho-ghost" use:toBody aria-hidden="true"
    style="width:{drag.w + 16}px;transform:translate({drag.x - drag.dx - 8}px, {drag.y - drag.dy}px)">
    {#if drag.kind === 'item'}
      <div class="mho-row">{@render rowBody(drag.ticker, drag.row.name, null, drag.row.price, itemMove(drag.row, win))}</div>
    {:else}
      <div class="mho-lhead"><span class="mho-title">{drag.label}</span></div>
    {/if}
  </div>
{/if}

<style>
  /* positioned: the drag hit test measures rows against it. Swiped rows reach
     through the pane's 14px gutter so their actions meet the screen edge. */
  .mho { position: relative; --sw-bleed: 14px; }

  .mho-head { display: flex; align-items: center; justify-content: space-between;
    padding: calc(33px + env(safe-area-inset-top)) 0 6px; }
  .mho-title { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .mho-win { display: inline-flex; gap: 2px; }

  .mho-empty { padding: 14px 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .sk-row { cursor: default; }
  .sk-badge { width: 44px; height: 18px; flex: 0 0 auto; }

  /* ~56px touch rows: identity left, price + move right. No selection or
     callout, so a hold picks the row up instead of the text. */
  .mho-row { position: relative; width: 100%; display: flex; align-items: center; gap: 12px; min-height: 56px;
    padding: 10px 0; border: 0; border-bottom: var(--bw) solid var(--hairline); border-radius: 0;
    background: transparent; cursor: pointer; text-align: left; font: inherit; color: var(--ink);
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; -webkit-tap-highlight-color: transparent; }
  .mho-row:active { background: var(--hover); }

  .mho-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
  .mho-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .mho-name { font-size: var(--fs-body); font-weight: 500; color: var(--muted); min-width: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mho-sub { display: flex; gap: 10px; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500;
    color: var(--muted); font-variant-numeric: tabular-nums; }

  .mho-right { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
  .mho-px { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    font-variant-numeric: tabular-nums; }

  /* ── lists ── */
  .mho-sec { display: flex; flex-direction: column; margin-top: 16px; }
  /* head: name on the badge edge, chevron hanging in the pane gutter, count
     muted; rename + delete sit behind a left swipe */
  .mho-lhead { display: flex; align-items: center; gap: 4px; min-height: 44px; }
  .mho-ltoggle { position: relative; flex: 1 1 auto; min-width: 0; min-height: 44px; display: flex; align-items: center; gap: 6px;
    padding: 0; background: transparent; border: 0; font: inherit; color: var(--ink); cursor: pointer; text-align: left;
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; -webkit-tap-highlight-color: transparent; }
  .mho-lname { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mho-count { font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); font-variant-numeric: tabular-nums; }
  .mho-chev { position: absolute; left: -12px; top: 50%; width: 10px; height: 10px; margin-top: -5px; color: var(--muted);
    transition: transform .12s ease; }
  .mho-chev.shut { transform: rotate(-90deg); }
  .mho-ask { flex: 1 1 auto; font-size: var(--fs-body); font-weight: 500; color: var(--ink); }
  .mho-hint { margin: 4px 0; padding: 12px; border: var(--bw) dashed var(--hairline); border-radius: var(--r);
    font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  /* a folded list under the finger: the head is the whole target */
  .mho-sec.target .mho-lhead { background: var(--hover); border-radius: var(--r); }

  /* fields: the sidebar rename box; 16px comes from the app.css iOS zoom guard */
  .mho-field { box-sizing: border-box; min-width: 0; height: 40px; padding: 0 10px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); outline: 0;
    font: inherit; font-weight: 600; color: var(--ink); }
  .mho-field::placeholder { color: var(--muted); font-weight: 500; }
  .mho-rename { flex: 1 1 auto; margin-left: -11px; }
  .mho-newname { width: 100%; margin-top: 18px; }
  .mho-new { width: 100%; min-height: 44px; margin-top: 18px; padding: 0 10px; background: transparent;
    border: var(--bw) dashed var(--hairline); border-radius: var(--r); cursor: pointer;
    font: inherit; font-size: var(--fs-body); font-weight: 500; color: var(--muted); -webkit-tap-highlight-color: transparent; }
  .mho-new:active { border-color: var(--muted); color: var(--ink); }

  /* ── drag states: the sidebar's, on the phone row ── */
  /* the landing slot, and the source a holding is copied out of — both
     reach 8px into the gutter so the dashed box clears the badge */
  .mho-ph { box-sizing: border-box; margin: 0 -8px; border: var(--bw) dashed var(--ink); border-radius: var(--r);
    background: var(--hover); }
  .mho-row.src::after { content: ''; position: absolute; inset: 2px -8px; pointer-events: none;
    border: var(--bw) dashed var(--muted); border-radius: var(--r); }
  .mho-row.src:active { background: transparent; }

  /* the lifted copy under the finger: the pressable-card lift, held */
  .mho-ghost { position: fixed; top: 0; left: 0; z-index: 300; pointer-events: none; box-sizing: border-box;
    padding: 0 8px; background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh-pop); }
  .mho-ghost .mho-row { border-bottom: 0; }
  .mho-ghost-chip { padding: 4px; }

  /* New list / Remove: over the dock for as long as a row is held */
  .mho-drop { position: fixed; left: 0; right: 0; bottom: 0; z-index: 150; box-sizing: border-box;
    display: flex; gap: 8px; height: calc(56px + env(safe-area-inset-bottom));
    padding: 8px 14px calc(8px + env(safe-area-inset-bottom));
    background: var(--surface); border-top: var(--bw) solid var(--hairline); }
  .mho-zone { flex: 1 1 0; display: flex; align-items: center; justify-content: center;
    border: var(--bw) dashed var(--muted); border-radius: var(--r);
    font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    transition: border-color .12s ease, color .12s ease, background .12s ease; }
  .mho-zone.over { border-style: solid; border-color: var(--ink); background: var(--hover); }
  .mho-zone-rm.over { border-color: var(--loss); color: var(--loss); background: color-mix(in srgb, var(--loss) 10%, transparent); }

  @media (prefers-reduced-motion: reduce) { .mho-chev { transition: none; } }
</style>

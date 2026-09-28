<script>
  // The stock view's list pill: which sidebar lists hold this ticker. The pill
  // names the list (or the count), ink when it's in any; the popover toggles
  // membership per list and can start a new one. Same panel as ProfileMenu.
  import { onMount, flushSync } from 'svelte';
  import { lists, loadLists, setMembership, createList } from '$lib/stores.js';

  let { ticker } = $props();
  const sym = $derived((ticker || '').toUpperCase());

  let open = $state(false);
  let naming = $state(false);
  let name = $state('');
  let root;
  let nameEl = $state();

  onMount(() => { loadLists(); });

  const memberOf = $derived(new Set(($lists ?? []).filter((L) => L.items.some((i) => i.ticker === sym)).map((L) => L.id)));
  const label = $derived.by(() => {
    if (!memberOf.size) return '+ Add to list';
    if (memberOf.size > 1) return `✓ ${memberOf.size} lists`;
    return '✓ ' + ($lists ?? []).find((L) => memberOf.has(L.id))?.name;
  });

  $effect(() => {
    if (!open) { naming = false; return; }
    const onDoc = (e) => { if (root && !root.contains(e.target)) open = false; };
    // stop here so the stock view's own Escape (close the view) doesn't also fire
    const onKey = (e) => { if (e.key === 'Escape') { e.stopPropagation(); open = false; } };
    const id = setTimeout(() => document.addEventListener('click', onDoc), 0);
    document.addEventListener('keydown', onKey);
    return () => {
      clearTimeout(id);
      document.removeEventListener('click', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  });

  // render + focus inside the tap: iOS won't raise the keyboard after an await
  function startNew() {
    naming = true;
    name = '';
    flushSync();
    nameEl?.focus();
  }
  function commitNew() {
    const n = name.trim();
    naming = false;
    if (n) createList(n, [sym]);
  }
</script>

<div class="lp" bind:this={root}>
  <button class="btn btn-line lp-pill" class:on={memberOf.size > 0} aria-haspopup="menu" aria-expanded={open}
    onclick={() => (open = !open)}>
    <span class="lp-label">{label}</span>
  </button>
  {#if open}
    <div class="lp-menu" role="menu" aria-label="Lists">
      {#each $lists ?? [] as L (L.id)}
        {@const on = memberOf.has(L.id)}
        <button class="lp-item" role="menuitemcheckbox" aria-checked={on} onclick={() => setMembership(sym, L.id, !on)}>
          <span class="lp-box" class:on aria-hidden="true">
            {#if on}<svg viewBox="0 0 10 10"><path d="M2.2 5.2 4.2 7.2 7.8 3" /></svg>{/if}
          </span>
          <span class="lp-name">{L.name}</span>
          <span class="lp-count">{L.items.length}</span>
        </button>
      {/each}
      {#if naming}
        <input class="lp-in" bind:this={nameEl} bind:value={name} placeholder="List name" maxlength="40"
          onkeydown={(e) => { if (e.key === 'Enter') commitNew(); else if (e.key === 'Escape') { e.stopPropagation(); naming = false; } }}
          onblur={commitNew} aria-label="New list name" />
      {:else}
        <button class="lp-item lp-new" onclick={startNew}>+ New list</button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .lp { position: relative; display: flex; }
  .lp-pill { max-width: 220px; }
  .lp-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; }

  .lp-menu { position: absolute; top: calc(100% + 6px); right: 0; z-index: 30; min-width: 196px; max-width: 260px;
    display: flex; flex-direction: column; padding: 5px; gap: 1px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .lp-item { width: 100%; display: flex; align-items: center; gap: 9px; padding: 7px 9px; cursor: pointer;
    background: transparent; border: 0; border-radius: 2px; text-align: left;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink); }
  .lp-item:hover { background: var(--hover); }
  .lp-name { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .lp-count { font-family: var(--num); font-size: var(--fs-meta); color: var(--muted); font-variant-numeric: tabular-nums; }
  /* checked = ink inversion, the system's selected state */
  .lp-box { flex: 0 0 auto; width: 14px; height: 14px; box-sizing: border-box; display: grid; place-items: center;
    border: var(--bw) solid var(--ink); border-radius: 3px; }
  .lp-box.on { background: var(--ink); }
  .lp-box svg { width: 10px; height: 10px; fill: none; stroke: var(--paper); stroke-width: 1.6;
    stroke-linecap: round; stroke-linejoin: round; }
  .lp-new { color: var(--muted); border-top: var(--bw) solid var(--hairline); border-radius: 0; margin-top: 3px; padding-top: 9px; }
  .lp-new:hover { color: var(--ink); }
  .lp-in { margin-top: 4px; height: 28px; box-sizing: border-box; padding: 0 8px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); outline: 0;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink); }
  .lp-in::placeholder { color: var(--muted); }
</style>

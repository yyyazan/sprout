<script>
  // ⌘K search on routes without the dashboard stage. Same strip and result
  // rows as the stage's inline search (app.css .strip / .ss-*), in a modal.
  // Debounced calls to /api/search; ↑ ↓ Enter, Esc to close.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { noteSearchKinds } from '$lib/stores.js';
  import TickerBadge from './TickerBadge.svelte';

  let { onClose, onPick, holdings = [] } = $props();

  let q = $state('');
  let results = $state([]);
  let active = $state(0);
  let loading = $state(false);
  let input = $state();

  // empty query → offer the user's own holdings as instant quick-access
  const list = $derived(q.trim() ? results : holdings);

  let seq = 0;
  let timer = null;
  $effect(() => {
    const query = q.trim();
    if (timer) clearTimeout(timer);
    if (!query) { results = []; loading = false; return; }
    loading = true;
    const mine = ++seq;
    timer = setTimeout(async () => {
      try {
        const r = await api.search(query);
        if (mine !== seq) return;        // a newer keystroke superseded this one
        results = r.results ?? [];
        noteSearchKinds(results);
        active = 0;
      } catch {
        if (mine === seq) results = [];
      } finally {
        if (mine === seq) loading = false;
      }
    }, 180);
  });

  function pick(r) { if (r) onPick?.(r); }

  function onKey(e) {
    if (e.key === 'Escape') { onClose?.(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, list.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
    else if (e.key === 'Enter') { e.preventDefault(); pick(list[active]); }
  }

  onMount(() => { input?.focus(); });
</script>

<div class="ss-scrim" role="presentation" onclick={() => onClose?.()}>
  <div class="ss" role="dialog" aria-modal="true" aria-label="Search stocks" onclick={(e) => e.stopPropagation()}>
    <div class="strip strip-active">
      <span class="strip-icon" aria-hidden="true"></span>
      <input bind:this={input} bind:value={q} onkeydown={onKey} type="text" placeholder="Search"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
      {#if loading}<span class="strip-spin" aria-hidden="true"></span>{/if}
      <button class="strip-esc" onclick={() => onClose?.()}>esc</button>
    </div>

    <div class="ss-panel">
      {#if q.trim() && !loading && results.length === 0}
        <div class="ss-empty">No matches for “{q.trim()}”.</div>
      {:else if list.length}
        {#if !q.trim()}<div class="ss-section">Your holdings</div>{/if}
        <ul class="ss-list" role="listbox">
          {#each list as r, i (r.symbol)}
            <li>
              <button class="ss-item" class:active={i === active} role="option" aria-selected={i === active}
                      onmouseenter={() => (active = i)} onclick={() => pick(r)}>
                <span class="ss-sym"><TickerBadge sym={r.symbol} size="md" /></span>
                <span class="ss-name">{r.name}</span>
                <span class="ss-meta"><span>{r.type}</span>{#if r.exchange}<span>{r.exchange}</span>{/if}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <div class="ss-empty">Search the whole market, not just your holdings.</div>
      {/if}
    </div>
  </div>
</div>

<style>
  .ss-scrim { position: fixed; inset: 0; z-index: 210; display: flex; justify-content: center; align-items: flex-start;
    padding: 12vh 20px 20px; background: rgba(0, 0, 0, .58); backdrop-filter: blur(3px);
    animation: ss-fade .14s ease; }
  @keyframes ss-fade { from { opacity: 0; } to { opacity: 1; } }
  /* the stage's search, lifted into a modal: strip on top, results card under it */
  .ss { width: min(620px, 96vw); display: flex; flex-direction: column; gap: 10px;
    animation: ss-rise .18s cubic-bezier(.34, 1.4, .5, 1); }
  @keyframes ss-rise { from { transform: translateY(-10px); opacity: 0; } to { transform: none; opacity: 1; } }
  .ss-panel { max-height: 52vh; display: flex; flex-direction: column; overflow: hidden;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); }
</style>

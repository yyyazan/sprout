<script>
  // Command-palette stock search. Type a ticker or company, pick a result → onPick.
  // Debounced calls to /api/search; full keyboard nav (↑ ↓ Enter, Esc to close).
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

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
    <div class="ss-bar">
      <span class="ss-icon" aria-hidden="true">⌕</span>
      <input
        bind:this={input}
        bind:value={q}
        onkeydown={onKey}
        type="text"
        placeholder="Search any stock — ticker or company…"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
      {#if loading}<span class="ss-spin" aria-hidden="true"></span>{/if}
      <kbd class="ss-esc">esc</kbd>
    </div>

    {#if q.trim() && !loading && results.length === 0}
      <div class="ss-empty">No matches for “{q.trim()}”.</div>
    {:else if list.length}
      {#if !q.trim()}<div class="ss-section">Your holdings</div>{/if}
      <ul class="ss-list" role="listbox">
        {#each list as r, i (r.symbol)}
          <li>
            <button class="ss-item" class:active={i === active} role="option" aria-selected={i === active}
                    onmouseenter={() => (active = i)} onclick={() => pick(r)}>
              <span class="ss-sym">{r.symbol}</span>
              <span class="ss-name">{r.name}</span>
              <span class="ss-meta">{r.type}{#if r.exchange} · {r.exchange}{/if}</span>
            </button>
          </li>
        {/each}
      </ul>
    {:else if !q.trim()}
      <div class="ss-hint">Search the whole market — not just your holdings.</div>
    {/if}
  </div>
</div>

<style>
  .ss-scrim { position: fixed; inset: 0; z-index: 210; display: flex; justify-content: center; align-items: flex-start;
    padding: 12vh 20px 20px; background: rgba(0, 0, 0, .58); backdrop-filter: blur(3px);
    animation: ss-fade .14s ease; }
  @keyframes ss-fade { from { opacity: 0; } to { opacity: 1; } }
  .ss { width: min(620px, 96vw); background: var(--surface); border: var(--bw) solid var(--ink);
    border-radius: calc(var(--r) + 2px); box-shadow: 8px 8px 0 var(--ink); overflow: hidden;
    animation: ss-rise .18s cubic-bezier(.34, 1.4, .5, 1); }
  @keyframes ss-rise { from { transform: translateY(-10px); opacity: 0; } to { transform: none; opacity: 1; } }

  .ss-bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: var(--bw) solid var(--ink); }
  .ss-icon { font-size: 18px; color: var(--muted); }
  .ss-bar input { flex: 1; border: 0; outline: 0; background: transparent; color: var(--text);
    font-family: var(--sans); font-size: 17px; font-weight: 600; min-width: 0; }
  .ss-bar input::placeholder { color: var(--muted); font-weight: 500; }
  .ss-esc { font-family: var(--mono); font-size: 10px; color: var(--muted); border: 1.5px solid var(--muted); border-radius: 4px; padding: 1px 5px; }
  .ss-spin { width: 13px; height: 13px; border: 2px solid color-mix(in srgb, var(--ink) 25%, transparent); border-top-color: var(--brand); border-radius: 50%; animation: ss-rot .6s linear infinite; }
  @keyframes ss-rot { to { transform: rotate(360deg); } }

  .ss-list { list-style: none; margin: 0; padding: 6px; max-height: 52vh; overflow-y: auto; }
  .ss-item { width: 100%; display: flex; align-items: baseline; gap: 12px; padding: 10px 12px; cursor: pointer;
    border: 0; border-radius: var(--r); background: transparent; color: var(--ink); text-align: left; font: inherit; }
  .ss-item.active { background: var(--hover); }
  .ss-sym { flex: 0 0 auto; font-family: var(--mono); font-weight: 700; font-size: 14px; min-width: 64px; }
  .ss-name { flex: 1; min-width: 0; font-family: var(--sans); font-size: 13px; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ss-meta { flex: 0 0 auto; font-family: var(--mono); font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }

  .ss-empty, .ss-hint { padding: 18px 18px 20px; font-family: var(--mono); font-size: 13px; color: var(--muted); }
  .ss-section { padding: 12px 18px 2px; font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
</style>

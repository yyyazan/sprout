<script>
  // Identity popover hung off the profile icon (desktop sidebar + mobile header).
  // Only the panel lives here: each host keeps its own trigger button, because
  // the mobile one is styled by hero-contextual selectors that Svelte's scoped
  // CSS can't reach into a child component.
  import { api } from '$lib/api.js';

  let { open = false, onClose = () => {}, align = 'right' } = $props();

  let me = $state(null);
  let busy = $state(false);
  let panel;

  // Load identity the first time the menu is opened, not on every mount.
  $effect(() => {
    if (open && me === null) api.me().then((r) => (me = r)).catch(() => (me = {}));
  });

  $effect(() => {
    if (!open) return;
    const onDoc = (e) => { if (panel && !panel.contains(e.target)) onClose(); };
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    // defer: the click that opened the menu is still propagating
    const id = setTimeout(() => document.addEventListener('click', onDoc), 0);
    document.addEventListener('keydown', onKey);
    return () => {
      clearTimeout(id);
      document.removeEventListener('click', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  });

  async function signOut() {
    if (busy) return;
    busy = true;
    try { await api.logout(); } catch { /* clearing the cookie is best-effort */ }
    // Full reload rather than a client-side transition: stores.js caches
    // holdings/trades/watchlist at module scope and its loaders short-circuit
    // when populated, so a soft sign-out would leak the old account's data.
    location.reload();
  }
</script>

{#if open}
  <div class="pm" class:pm-left={align === 'left'} bind:this={panel} role="menu" aria-label="Account">
    <div class="pm-id">
      <span class="pm-name">{me?.name && me.name !== 'default' ? me.name : 'Signed in'}</span>
      <span class="pm-mail">{me?.email ?? 'Local session'}</span>
    </div>
    <button class="pm-item" type="button" role="menuitem" onclick={signOut} disabled={busy}>
      {busy ? 'Signing out…' : 'Sign out'}
    </button>
  </div>
{/if}

<style>
  .pm { position: absolute; top: calc(100% + 6px); right: 0; z-index: 30; min-width: 176px;
    display: flex; flex-direction: column; padding: 5px; gap: 2px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-shadow: var(--sh); }
  .pm-left { right: auto; left: 0; }
  .pm-id { display: flex; flex-direction: column; gap: 1px; padding: 6px 9px 8px; }
  .pm-name { font-family: var(--sans); font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .pm-mail { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  /* Cap below the panel's min-width: the sidebar clips overflow and the panel is
     right-aligned to the icon, so a long address would grow it off-screen. */
  .pm-name, .pm-mail { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pm-item { width: 100%; text-align: left; cursor: pointer; padding: 7px 9px;
    border: 0; border-top: var(--bw) solid var(--hairline); background: transparent; border-radius: 0 0 2px 2px;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink); }
  .pm-item:hover:not(:disabled) { background: var(--hover); }
  .pm-item:disabled { color: var(--muted); cursor: default; }
</style>

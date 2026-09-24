<script>
  // Identity popover hung off the profile icon (desktop sidebar + mobile header).
  // Only the panel lives here: each host keeps its own trigger button, because
  // the mobile one is styled by hero-contextual selectors that Svelte's scoped
  // CSS can't reach into a child component.
  import { api } from '$lib/api.js';
  import { fmt } from '$lib/format.js';

  let { open = false, onClose = () => {}, align = 'right' } = $props();

  let me = $state(null);
  let busy = $state(false);
  let panel;

  // Load identity the first time the menu is opened, not on every mount.
  $effect(() => {
    if (open && me === null) api.me().then((r) => (me = r)).catch(() => (me = {}));
  });

  // Cash reconciliation — the offset that reconciles computed cash to the
  // broker's actual balance. Previously only settable by hand-editing SQLite;
  // this is the one place a user can see and change it.
  let recon = $state(null);
  let editingRecon = $state(false);
  let reAmount = $state(''), reNote = $state('');
  let reSaving = $state(false), reError = $state(null);

  $effect(() => {
    if (open && recon === null) api.reconciliation().then((r) => (recon = r)).catch(() => (recon = {}));
  });

  function startEditRecon() {
    reAmount = recon?.offset_usd != null ? String(recon.offset_usd) : '0';
    reNote = recon?.note ?? '';
    reError = null;
    editingRecon = true;
  }
  const cancelEditRecon = () => (editingRecon = false);

  async function saveRecon() {
    if (reSaving) return;
    if (reAmount === '' || Number.isNaN(Number(reAmount))) { reError = 'Enter a number'; return; }
    reSaving = true; reError = null;
    try {
      const r = await api.setReconciliation({ offset_usd: Number(reAmount), note: reNote || null });
      if (r?.ok) { recon = r; editingRecon = false; }
      else reError = 'Save failed';
    } catch {
      reError = 'Save failed';
    } finally {
      reSaving = false;
    }
  }

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
    // holdings/trades/lists at module scope and its loaders short-circuit
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
    {#if editingRecon}
      <div class="pm-recon-edit">
        <label class="pm-recon-field">
          <span>Offset ($)</span>
          <input type="number" step="any" inputmode="decimal" bind:value={reAmount}
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveRecon(); } }} />
        </label>
        <label class="pm-recon-field">
          <span>Note</span>
          <input type="text" placeholder="optional" bind:value={reNote} maxlength="120"
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveRecon(); } }} />
        </label>
        {#if reError}<div class="pm-recon-err" role="alert">{reError}</div>{/if}
        <div class="pm-recon-actions">
          <button type="button" class="pm-recon-btn" disabled={reSaving} onclick={saveRecon}>{reSaving ? 'Saving…' : 'Save'}</button>
          <button type="button" class="pm-recon-btn pm-recon-quiet" onclick={cancelEditRecon}>Cancel</button>
        </div>
      </div>
    {:else}
      <button class="pm-item pm-recon-row" type="button" role="menuitem" onclick={startEditRecon}>
        <span>Cash offset</span>
        <span class="pm-recon-val">{recon ? fmt.signedMoney2(recon.offset_usd ?? 0) : '—'}</span>
      </button>
    {/if}
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

  .pm-recon-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .pm-recon-val { font-family: var(--num); font-variant-numeric: tabular-nums; color: var(--muted); }

  .pm-recon-edit { display: flex; flex-direction: column; gap: 6px; padding: 8px 9px;
    border-top: var(--bw) solid var(--hairline); }
  .pm-recon-field { display: flex; flex-direction: column; gap: 2px; }
  .pm-recon-field span { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .pm-recon-field input { width: 100%; box-sizing: border-box; height: 26px; padding: 0 7px;
    background: var(--paper); border: var(--bw) solid var(--ink); border-radius: var(--r);
    font-family: var(--num); font-size: 12px; font-weight: 600; color: var(--ink); }
  .pm-recon-field input::placeholder { color: var(--muted); font-family: var(--sans); font-weight: 500; }
  .pm-recon-field input[type="number"] { -moz-appearance: textfield; }
  .pm-recon-field input::-webkit-outer-spin-button, .pm-recon-field input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
  .pm-recon-err { color: var(--loss); font-family: var(--num); font-size: 11px; font-weight: 600; }
  .pm-recon-actions { display: flex; gap: 6px; padding-top: 2px; }
  .pm-recon-btn { flex: 1 1 auto; height: 24px; padding: 0 8px; box-sizing: border-box;
    border-radius: 999px; background: transparent; font-family: var(--sans); font-size: 11.5px; font-weight: 600;
    cursor: pointer; border: var(--bw) solid var(--hairline); color: var(--ink); }
  .pm-recon-btn:hover:not(:disabled) { border-color: var(--ink); }
  .pm-recon-btn:disabled { opacity: .5; cursor: default; }
  .pm-recon-quiet { color: var(--muted); }
</style>

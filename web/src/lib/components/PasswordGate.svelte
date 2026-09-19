<script>
  // Sign-in screen, shown by the layout when any API call hits the server gate
  // (401). Google is the front door; the password is the owner's fallback for
  // when OAuth config breaks, so it stays folded away behind a text link.
  // On success the server sets the session cookie and a reload refetches
  // everything cleanly under the new identity.
  import { api } from '$lib/api.js';

  let pw = $state('');
  let err = $state(false);
  let busy = $state(false);
  let showPw = $state(false);
  let oauth = $state(true);   // assume Google until /me says otherwise
  let inEl;

  // The OAuth callback bounces back to /?auth_error=… when sign-in is refused
  // (not on the allowlist, unverified email, expired state).
  const authError = $derived.by(() => {
    if (typeof window === 'undefined') return '';
    return new URLSearchParams(window.location.search).get('auth_error') ?? '';
  });

  // A 401 from /me still tells us whether Google is configured on this deploy.
  $effect(() => {
    api.me()
      .then((r) => (oauth = r?.oauth ?? false))
      .catch(() => {});
  });

  $effect(() => { if (showPw) inEl?.focus(); });

  async function unlock() {
    if (busy || !pw) return;
    busy = true;
    err = false;
    try {
      const r = await api.login(pw);
      if (r?.ok) { location.reload(); return; }
      err = true;
    } catch {
      err = true;
    } finally {
      busy = false;
    }
  }
</script>

<div class="gate" role="dialog" aria-modal="true" aria-label="Sign in to Sprout">
  <div class="gate-card" class:bad={err}>
    <div class="gate-brand">sprout</div>
    <div class="gate-sub">Private portfolio — sign in to continue</div>

    {#if authError}
      <div class="gate-err" role="alert">{authError}</div>
    {/if}

    {#if oauth}
      <a class="btn btn-line gate-google" href="/api/auth/google/login">Continue with Google</a>
    {/if}

    {#if showPw || !oauth}
      <div class="gate-pw">
        <input class="gate-in" type="password" placeholder="Owner password" bind:value={pw} bind:this={inEl}
          autocomplete="current-password" aria-label="Owner password"
          oninput={() => (err = false)}
          onkeydown={(e) => { if (e.key === 'Enter') unlock(); }} />
        <button class="btn btn-line gate-btn" onclick={unlock} disabled={busy || !pw}>Unlock</button>
        {#if err}<div class="gate-err" role="alert">Wrong password</div>{/if}
      </div>
    {:else}
      <button class="gate-alt" type="button" onclick={() => (showPw = true)}>Owner sign-in</button>
    {/if}
  </div>
</div>

<style>
  /* Opaque on purpose — nothing underneath should be readable while locked. */
  .gate { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
    background: var(--surface); padding: 24px; }
  .gate-card { display: flex; flex-direction: column; gap: 10px; width: min(320px, 100%);
    padding: 28px 24px; border: var(--bw) solid var(--ink); border-radius: var(--r); }
  .gate-card.bad { border-color: var(--loss); }
  .gate-brand { font-family: var(--sans); font-size: 22px; font-weight: 800; color: var(--ink); }
  .gate-sub { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500;
    color: var(--muted); margin-bottom: 8px; }
  .gate-google { height: 36px; display: grid; place-items: center; text-decoration: none; }
  .gate-pw { display: flex; flex-direction: column; gap: 10px; }
  .gate-in { box-sizing: border-box; width: 100%; height: 38px; padding: 0 12px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); background: transparent;
    outline: none; font-family: var(--sans); font-size: 16px; font-weight: 500; color: var(--text); }
  .gate-in::placeholder { color: var(--muted); opacity: .6; }
  .gate-btn { height: 34px; }
  .gate-btn:disabled { opacity: .4; cursor: default; }
  .gate-alt { align-self: flex-start; padding: 0; border: 0; background: transparent; cursor: pointer;
    font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .gate-alt:hover { color: var(--ink); }
  .gate-err { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--loss); }
</style>

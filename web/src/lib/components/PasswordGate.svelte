<script>
  // Sign-in screen, shown by the layout when any API call hits the server gate
  // (401). The garden is the backdrop — ambient only, no hover/click/drag, and
  // grown from a fixed decorative set since nobody's portfolio is loaded yet.
  // Google is the front door; the password is the owner's fallback, tucked
  // away as a quiet "secret" link at the foot of the screen.
  // On success the server sets the session cookie and a reload refetches
  // everything cleanly under the new identity.
  import { api } from '$lib/api.js';
  import GardenView from './GardenView.svelte';

  // Plant model is a deterministic hash of the ticker string and size follows
  // position_pct, so these seeds are just a stable, pleasant arrangement — not
  // anyone's holdings.
  const DECOR = [
    { ticker: 'SPROUT', position_pct: 30 },
    { ticker: 'FERN', position_pct: 22 },
    { ticker: 'MOSS', position_pct: 18 },
    { ticker: 'IVY', position_pct: 14 },
    { ticker: 'SAGE', position_pct: 10 },
    { ticker: 'REED', position_pct: 6 },
  ];

  // The bed's PLANT_SLOTS were composed for the dashboard band and pile up on
  // the right, with one landing behind the card. Compose our own in SCREEN
  // terms — `s` sideways (− left, + right), `d` toward the camera (+ nearer,
  // lower, bigger) — and rotate into world space through the camera's azimuth
  // (context.js: az 0.582 around the target). Slots fill in weight order, so
  // the first entries get the biggest plants.
  const AZ = 0.582, TX = 2.921, TZ = -2.734;
  const place = (s, d, rot = 0, extra = {}) => ({
    x: TX + s * Math.cos(AZ) + d * Math.sin(AZ),
    z: TZ - s * Math.sin(AZ) + d * Math.cos(AZ),
    rot,
    ...extra, // y → raise or sink relative to the (absent) ground
  });
  // Desktop: a loose ring around the card. Perspective pulls far plants toward
  // centre, so the pairs are staggered — front low and inner, mid wide, back
  // high and inner again — rather than stacked at one |s| per side.
  const DESKTOP_SLOTS = [
    place(-5.5, 6, 0.3), place(6, 5.5, -0.4),
    place(-14, -1, -0.1), place(14, -2, 0.2),
    place(-11.5, -13, 0.5), place(12, -13, -0.3),
  ];
  // Phone: just three plants along the bottom, under the centred card. Sunk a
  // little (y) so their tops clear the card, which spans nearly the full width.
  // Fewer plants, not just fewer slots — six plants on three slots would wrap
  // and stack. Same three as the desktop bottom row, so the scale ratio holds.
  const MOBILE_DECOR = [DECOR[0], DECOR[1], DECOR[5]];
  const MOBILE_SLOTS = [
    place(-2.6, 6, 0.3, { y: -2.5 }), place(2.8, 5.5, -0.4, { y: -2.5 }),
    place(0.1, 8, 0.5, { y: -2.5 }),
  ];
  // Same breakpoint as the CSS below, and LIVE — a one-shot innerWidth check
  // at mount fell out of sync with the media query whenever the viewport
  // changed after load (devtools device toggle, window resize), leaving desktop
  // plants pushed off the edges under a mobile layout.
  const NARROW = '(max-width: 640px)';
  let narrow = $state(typeof window !== 'undefined' && window.matchMedia(NARROW).matches);
  $effect(() => {
    const mq = window.matchMedia(NARROW);
    const apply = () => (narrow = mq.matches);
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  });
  const slots = $derived(narrow ? MOBILE_SLOTS : DESKTOP_SLOTS);
  const plants = $derived(narrow ? MOBILE_DECOR : DECOR);

  // Mirrors api/greeting.py time_of_day() — the API is locked, so derive it here.
  function periodNow() {
    const h = new Date().getHours();
    if (h >= 5 && h < 12) return 'morning';
    if (h >= 12 && h < 17) return 'afternoon';
    if (h >= 17 && h < 21) return 'evening';
    return 'night';
  }
  const period = periodNow();

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
  <div class="gate-garden" aria-hidden="true">
    <GardenView positions={plants} {period} {slots} interactive={false} fill bare />
  </div>

  <div class="gate-card" class:bad={err}>
    <div class="gate-brand">sprout</div>

    {#if authError}
      <div class="gate-err" role="alert">{authError}</div>
    {/if}

    {#if oauth}
      <a class="btn btn-line gate-google" href="/api/auth/google/login">Continue with Google</a>
    {/if}

    {#if showPw || !oauth}
      <div class="gate-pw">
        <input class="gate-in" type="password" placeholder="Password" bind:value={pw} bind:this={inEl}
          autocomplete="current-password" aria-label="Owner password"
          oninput={() => (err = false)}
          onkeydown={(e) => { if (e.key === 'Enter') unlock(); }} />
        <button class="btn btn-line gate-btn" onclick={unlock} disabled={busy || !pw}>Unlock</button>
        {#if err}<div class="gate-err" role="alert">Wrong password</div>{/if}
      </div>
    {/if}
  </div>

  {#if oauth && !showPw}
    <button class="gate-secret" type="button" onclick={() => (showPw = true)}>secret</button>
  {/if}
</div>

<style>
  /* Opaque on purpose — nothing underneath should be readable while locked.
     The garden renders bare (plants only, transparent canvas), so this paper
     IS the scene background and everything follows the theme normally. */
  .gate { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
    padding: 24px; background: var(--paper); overflow: hidden; }
  .gate-garden { position: absolute; inset: 0; }
  /* GardenView's root is a global class; make it fill this host. */
  .gate-garden :global(.garden-canvas-root) { height: 100%; }

  /* surface == paper here, so the 1px ink border is the only edge — as everywhere */
  .gate-card { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 10px;
    width: min(320px, 100%); padding: 28px 24px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); }
  .gate-card.bad { border-color: var(--loss); }
  .gate-brand { font-family: var(--sans); font-size: 22px; font-weight: 800; color: var(--ink); margin-bottom: 6px; }
  .gate-google { height: 36px; display: grid; place-items: center; text-decoration: none; }
  .gate-pw { display: flex; flex-direction: column; gap: 10px; }
  .gate-in { box-sizing: border-box; width: 100%; height: 38px; padding: 0 12px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); background: transparent;
    outline: none; font-family: var(--sans); font-size: 16px; font-weight: 500; color: var(--text); }
  .gate-in::placeholder { color: var(--muted); opacity: .6; }
  .gate-btn { height: 34px; }
  .gate-btn:disabled { opacity: .4; cursor: default; }
  .gate-err { font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--loss); }

  /* the owner fallback: a quiet word at the foot, above the phone's home bar */
  .gate-secret { position: absolute; z-index: 1; left: 50%; transform: translateX(-50%);
    bottom: calc(20px + env(safe-area-inset-bottom, 0px));
    padding: 6px 12px; border: 0; background: transparent; cursor: pointer;
    font-family: var(--sans); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .gate-secret:hover { color: var(--ink); }

  /* Phone: card stays centred, and loses its outline — with surface == paper
     that leaves just the wordmark and button floating among the plants. */
  @media (max-width: 640px) {
    .gate-card { border-color: transparent; }
    .gate-card.bad { border-color: var(--loss); }
  }
</style>

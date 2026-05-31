<script>
  // Self-reporting brutalist submit button — the button IS the notification.
  //   idle → (click) → working (label morphs to cycling dots) → runs `action()` →
  //   success (green cards fan out, ✓) | error (shake + red fan, ✕) → resets to idle.
  // `action` is an async fn returning a result; success = a truthy `.ok`.
  import { onDestroy } from 'svelte';

  let {
    label = 'Save',
    action,                  // async () => ({ ok: boolean, ... })  (may throw)
    onresult = () => {},     // called with the result on success
    resetMs = 840,
    variant = 'stack'
  } = $props();

  let phase = $state('idle'); // 'idle' | 'working' | 'success' | 'error'
  let dots = $state(1);
  let iv, t2, mounted = true;

  function stop() { clearInterval(iv); clearTimeout(t2); }

  async function run() {
    if (phase !== 'idle') return;
    phase = 'working';
    dots = 1;
    iv = setInterval(() => { dots = (dots % 3) + 1; }, 224);
    let res;
    try { res = await action?.(); } catch { res = null; }
    clearInterval(iv);
    if (!mounted) return;
    const ok = !!(res && res.ok);
    phase = ok ? 'success' : 'error';
    if (ok) onresult(res);
    t2 = setTimeout(() => { if (mounted) phase = 'idle'; }, resetMs);
  }

  onDestroy(() => { mounted = false; stop(); });
</script>

<button
  class="fb fb-{variant}"
  class:working={phase === 'working'}
  class:success={phase === 'success'}
  class:error={phase === 'error'}
  onclick={run}
  disabled={phase !== 'idle'}
  aria-live="polite"
>
  {#if phase === 'idle'}{label}
  {:else if phase === 'working'}<span class="fb-dots">{'.'.repeat(dots)}</span>
  {:else if phase === 'success'}<span class="fb-glyph">✓</span>
  {:else}<span class="fb-glyph">✕</span>{/if}
</button>

<style>
  .fb {
    font-family: var(--sans, 'Space Grotesk', sans-serif);
    font-size: 14px; font-weight: 700; line-height: 1;
    /* fixed width AND height so neither dots nor glyphs ever resize the button */
    width: 156px; height: 46px; padding: 0 20px;
    display: inline-flex; align-items: center; justify-content: center;
    cursor: pointer; color: var(--ink); background: var(--brand);
    border: 2.5px solid var(--ink); border-radius: 6px;
    box-shadow: 4px 4px 0 var(--ink);
    transition: transform .1s ease, box-shadow .1s ease;
  }
  .fb:hover:not(:disabled) { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 var(--ink); }
  .fb:active:not(:disabled) { transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--ink); }
  .fb:disabled { opacity: 1; cursor: default; }

  /* working: button settles in, dots cycle (driven from JS) */
  .fb.working { transform: translate(1px, 1px); box-shadow: 3px 3px 0 var(--ink); background: var(--brand); }
  .fb-dots { display: inline-block; width: 22px; text-align: center; font-family: var(--mono, monospace); font-size: 18px; }
  /* confirmation glyph (✓ on success, ✕ on error), for a beat */
  .fb-glyph { display: inline-block; font-size: 19px; font-weight: 700; line-height: 1; }

  /* success: green cards fan out (0.8s), ending back on the idle ink shadow */
  .fb.success { animation: fb-stack .8s ease both; }

  /* error: horizontal shake + red fan-out (red sibling of the success fan) */
  .fb.error { animation: fb-error .8s ease both; }

  /* deal a hand: three green cards (each with a 1px ink edge) fan out from under
     the base shadow while the button lifts, hold, then collapse back. 7 shadow
     layers in every frame so the fan slides smoothly instead of popping. */
  @keyframes fb-stack {
    0% {
      transform: translate(0, 0);
      box-shadow:
        4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink);
    }
    52% {
      transform: translate(-2px, -2px);
      box-shadow:
        4px 4px 0 var(--ink),
        9px 9px 0 var(--gain), 10px 10px 0 var(--ink),
        15px 15px 0 var(--gain), 16px 16px 0 var(--ink),
        21px 21px 0 var(--gain), 22px 22px 0 var(--ink);
    }
    74% {
      transform: translate(-2px, -2px);
      box-shadow:
        4px 4px 0 var(--ink),
        9px 9px 0 var(--gain), 10px 10px 0 var(--ink),
        15px 15px 0 var(--gain), 16px 16px 0 var(--ink),
        21px 21px 0 var(--gain), 22px 22px 0 var(--ink);
    }
    100% {
      transform: translate(0, 0);
      box-shadow:
        4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink),
        4px 4px 0 var(--gain), 4px 4px 0 var(--ink);
    }
  }

  /* error: a red fan snaps out and the button shakes side to side, then collapses. */
  @keyframes fb-error {
    0% {
      transform: translateX(0);
      box-shadow:
        4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink);
    }
    18% {
      transform: translateX(-5px);
      box-shadow:
        4px 4px 0 var(--ink),
        9px 9px 0 var(--loss), 10px 10px 0 var(--ink),
        15px 15px 0 var(--loss), 16px 16px 0 var(--ink),
        21px 21px 0 var(--loss), 22px 22px 0 var(--ink);
    }
    34% { transform: translateX(5px); }
    50% { transform: translateX(-4px); }
    66% { transform: translateX(4px); }
    82% {
      transform: translateX(-2px);
      box-shadow:
        4px 4px 0 var(--ink),
        9px 9px 0 var(--loss), 10px 10px 0 var(--ink),
        15px 15px 0 var(--loss), 16px 16px 0 var(--ink),
        21px 21px 0 var(--loss), 22px 22px 0 var(--ink);
    }
    100% {
      transform: translateX(0);
      box-shadow:
        4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink),
        4px 4px 0 var(--loss), 4px 4px 0 var(--ink);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .fb.success, .fb.error { animation: none; }
    .fb.success { box-shadow: 4px 4px 0 var(--gain); }
    .fb.error { box-shadow: 4px 4px 0 var(--loss); }
  }
</style>

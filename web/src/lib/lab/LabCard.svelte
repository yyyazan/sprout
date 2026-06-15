<script>
  // Shared module shell for the Lab grid: title row + live/soon status chip,
  // a one-line blurb, then whatever the module renders. Border-only chrome
  // per the design system — status is the only inversion.
  let { title, status = 'soon', blurb = '', wide = false, children } = $props();
</script>

<section class="lab-card" class:wide>
  <div class="lc-head">
    <span class="lc-title">{title}</span>
    <span class="lc-chip" class:on={status === 'live'}>{status}</span>
  </div>
  {#if blurb}<p class="lc-blurb">{blurb}</p>{/if}
  {@render children?.()}
</section>

<style>
  .lab-card { min-width: 0; padding: 16px 18px 18px; border: var(--bw) solid var(--ink);
    border-radius: var(--r); display: flex; flex-direction: column; gap: 10px; }
  .lab-card.wide { grid-column: 1 / -1; }

  .lc-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
  .lc-title { font-family: var(--sans); font-size: 13px; font-weight: 800; color: var(--ink);
    text-transform: uppercase; letter-spacing: .08em; }
  .lc-chip { font-family: var(--mono); font-size: 9.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: var(--muted); padding: 2px 8px; border: var(--bw) solid var(--hairline);
    border-radius: 999px; }
  .lc-chip.on { color: var(--paper); background: var(--ink); border-color: var(--ink); }

  .lc-blurb { margin: 0; font-family: var(--sans); font-size: 12px; line-height: 1.5;
    color: var(--muted); }
</style>

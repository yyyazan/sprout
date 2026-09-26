<script>
  // Crosshair tooltip for both charts. Ink chip above the cursor (below it near
  // the top edge). A measure turns it gain/loss with the span's change.
  //   point:   value · date · fills on that bar
  //   measure: change $ and % · from → to, oldest first
  let { x, y, tone = null, value, aside = null, sub = null, lines = [] } = $props();
</script>

<div class="ct {tone ?? ''}" class:below={y < 48} style="left:{x}px; top:{y}px">
  <span class="ct-v">{value}{#if aside}<span class="ct-a">{aside}</span>{/if}</span>
  {#if sub}<span class="ct-d">{sub}</span>{/if}
  {#each lines.slice(0, 4) as l}
    <span class="ct-trade {l.up ? 'up' : 'down'}">{l.text}</span>
  {/each}
  {#if lines.length > 4}<span class="ct-d">{lines.length - 4} more</span>{/if}
</div>

<style>
  .ct { position: absolute; z-index: 5; pointer-events: none; white-space: nowrap;
    transform: translate(-50%, calc(-100% - 12px));
    display: flex; flex-direction: column; align-items: center; line-height: 1.2;
    font-family: var(--num); font-variant-numeric: tabular-nums;
    padding: 4px 8px; background: var(--ink); color: var(--paper); border-radius: 4px; }
  .ct.below { transform: translate(-50%, 12px); }
  .ct.pos { background: var(--gain); color: #fff; }
  .ct.neg { background: var(--loss); color: #fff; }
  .ct-v { font-size: var(--fs-body); font-weight: 600; }
  .ct-a { margin-left: 5px; opacity: .8; font-weight: 500; }
  .ct-d { font-size: var(--fs-meta); font-weight: 500; opacity: .8; }
  .ct-trade { margin-top: 3px; font-size: var(--fs-meta); font-weight: 600; }
  .ct-trade.up { color: var(--gain); }
  .ct-trade.down { color: var(--loss); }
</style>

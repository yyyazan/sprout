<script>
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, LineSeries, BaselineSeries, LineStyle, ColorType, CrosshairMode } from 'lightweight-charts';
  import { MUTED, GRID } from '$lib/charts.js';
  import { formatValue } from '$lib/format.js';

  // `spec` is a {kind:'timeseries', fmt, baseline?, series:[...]} from charts.js.
  let { spec } = $props();

  let host = $state();
  let tooltip = $state();
  let tip = $state(null); // { x, y, date, rows:[{name,color,text}] }

  function hexToRgba(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  function fmtValue(v) {
    if (v === null || v === undefined) return '—';
    if (spec.fmt === 'percent') return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
    return formatValue(v, 'money');
  }

  function priceFormatter(v) {
    if (spec.fmt === 'percent') return v.toFixed(1) + '%';
    return '$' + v.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }

  function addSeries(chart, s) {
    if (s.type === 'area') {
      return chart.addSeries(AreaSeries, {
        lineColor: s.color, lineWidth: 2,
        topColor: hexToRgba(s.color, 0.28), bottomColor: hexToRgba(s.color, 0),
        priceLineVisible: false, lastValueVisible: false
      });
    }
    if (s.type === 'baseline') {
      return chart.addSeries(BaselineSeries, {
        baseValue: { type: 'price', price: 0 },
        topLineColor: 'rgba(0,0,0,0)', topFillColor1: 'rgba(0,0,0,0)', topFillColor2: 'rgba(0,0,0,0)',
        bottomLineColor: s.color, bottomFillColor1: hexToRgba(s.color, 0.04), bottomFillColor2: hexToRgba(s.color, 0.28),
        lineWidth: 1.6, priceLineVisible: false, lastValueVisible: false
      });
    }
    return chart.addSeries(LineSeries, {
      color: s.color, lineWidth: s.width ?? 2,
      lineStyle: s.dashed ? LineStyle.Dotted : LineStyle.Solid,
      priceLineVisible: false, lastValueVisible: false
    });
  }

  onMount(() => {
    const chart = createChart(host, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'rgba(0,0,0,0)' },
        textColor: MUTED,
        fontFamily: '-apple-system, system-ui, sans-serif',
        fontSize: 11,
        attributionLogo: false
      },
      grid: { vertLines: { visible: false }, horzLines: { color: GRID } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: GRID, width: 1, style: LineStyle.Solid, labelVisible: false },
        horzLine: { color: GRID, width: 1, style: LineStyle.Dotted, labelVisible: false }
      },
      localization: { priceFormatter },
      handleScroll: false,
      handleScale: false
    });

    const handles = spec.series.map((s) => {
      const series = addSeries(chart, s);
      series.setData(s.data);
      return { s, series };
    });

    if (spec.baseline !== undefined && handles.length) {
      handles[0].series.createPriceLine({
        price: spec.baseline, color: GRID, lineWidth: 1,
        lineStyle: LineStyle.Dashed, axisLabelVisible: false
      });
    }

    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {
        tip = null;
        return;
      }
      const rows = [];
      for (const { s, series } of handles) {
        const d = param.seriesData.get(series);
        if (!d) continue;
        const v = d.value ?? d.close;
        rows.push({ name: s.name, color: s.color, text: fmtValue(v) });
      }
      if (!rows.length) { tip = null; return; }
      const date = typeof param.time === 'string'
        ? new Date(param.time + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        : param.time;
      tip = { x: param.point.x, y: param.point.y, date, rows };
    });

    return () => chart.remove();
  });

  // Position the tooltip near the crosshair, clamped inside the host.
  let tipStyle = $derived.by(() => {
    if (!tip || !host) return 'display:none';
    const w = host.clientWidth, pad = 12, tw = 150;
    const left = Math.min(Math.max(tip.x + pad, pad), w - tw - pad);
    return `left:${left}px; top:${Math.max(tip.y - 8, 4)}px`;
  });
</script>

<div class="ts-chart" bind:this={host}>
  <div class="ts-tooltip" class:visible={!!tip} bind:this={tooltip} style={tipStyle}>
    {#if tip}
      <div class="ts-tip-date">{tip.date}</div>
      {#each tip.rows as r}
        <div class="ts-tip-row">
          <span class="ts-tip-dot" style="background:{r.color}"></span>
          {#if r.name}<span class="ts-tip-name">{r.name}</span>{/if}
          <span class="ts-tip-val">{r.text}</span>
        </div>
      {/each}
    {/if}
  </div>
</div>

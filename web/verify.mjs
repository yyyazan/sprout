import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

const ROUTES = [
  ['/', 'dashboard'],
  ['/investments', 'investments'],
  ['/trades', 'trades']
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });

const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
page.on('requestfailed', (r) => {
  const u = r.url();
  // ignore third-party logo/icon 404s (duckduckgo) — cosmetic only
  if (!u.includes('duckduckgo') && !u.includes('clearbit')) {
    errors.push('REQFAIL: ' + u + ' ' + (r.failure()?.errorText || ''));
  }
});

for (const [path, name] of ROUTES) {
  errors.length = 0;
  await page.goto(BASE + path, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(5000); // let THREE garden + charts paint
  await page.screenshot({ path: `/tmp/shot-${name}.png`, fullPage: true });
  // quick DOM probes
  const probe = await page.evaluate(() => ({
    canvas: !!document.querySelector('#garden-root canvas'),
    cards: document.querySelectorAll('.portfolio-card').length,
    tsCharts: document.querySelectorAll('.ts-chart').length,
    svgCharts: document.querySelectorAll('.donut, .pnl-bars').length,
    rows: document.querySelectorAll('table.data-table tbody tr').length,
    kpis: document.querySelectorAll('.kpi-card').length
  }));
  console.log(`[${name}] errors=${errors.length ? JSON.stringify(errors.slice(0, 6)) : 'none'} | probe=${JSON.stringify(probe)}`);
}

await browser.close();

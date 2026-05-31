<script>
  import { page } from '$app/stores';
  const NAV = [
    { label: 'Dashboard', path: '/', glyph: '◇' },
    { label: 'Investments', path: '/investments', glyph: '↗' },
    { label: 'Log', path: '/trades', glyph: '↓' }
  ];
  function isActive(pathname, path) {
    return path === '/' ? pathname === '/' : pathname.startsWith(path);
  }
  // Each hover paints the nav link's hard shadow a fresh random accent.
  const ACCENTS = ['#ff90e8', '#ffc900', '#23a094', '#5b8def', '#c994e8', '#ff6e5e'];
  function randAccent(e) {
    e.currentTarget.style.setProperty('--hovsh', ACCENTS[Math.floor(Math.random() * ACCENTS.length)]);
  }
</script>

<aside class="sidebar">
  <div class="brand"><span class="brand-title">sprout</span></div>
  <nav class="nav">
    {#each NAV as item}
      <a href={item.path} class="nav-link" class:active={isActive($page.url.pathname, item.path)} onmouseenter={randAccent}>
        <div class="nav-item">
          <span class="nav-icon">{item.glyph}</span>
          <span class="nav-label">{item.label}</span>
        </div>
      </a>
    {/each}
  </nav>
</aside>

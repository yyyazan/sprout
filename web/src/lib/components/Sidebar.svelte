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
</script>

<aside class="sidebar">
  <div class="brand"><span class="brand-title">sprout</span></div>
  <nav class="nav">
    {#each NAV as item}
      <a href={item.path} class="nav-link" class:active={isActive($page.url.pathname, item.path)}>
        <div class="nav-item">
          <span class="nav-icon">{item.glyph}</span>
          <span class="nav-label">{item.label}</span>
        </div>
      </a>
    {/each}
  </nav>
</aside>

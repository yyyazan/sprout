<script>
  import '../app.css';
  // Sidebar hidden for now — re-enable by uncommenting both lines below
  // and removing the `app-root--nosidebar` modifier.
  // import Sidebar from '$lib/components/Sidebar.svelte';
  let { children } = $props();
</script>

<div class="app-root app-root--nosidebar">
  <!-- <Sidebar /> -->
  {@render children()}
</div>

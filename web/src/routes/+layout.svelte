<script>
  import '../app.css';
  import Sidebar from '$lib/components/Sidebar.svelte';
  let { children } = $props();
</script>

<div class="app-root">
  <Sidebar />
  {@render children()}
</div>

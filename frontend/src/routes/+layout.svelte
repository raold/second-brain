<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import { onMount, onDestroy } from 'svelte';
  import { wsClient } from '$lib/api/websocket';
  
  onMount(() => {
    // Connect to WebSocket for real-time updates
    wsClient.connect();
  });
  
  onDestroy(() => {
    // Clean up WebSocket connection
    wsClient.disconnect();
  });
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
  <!-- Navigation -->
  <nav class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex">
          <div class="flex-shrink-0 flex items-center">
            <a href="/" class="text-xl font-bold text-gray-900 dark:text-white">
              🧠 Second Brain
            </a>
          </div>
          <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
            <a
              href="/"
              class="border-b-2 px-1 pt-1 text-sm font-medium {$page.url.pathname === '/' ? 'border-primary-500 text-gray-900 dark:text-white' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-white'} inline-flex items-center"
            >
              Search
            </a>
            <a
              href="/memories"
              class="border-b-2 px-1 pt-1 text-sm font-medium {$page.url.pathname.startsWith('/memories') ? 'border-primary-500 text-gray-900 dark:text-white' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-white'} inline-flex items-center"
            >
              Memories
            </a>
            <a
              href="/visualize"
              class="border-b-2 px-1 pt-1 text-sm font-medium {$page.url.pathname === '/visualize' ? 'border-primary-500 text-gray-900 dark:text-white' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-white'} inline-flex items-center"
            >
              Visualize
            </a>
          </div>
        </div>
        <div class="flex items-center">
          <a
            href="/memories/new"
            class="ml-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            New Memory
          </a>
        </div>
      </div>
    </div>
  </nav>

  <!-- Main content -->
  <main class="flex-1">
    <slot />
  </main>
</div>
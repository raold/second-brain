<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';
  import { searchQuery, searchResults, isLoading, error } from '$lib/stores/memories';
  import SearchBar from '$lib/components/SearchBar.svelte';
  import MemoryCard from '$lib/components/MemoryCard.svelte';
  
  let searchMode: 'vector' | 'hybrid' = 'hybrid';
  let vectorWeight = 0.6;
  
  async function performSearch() {
    if (!$searchQuery.trim()) {
      searchResults.set([]);
      return;
    }
    
    isLoading.set(true);
    error.set(null);
    
    try {
      const response = searchMode === 'vector'
        ? await api.searchVector({ query: $searchQuery, limit: 20 })
        : await api.searchHybrid({ 
            query: $searchQuery, 
            limit: 20, 
            vector_weight: vectorWeight 
          });
      
      searchResults.set(response.results);
    } catch (e) {
      error.set(e instanceof Error ? e.message : 'Search failed');
      searchResults.set([]);
    } finally {
      isLoading.set(false);
    }
  }
  
  // Debounced search
  let searchTimeout: NodeJS.Timeout;
  $: {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(performSearch, 300);
  }
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <!-- Hero Section -->
  <div class="text-center mb-12">
    <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">
      Search Your Second Brain
    </h1>
    <p class="text-lg text-gray-600 dark:text-gray-300">
      Find memories using semantic search powered by AI
    </p>
  </div>

  <!-- Search Controls -->
  <div class="max-w-4xl mx-auto mb-8">
    <SearchBar bind:value={$searchQuery} />
    
    <!-- Search Options -->
    <div class="mt-4 flex items-center justify-center space-x-4">
      <div class="flex items-center space-x-2">
        <input
          type="radio"
          id="vector"
          value="vector"
          bind:group={searchMode}
          class="text-primary-600 focus:ring-primary-500"
        />
        <label for="vector" class="text-sm text-gray-700 dark:text-gray-300">
          Vector Search
        </label>
      </div>
      
      <div class="flex items-center space-x-2">
        <input
          type="radio"
          id="hybrid"
          value="hybrid"
          bind:group={searchMode}
          class="text-primary-600 focus:ring-primary-500"
        />
        <label for="hybrid" class="text-sm text-gray-700 dark:text-gray-300">
          Hybrid Search
        </label>
      </div>
      
      {#if searchMode === 'hybrid'}
        <div class="flex items-center space-x-2">
          <label for="weight" class="text-sm text-gray-700 dark:text-gray-300">
            Vector Weight:
          </label>
          <input
            type="range"
            id="weight"
            min="0"
            max="1"
            step="0.1"
            bind:value={vectorWeight}
            class="w-32"
          />
          <span class="text-sm text-gray-700 dark:text-gray-300">
            {vectorWeight}
          </span>
        </div>
      {/if}
    </div>
  </div>

  <!-- Error Message -->
  {#if $error}
    <div class="max-w-4xl mx-auto mb-8">
      <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {$error}
      </div>
    </div>
  {/if}

  <!-- Search Results -->
  <div class="max-w-4xl mx-auto">
    {#if $isLoading}
      <div class="text-center py-12">
        <div class="inline-flex items-center">
          <svg class="animate-spin h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="ml-2 text-gray-600 dark:text-gray-300">Searching...</span>
        </div>
      </div>
    {:else if $searchResults.length > 0}
      <div class="space-y-4">
        <p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
          Found {$searchResults.length} results
        </p>
        {#each $searchResults as result}
          <MemoryCard memory={result} showScore={true} />
        {/each}
      </div>
    {:else if $searchQuery}
      <div class="text-center py-12 text-gray-500 dark:text-gray-400">
        No results found for "{$searchQuery}"
      </div>
    {:else}
      <div class="text-center py-12 text-gray-500 dark:text-gray-400">
        Start typing to search your memories
      </div>
    {/if}
  </div>
</div>
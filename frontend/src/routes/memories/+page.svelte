<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';
  import { memories, isLoading, error } from '$lib/stores/memories';
  import MemoryCard from '$lib/components/MemoryCard.svelte';
  import type { Memory } from '$lib/types/memory';
  
  let filterType = '';
  let filterTag = '';
  let sortBy: 'created' | 'accessed' | 'importance' = 'created';
  let sortOrder: 'asc' | 'desc' = 'desc';
  
  onMount(async () => {
    await loadMemories();
  });
  
  async function loadMemories() {
    isLoading.set(true);
    error.set(null);
    
    try {
      const response = await api.listMemories({ limit: 100 });
      memories.set(response.memories);
    } catch (e) {
      error.set(e instanceof Error ? e.message : 'Failed to load memories');
    } finally {
      isLoading.set(false);
    }
  }
  
  async function deleteMemory(id: string) {
    if (!confirm('Are you sure you want to delete this memory?')) return;
    
    try {
      await api.deleteMemory(id);
      memories.update(items => items.filter(m => m.id !== id));
    } catch (e) {
      error.set(e instanceof Error ? e.message : 'Failed to delete memory');
    }
  }
  
  // Filter and sort memories
  $: filteredMemories = $memories
    .filter(m => !filterType || m.memory_type === filterType)
    .filter(m => !filterTag || m.tags.includes(filterTag))
    .sort((a, b) => {
      let aVal: any, bVal: any;
      switch (sortBy) {
        case 'created':
          aVal = new Date(a.created_at);
          bVal = new Date(b.created_at);
          break;
        case 'accessed':
          aVal = a.access_count;
          bVal = b.access_count;
          break;
        case 'importance':
          aVal = a.importance_score;
          bVal = b.importance_score;
          break;
      }
      return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
    });
  
  // Get unique types and tags
  $: memoryTypes = [...new Set($memories.map(m => m.memory_type))];
  $: allTags = [...new Set($memories.flatMap(m => m.tags))];
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <!-- Header -->
  <div class="flex justify-between items-center mb-8">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
        Memory Bank
      </h1>
      <p class="mt-2 text-gray-600 dark:text-gray-300">
        {$memories.length} memories stored
      </p>
    </div>
    <a
      href="/memories/new"
      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
    >
      <svg class="-ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
      </svg>
      New Memory
    </a>
  </div>
  
  <!-- Filters and Sort -->
  <div class="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-6">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- Type Filter -->
      <div>
        <label for="type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Type
        </label>
        <select
          id="type"
          bind:value={filterType}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
        >
          <option value="">All Types</option>
          {#each memoryTypes as type}
            <option value={type}>{type}</option>
          {/each}
        </select>
      </div>
      
      <!-- Tag Filter -->
      <div>
        <label for="tag" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Tag
        </label>
        <select
          id="tag"
          bind:value={filterTag}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
        >
          <option value="">All Tags</option>
          {#each allTags as tag}
            <option value={tag}>{tag}</option>
          {/each}
        </select>
      </div>
      
      <!-- Sort By -->
      <div>
        <label for="sort" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Sort By
        </label>
        <select
          id="sort"
          bind:value={sortBy}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
        >
          <option value="created">Created Date</option>
          <option value="accessed">Access Count</option>
          <option value="importance">Importance</option>
        </select>
      </div>
      
      <!-- Sort Order -->
      <div>
        <label for="order" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Order
        </label>
        <select
          id="order"
          bind:value={sortOrder}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>
    </div>
  </div>
  
  <!-- Error Message -->
  {#if $error}
    <div class="mb-8">
      <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {$error}
      </div>
    </div>
  {/if}
  
  <!-- Memory List -->
  {#if $isLoading}
    <div class="text-center py-12">
      <div class="inline-flex items-center">
        <svg class="animate-spin h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="ml-2 text-gray-600 dark:text-gray-300">Loading memories...</span>
      </div>
    </div>
  {:else if filteredMemories.length > 0}
    <div class="grid gap-4">
      {#each filteredMemories as memory}
        <div class="relative">
          <MemoryCard {memory} />
          <button
            on:click={() => deleteMemory(memory.id)}
            class="absolute top-4 right-4 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            title="Delete memory"
          >
            <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm4 0a1 1 0 012 0v6a1 1 0 11-2 0V8z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-center py-12 text-gray-500 dark:text-gray-400">
      {#if $memories.length === 0}
        <p>No memories yet. Create your first memory!</p>
      {:else}
        <p>No memories match your filters.</p>
      {/if}
    </div>
  {/if}
</div>
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api/client';
  import { currentMemory, removeMemory } from '$lib/stores/memories';
  import type { Memory } from '$lib/types/memory';
  
  let isLoading = true;
  let error = '';
  let relatedMemories: Memory[] = [];
  
  $: memoryId = $page.params.id;
  
  onMount(async () => {
    await loadMemory();
  });
  
  async function loadMemory() {
    isLoading = true;
    error = '';
    
    try {
      const memory = await api.getMemory(memoryId);
      currentMemory.set(memory);
      
      // Load related memories
      if (memory.embedding) {
        try {
          const related = await api.searchVector({ 
            query: memory.content.slice(0, 100), 
            limit: 5 
          });
          relatedMemories = related.results.filter(m => m.id !== memory.id).slice(0, 4);
        } catch (e) {
          // Ignore related memories errors
        }
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load memory';
    } finally {
      isLoading = false;
    }
  }
  
  async function handleDelete() {
    if (!$currentMemory || !confirm('Are you sure you want to delete this memory?')) return;
    
    try {
      await api.deleteMemory($currentMemory.id);
      removeMemory($currentMemory.id);
      await goto('/memories');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete memory';
    }
  }
  
  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  function getImportanceLabel(score: number) {
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
  }
</script>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  {#if isLoading}
    <div class="text-center py-12">
      <div class="inline-flex items-center">
        <svg class="animate-spin h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="ml-2 text-gray-600 dark:text-gray-300">Loading memory...</span>
      </div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-8">
      {error}
    </div>
    <a href="/memories" class="text-primary-600 hover:text-primary-500">
      ← Back to memories
    </a>
  {:else if $currentMemory}
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex justify-between items-start">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {$currentMemory.memory_type}
            </h1>
            <div class="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
              <span>Created {formatDate($currentMemory.created_at)}</span>
              {#if $currentMemory.updated_at !== $currentMemory.created_at}
                <span>•</span>
                <span>Updated {formatDate($currentMemory.updated_at)}</span>
              {/if}
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <a
              href="/memories/{$currentMemory.id}/edit"
              class="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
            >
              Edit
            </a>
            <button
              on:click={handleDelete}
              class="px-3 py-1 text-sm font-medium text-red-700 bg-red-50 border border-red-300 rounded-md hover:bg-red-100 dark:bg-red-900 dark:text-red-300 dark:border-red-700 dark:hover:bg-red-800"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
      
      <!-- Content -->
      <div class="px-6 py-4">
        <p class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
          {$currentMemory.content}
        </p>
      </div>
      
      <!-- Metadata -->
      <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Importance -->
          <div>
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Importance
            </h3>
            <div class="flex items-center">
              <div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 mr-2">
                <div
                  class="h-2 rounded-full {$currentMemory.importance_score >= 0.8 ? 'bg-red-500' : $currentMemory.importance_score >= 0.5 ? 'bg-yellow-500' : 'bg-gray-400'}"
                  style="width: {$currentMemory.importance_score * 100}%"
                />
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {getImportanceLabel($currentMemory.importance_score)} ({($currentMemory.importance_score * 100).toFixed(0)}%)
              </span>
            </div>
          </div>
          
          <!-- Access Count -->
          <div>
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Access Count
            </h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {$currentMemory.access_count} times
            </p>
          </div>
          
          <!-- Tags -->
          {#if $currentMemory.tags.length > 0}
            <div class="md:col-span-2">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tags
              </h3>
              <div class="flex flex-wrap gap-2">
                {#each $currentMemory.tags as tag}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {tag}
                  </span>
                {/each}
              </div>
            </div>
          {/if}
          
          <!-- Vector Status -->
          {#if $currentMemory.embedding}
            <div class="md:col-span-2">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Vector Embedding
              </h3>
              <p class="text-sm text-green-600 dark:text-green-400">
                ✓ Generated (1536 dimensions)
              </p>
            </div>
          {/if}
        </div>
      </div>
      
      <!-- Related Memories -->
      {#if relatedMemories.length > 0}
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Related Memories
          </h3>
          <div class="space-y-3">
            {#each relatedMemories as related}
              <a
                href="/memories/{related.id}"
                class="block p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900 dark:text-white">
                      {related.memory_type}
                    </p>
                    <p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                      {related.content}
                    </p>
                  </div>
                  {#if related.similarity}
                    <span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {(related.similarity * 100).toFixed(0)}% match
                    </span>
                  {/if}
                </div>
              </a>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
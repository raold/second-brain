<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api/client';
  import { addMemory } from '$lib/stores/memories';
  import type { Memory } from '$lib/types/memory';
  
  let content = '';
  let memoryType = 'thought';
  let tags = '';
  let importanceScore = 0.5;
  let isSubmitting = false;
  let error = '';
  
  const memoryTypes = [
    'thought', 'note', 'idea', 'todo', 'reference',
    'conversation', 'decision', 'learning', 'insight'
  ];
  
  async function handleSubmit() {
    if (!content.trim()) {
      error = 'Content is required';
      return;
    }
    
    isSubmitting = true;
    error = '';
    
    try {
      const memory = await api.createMemory({
        content: content.trim(),
        memory_type: memoryType,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        importance_score: importanceScore,
        metadata: {}
      });
      
      addMemory(memory);
      await goto(`/memories/${memory.id}`);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create memory';
      isSubmitting = false;
    }
  }
  
  function handleCancel() {
    goto('/memories');
  }
</script>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <div class="bg-white dark:bg-gray-800 shadow rounded-lg">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
        Create New Memory
      </h1>
    </div>
    
    <!-- Form -->
    <form on:submit|preventDefault={handleSubmit} class="px-6 py-4 space-y-6">
      <!-- Content -->
      <div>
        <label for="content" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Content <span class="text-red-500">*</span>
        </label>
        <textarea
          id="content"
          bind:value={content}
          rows="6"
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          placeholder="What's on your mind?"
          disabled={isSubmitting}
        />
      </div>
      
      <!-- Memory Type -->
      <div>
        <label for="type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Type
        </label>
        <select
          id="type"
          bind:value={memoryType}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
          disabled={isSubmitting}
        >
          {#each memoryTypes as type}
            <option value={type}>{type}</option>
          {/each}
        </select>
      </div>
      
      <!-- Tags -->
      <div>
        <label for="tags" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Tags
        </label>
        <input
          id="tags"
          type="text"
          bind:value={tags}
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600"
          placeholder="tag1, tag2, tag3"
          disabled={isSubmitting}
        />
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Separate tags with commas
        </p>
      </div>
      
      <!-- Importance Score -->
      <div>
        <label for="importance" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Importance: {(importanceScore * 100).toFixed(0)}%
        </label>
        <input
          id="importance"
          type="range"
          min="0"
          max="1"
          step="0.1"
          bind:value={importanceScore}
          class="block w-full"
          disabled={isSubmitting}
        />
        <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>Low</span>
          <span>Medium</span>
          <span>High</span>
        </div>
      </div>
      
      <!-- Error Message -->
      {#if error}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      {/if}
      
      <!-- Actions -->
      <div class="flex justify-end space-x-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          on:click={handleCancel}
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          type="submit"
          class="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={isSubmitting}
        >
          {#if isSubmitting}
            <span class="inline-flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating...
            </span>
          {:else}
            Create Memory
          {/if}
        </button>
      </div>
    </form>
  </div>
</div>
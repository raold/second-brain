<script lang="ts">
  import type { Memory, SearchResult } from '$lib/types/memory';
  
  export let memory: Memory | SearchResult;
  export let showScore = false;
  
  function isSearchResult(m: Memory | SearchResult): m is SearchResult {
    return 'similarity' in m || 'text_rank' in m || 'combined_score' in m;
  }
  
  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
  
  function getImportanceColor(score: number) {
    if (score >= 0.8) return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    if (score >= 0.5) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  }
</script>

<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
  <div class="flex items-start justify-between">
    <div class="flex-1">
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
        {memory.memory_type}
      </h3>
      <p class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
        {memory.content}
      </p>
    </div>
    <div class="ml-4 flex-shrink-0">
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getImportanceColor(memory.importance_score)}">
        {(memory.importance_score * 100).toFixed(0)}%
      </span>
    </div>
  </div>
  
  <!-- Tags -->
  {#if memory.tags.length > 0}
    <div class="mt-4 flex flex-wrap gap-2">
      {#each memory.tags as tag}
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          {tag}
        </span>
      {/each}
    </div>
  {/if}
  
  <!-- Metadata -->
  <div class="mt-4 flex items-center text-sm text-gray-500 dark:text-gray-400">
    <span>{formatDate(memory.created_at)}</span>
    {#if memory.access_count > 0}
      <span class="mx-2">•</span>
      <span>Accessed {memory.access_count} times</span>
    {/if}
  </div>
  
  <!-- Search Scores -->
  {#if showScore && isSearchResult(memory)}
    <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
      <div class="flex items-center space-x-4 text-xs text-gray-600 dark:text-gray-400">
        {#if memory.similarity !== undefined}
          <span>Vector: {(memory.similarity * 100).toFixed(1)}%</span>
        {/if}
        {#if memory.text_rank !== undefined}
          <span>Text: {memory.text_rank.toFixed(3)}</span>
        {/if}
        {#if memory.combined_score !== undefined}
          <span class="font-medium">Combined: {(memory.combined_score * 100).toFixed(1)}%</span>
        {/if}
      </div>
    </div>
  {/if}
  
  <!-- Actions -->
  <div class="mt-4 flex items-center space-x-4">
    <a
      href="/memories/{memory.id}"
      class="text-sm text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
    >
      View Details
    </a>
    <a
      href="/memories/{memory.id}/edit"
      class="text-sm text-gray-600 hover:text-gray-500 dark:text-gray-400 dark:hover:text-gray-300"
    >
      Edit
    </a>
  </div>
</div>
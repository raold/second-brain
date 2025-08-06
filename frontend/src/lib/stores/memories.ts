import { writable, derived } from 'svelte/store';
import type { Memory, SearchResult } from '$lib/types/memory';

// Core stores
export const memories = writable<Memory[]>([]);
export const searchResults = writable<SearchResult[]>([]);
export const currentMemory = writable<Memory | null>(null);
export const searchQuery = writable<string>('');
export const isLoading = writable<boolean>(false);
export const error = writable<string | null>(null);

// Derived stores
export const totalMemories = derived(memories, $memories => $memories.length);

export const memoriesByType = derived(memories, $memories => {
  const grouped = new Map<string, Memory[]>();
  $memories.forEach(memory => {
    const type = memory.memory_type;
    if (!grouped.has(type)) {
      grouped.set(type, []);
    }
    grouped.get(type)!.push(memory);
  });
  return grouped;
});

export const allTags = derived(memories, $memories => {
  const tags = new Set<string>();
  $memories.forEach(memory => {
    memory.tags.forEach(tag => tags.add(tag));
  });
  return Array.from(tags).sort();
});

// Helper functions
export function addMemory(memory: Memory) {
  memories.update(items => [memory, ...items]);
}

export function updateMemory(id: string, updates: Partial<Memory>) {
  memories.update(items => 
    items.map(item => 
      item.id === id ? { ...item, ...updates } : item
    )
  );
}

export function removeMemory(id: string) {
  memories.update(items => items.filter(item => item.id !== id));
}
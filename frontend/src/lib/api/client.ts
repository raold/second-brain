import type { Memory, MemoryInput, SearchQuery, SearchResponse } from '$lib/types/memory';

export class SecondBrainAPI {
  private baseURL: string;

  constructor(baseURL: string = '') {
    this.baseURL = baseURL;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  // Memory CRUD operations
  async createMemory(memory: MemoryInput): Promise<{ memory: Memory }> {
    return this.request('/api/v2/memories/', {
      method: 'POST',
      body: JSON.stringify(memory),
    });
  }

  async getMemory(id: string): Promise<{ memory: Memory }> {
    return this.request(`/api/v2/memories/${id}`);
  }

  async listMemories(params?: {
    limit?: number;
    offset?: number;
    memory_type?: string;
    tags?: string[];
  }): Promise<{ memories: Memory[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }
    
    return this.request(`/api/v2/memories/?${searchParams}`);
  }

  async updateMemory(id: string, updates: Partial<MemoryInput>): Promise<{ memory: Memory }> {
    return this.request(`/api/v2/memories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async deleteMemory(id: string): Promise<{ success: boolean }> {
    return this.request(`/api/v2/memories/${id}`, {
      method: 'DELETE',
    });
  }

  // Search operations
  async searchVector(query: SearchQuery): Promise<SearchResponse> {
    return this.request('/api/v2/search/vector', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  }

  async searchHybrid(query: SearchQuery): Promise<SearchResponse> {
    return this.request('/api/v2/search/hybrid', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  }

  async searchSuggestions(prefix: string, limit: number = 5): Promise<{ suggestions: string[] }> {
    const params = new URLSearchParams({ prefix, limit: String(limit) });
    return this.request(`/api/v2/search/suggestions?${params}`);
  }

  // Health check
  async health(): Promise<{ status: string; ready: boolean }> {
    return this.request('/health');
  }
}

// Create singleton instance
export const api = new SecondBrainAPI();
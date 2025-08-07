export interface Memory {
  id: string;
  content: string;
  memory_type: string;
  importance_score: number;
  tags: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  access_count: number;
  last_accessed: string | null;
  has_embedding?: boolean;
  embedding_model?: string;
}

export interface MemoryInput {
  content: string;
  memory_type?: string;
  importance_score?: number;
  tags?: string[];
  metadata?: Record<string, any>;
  generate_embedding?: boolean;
}

export interface SearchResult {
  id: string;
  content: string;
  memory_type: string;
  importance_score: number;
  tags: string[];
  metadata: Record<string, any>;
  created_at: string;
  similarity?: number;
  text_rank?: number;
  combined_score?: number;
}

export interface SearchQuery {
  query: string;
  limit?: number;
  offset?: number;
  memory_type?: string;
  tags?: string[];
  min_similarity?: number;
  vector_weight?: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  search_type: 'vector' | 'text' | 'hybrid';
  processing_time_ms: number;
}
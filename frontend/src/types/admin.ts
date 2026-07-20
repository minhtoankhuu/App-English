export interface TeacherOut {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TeacherCreateRequest {
  email: string;
  full_name: string;
  password: string;
}

export interface TeacherUpdateRequest {
  full_name?: string;
  is_active?: boolean;
  password?: string;
}

export interface KnowledgeUnitRefOut {
  id: string;
  order_no: number;
  title: string;
  grade_number: number;
}

export interface KnowledgeGrammarPointRefOut {
  id: string;
  name: string;
  group_name: string;
  topic_name: string;
}

export interface KnowledgeDocumentOut {
  id: string;
  file_name: string;
  is_published: boolean;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  unit: KnowledgeUnitRefOut | null;
  grammar_point: KnowledgeGrammarPointRefOut | null;
}

export type KnowledgeChunkType = "vocabulary" | "word_form" | "phrase" | "grammar" | "other";

export interface KnowledgeChunkAdminOut {
  id: string;
  order_no: number;
  chunk_type: KnowledgeChunkType;
  section_title: string;
  raw_text: string;
  structured: Record<string, unknown> | null;
}

export interface AIProviderConfigOut {
  id: string;
  provider: string;
  model: string;
  embedding_model: string;
  temperature: number;
  duplicate_similarity_threshold: number;
  is_active: boolean;
  api_key_masked: string;
  updated_at: string;
}

export interface AIProviderConfigUpdateRequest {
  model: string;
  embedding_model: string;
  temperature: number;
  duplicate_similarity_threshold: number;
  api_key: string | null;
}

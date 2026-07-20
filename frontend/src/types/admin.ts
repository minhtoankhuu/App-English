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

export interface KnowledgeDocumentOut {
  id: string;
  file_name: string;
  is_published: boolean;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  unit: KnowledgeUnitRefOut;
}

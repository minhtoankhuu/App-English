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

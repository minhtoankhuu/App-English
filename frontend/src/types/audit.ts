export interface AuditLogOut {
  id: string;
  created_at: string;
  actor_user_id: string;
  actor_email: string;
  action: string;
  target_type: string;
  target_id: string;
  target_label: string;
  details: Record<string, unknown>;
}

export interface AuditLogPage {
  items: AuditLogOut[];
  total: number;
  limit: number;
  offset: number;
}

export const ACTION_LABELS: Record<string, string> = {
  "teacher.created": "Tạo giáo viên",
  "teacher.updated": "Cập nhật giáo viên",
  "teacher.activated": "Mở tài khoản",
  "teacher.deactivated": "Khóa tài khoản",
  "teacher.password_reset": "Đặt lại mật khẩu",
};

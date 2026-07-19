import { useEffect, useState } from "react";
import { createTeacher, deleteTeacher, listTeachers, updateTeacher } from "../api/admin";
import { ApiError } from "../api/client";
import { Modal } from "../components/Modal";
import type { TeacherOut } from "../types/admin";

export function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<TeacherOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");

  const [resettingId, setResettingId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  function reload() {
    listTeachers()
      .then(setTeachers)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được danh sách"));
  }

  useEffect(reload, []);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      await createTeacher({ email, full_name: fullName, password });
      setEmail("");
      setFullName("");
      setPassword("");
      setShowCreate(false);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không tạo được tài khoản");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleActive(teacher: TeacherOut) {
    setError(null);
    try {
      await updateTeacher(teacher.id, { is_active: !teacher.is_active });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không cập nhật được");
    }
  }

  async function handleResetPassword() {
    if (!resettingId) return;
    if (newPassword.length < 8) {
      setError("Mật khẩu mới phải từ 8 ký tự");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateTeacher(resettingId, { password: newPassword });
      setResettingId(null);
      setNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không đặt lại được mật khẩu");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(teacher: TeacherOut) {
    if (!window.confirm(`Xóa vĩnh viễn tài khoản "${teacher.full_name}"? Không thể hoàn tác.`)) return;
    setDeletingId(teacher.id);
    setError(null);
    try {
      await deleteTeacher(teacher.id);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không xóa được tài khoản");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Tài khoản giáo viên</h2>
        <button type="button" className="button primary" onClick={() => setShowCreate(true)}>
          + Thêm tài khoản
        </button>
      </div>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!teachers && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
      {teachers && teachers.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có giáo viên nào.</p>}

      {teachers && teachers.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Họ tên</th>
              <th>Email</th>
              <th>Trạng thái</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {teachers.map((teacher) => (
              <tr key={teacher.id}>
                <td>{teacher.full_name}</td>
                <td>{teacher.email}</td>
                <td>
                  <span className={`status-pill ${teacher.is_active ? "active" : "locked"}`}>
                    {teacher.is_active ? "Đang hoạt động" : "Đã khóa"}
                  </span>
                </td>
                <td className="actions">
                  <button type="button" className="button secondary compact" onClick={() => handleToggleActive(teacher)}>
                    {teacher.is_active ? "Khóa" : "Mở lại"}
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => {
                      setResettingId(teacher.id);
                      setNewPassword("");
                    }}
                  >
                    Đặt lại mật khẩu
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => handleDelete(teacher)}
                    disabled={deletingId === teacher.id}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Thêm tài khoản giáo viên">
        <div className="app-modal-body">
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Họ tên
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
          <label>
            Mật khẩu ban đầu
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
            />
          </label>
        </div>
        <div className="app-modal-footer">
          <button type="button" className="button secondary" onClick={() => setShowCreate(false)}>
            Hủy
          </button>
          <button
            type="button"
            className="button primary"
            onClick={handleCreate}
            disabled={creating || !email || !fullName || password.length < 8}
          >
            {creating ? "Đang tạo..." : "Tạo tài khoản"}
          </button>
        </div>
      </Modal>

      <Modal open={resettingId !== null} onClose={() => setResettingId(null)} title="Đặt lại mật khẩu">
        <div className="app-modal-body">
          <label>
            Mật khẩu mới (tối thiểu 8 ký tự)
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          </label>
        </div>
        <div className="app-modal-footer">
          <button type="button" className="button secondary" onClick={() => setResettingId(null)}>
            Hủy
          </button>
          <button type="button" className="button primary" onClick={handleResetPassword} disabled={saving}>
            {saving ? "Đang lưu..." : "Lưu"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

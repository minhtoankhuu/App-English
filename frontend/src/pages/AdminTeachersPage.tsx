import { useEffect, useState } from "react";
import { createTeacher, listTeachers, updateTeacher } from "../api/admin";
import { ApiError } from "../api/client";
import type { TeacherOut } from "../types/admin";

export function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<TeacherOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [resettingId, setResettingId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");

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

  async function handleResetPassword(teacherId: string) {
    if (newPassword.length < 8) {
      setError("Mật khẩu mới phải từ 8 ký tự");
      return;
    }
    setError(null);
    try {
      await updateTeacher(teacherId, { password: newPassword });
      setResettingId(null);
      setNewPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không đặt lại được mật khẩu");
    }
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Thêm tài khoản giáo viên</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label style={fieldStyle}>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} type="email" />
          </label>
          <label style={fieldStyle}>
            Họ tên
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} style={inputStyle} />
          </label>
          <label style={fieldStyle}>
            Mật khẩu ban đầu
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              type="password"
              minLength={8}
            />
          </label>
          <button
            onClick={handleCreate}
            disabled={creating || !email || !fullName || password.length < 8}
            style={primaryButtonStyle}
          >
            {creating ? "Đang tạo..." : "+ Tạo tài khoản"}
          </button>
        </div>
      </section>

      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Tài khoản giáo viên</h2>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        {!teachers && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
        {teachers && teachers.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có giáo viên nào.</p>}

        <div style={{ display: "grid", gap: 10 }}>
          {teachers?.map((teacher) => (
            <article key={teacher.id} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <strong>{teacher.full_name}</strong>
                  <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>{teacher.email}</p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      fontSize: 12,
                      padding: "3px 10px",
                      borderRadius: 999,
                      background: teacher.is_active ? "#e2f6ee" : "#fdecec",
                      color: teacher.is_active ? "#0f8a62" : "#c0392b",
                    }}
                  >
                    {teacher.is_active ? "Đang hoạt động" : "Đã khóa"}
                  </span>
                  <button onClick={() => handleToggleActive(teacher)} style={smallButtonStyle}>
                    {teacher.is_active ? "Khóa tài khoản" : "Mở lại"}
                  </button>
                  <button
                    onClick={() => setResettingId(resettingId === teacher.id ? null : teacher.id)}
                    style={smallButtonStyle}
                  >
                    Đặt lại mật khẩu
                  </button>
                </div>
              </div>

              {resettingId === teacher.id && (
                <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
                  <input
                    type="password"
                    placeholder="Mật khẩu mới (tối thiểu 8 ký tự)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <button onClick={() => handleResetPassword(teacher.id)} style={primaryButtonStyle}>
                    Lưu
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

const fieldStyle: React.CSSProperties = { display: "grid", gap: 4, fontSize: 13, fontWeight: 600 };

const inputStyle: React.CSSProperties = {
  height: 38,
  padding: "0 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 13,
};

const primaryButtonStyle: React.CSSProperties = {
  height: 38,
  padding: "0 16px",
  borderRadius: 8,
  border: "none",
  background: "var(--primary)",
  color: "#fff",
  fontWeight: 600,
};

const smallButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "#fff",
  fontSize: 12,
  fontWeight: 600,
};

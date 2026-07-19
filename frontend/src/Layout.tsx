import { Link, Outlet } from "react-router-dom";
import { logout } from "./api/auth";
import type { UserOut } from "./types/auth";

interface LayoutProps {
  user: UserOut;
  onLogout: () => void;
}

export function Layout({ user, onLogout }: LayoutProps) {
  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <div style={{ width: "100%", maxWidth: 960, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 20px",
          background: "var(--surface)",
          borderRadius: 12,
          marginBottom: 18,
        }}
      >
        <Link to="/exams" style={{ fontWeight: 700, color: "var(--primary)", textDecoration: "none" }}>
          ExamCraft AI
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "var(--muted)" }}>
            {user.full_name} · {user.role === "admin" ? "Quản trị viên" : "Giáo viên"}
          </span>
          <button
            onClick={handleLogout}
            style={{ border: "1px solid var(--border)", background: "#fff", borderRadius: 8, padding: "6px 12px" }}
          >
            Đăng xuất
          </button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

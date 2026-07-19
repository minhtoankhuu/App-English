import { Link, Outlet, useLocation } from "react-router-dom";
import { logout } from "./api/auth";
import type { UserOut } from "./types/auth";

interface LayoutProps {
  user: UserOut;
  onLogout: () => void;
}

export function Layout({ user, onLogout }: LayoutProps) {
  const location = useLocation();

  async function handleLogout() {
    await logout();
    onLogout();
  }

  const navLinks = [{ to: "/exams", label: "Đề của tôi" }];
  if (user.role === "admin") {
    navLinks.push({ to: "/admin/teachers", label: "Quản lý tài khoản" });
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
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <Link to="/exams" style={{ fontWeight: 700, color: "var(--primary)", textDecoration: "none" }}>
            ExamCraft AI
          </Link>
          <nav style={{ display: "flex", gap: 14 }}>
            {navLinks.map((link) => {
              const active = location.pathname.startsWith(link.to);
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  style={{
                    fontSize: 13,
                    fontWeight: active ? 700 : 500,
                    color: active ? "var(--primary)" : "var(--ink)",
                    textDecoration: "none",
                  }}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
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

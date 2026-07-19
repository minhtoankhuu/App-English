import { Link, Outlet, useLocation } from "react-router-dom";
import { logout } from "./api/auth";
import type { UserOut } from "./types/auth";
import { UsageProvider, useUsage } from "./usage/UsageContext";

interface LayoutProps {
  user: UserOut;
  onLogout: () => void;
}

function LayoutContent({ user, onLogout }: LayoutProps) {
  const location = useLocation();
  const { status } = useUsage();

  async function handleLogout() {
    await logout();
    onLogout();
  }

  const isAdmin = user.role === "admin";
  const homePath = isAdmin ? "/admin" : "/exams";
  const navLinks = isAdmin
    ? [{ to: "/admin", label: "Quản trị" }]
    : [{ to: "/exams", label: "Đề của tôi" }];

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
          <Link to={homePath} style={{ fontWeight: 700, color: "var(--primary)", textDecoration: "none" }}>
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
          {user.role === "teacher" && status && (
            <span style={{ fontSize: 13, color: "var(--primary)", fontWeight: 600 }}>
              Còn {status.remaining}/{status.limit} lượt hôm nay
            </span>
          )}
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

export function Layout(props: LayoutProps) {
  return (
    <UsageProvider user={props.user}>
      <LayoutContent {...props} />
    </UsageProvider>
  );
}

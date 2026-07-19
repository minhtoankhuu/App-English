import type { ComponentType } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { logout } from "./api/auth";
import type { UserOut } from "./types/auth";
import { UsageProvider, useUsage } from "./usage/UsageContext";
import { BankIcon, DocIcon, LayersIcon, PlusIcon, UsersIcon } from "./icons/Icon";

interface LayoutProps {
  user: UserOut;
  onLogout: () => void;
}

interface NavItem {
  to: string;
  label: string;
  Icon: ComponentType;
}

const TEACHER_NAV: NavItem[] = [
  { to: "/exams#tao-de", label: "Tạo đề", Icon: PlusIcon },
  { to: "/exams", label: "Đề của tôi", Icon: DocIcon },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Tổng quan", Icon: LayersIcon },
  { to: "/admin/teachers", label: "Quản lý giáo viên", Icon: UsersIcon },
  { to: "/admin/audit-logs", label: "Audit log", Icon: BankIcon },
];

function isNavActive(location: { pathname: string; hash: string }, to: string): boolean {
  const [toPath = "", toHash] = to.split("#");
  if (toPath === "/admin") return location.pathname === "/admin";
  if (toHash) return location.pathname === toPath && location.hash === `#${toHash}`;
  return location.pathname.startsWith(toPath) && !location.hash;
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
  const navItems = isAdmin ? ADMIN_NAV : TEACHER_NAV;
  const avatarLetter = user.full_name.trim().charAt(0).toUpperCase() || "?";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to={homePath} aria-label="ExamCraft AI">
          <span className="brand-mark">E</span>
          <span className="brand-name">
            ExamCraft <em>AI</em>
          </span>
        </Link>

        <nav className="main-nav" aria-label={isAdmin ? "Điều hướng quản trị" : "Điều hướng giáo viên"}>
          {navItems.map(({ to, label, Icon }) => (
            <Link key={to} to={to} className={`nav-item${isNavActive(location, to) ? " active" : ""}`}>
              <Icon />
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        {!isAdmin && status && (
          <p className="usage-badge">
            Còn {status.remaining}/{status.limit} lượt hôm nay
          </p>
        )}

        <div className="user-card">
          <span className="avatar">{avatarLetter}</span>
          <span className="user-meta">
            <strong>{user.full_name}</strong>
            <small>{isAdmin ? "Quản trị viên" : "Giáo viên"}</small>
          </span>
        </div>

        <button type="button" className="sidebar-logout" onClick={handleLogout}>
          Đăng xuất
        </button>
      </aside>

      <main className="main-content">
        <div className="workspace">
          <Outlet />
        </div>
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

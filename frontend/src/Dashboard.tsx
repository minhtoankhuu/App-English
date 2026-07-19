import { useEffect, useState } from "react";
import { fetchDashboardData } from "./api/dashboardData";
import { logout } from "./api/auth";
import { ApiError } from "./api/client";
import type { UserOut } from "./types/auth";
import type { DashboardData } from "./api/dashboardData";

interface DashboardProps {
  user: UserOut;
  onLogout: () => void;
}

export function Dashboard({ user, onLogout }: DashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDashboardData()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Không tải được danh mục");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <div style={{ width: 480, maxWidth: "100%", background: "var(--surface)", borderRadius: 16, padding: 28 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20 }}>Xin chào, {user.full_name}</h1>
          <p style={{ margin: "2px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Vai trò: {user.role === "admin" ? "Quản trị viên" : "Giáo viên"}
          </p>
        </div>
        <button
          onClick={handleLogout}
          style={{
            border: "1px solid var(--border)",
            background: "#fff",
            borderRadius: 8,
            padding: "8px 14px",
            fontWeight: 600,
          }}
        >
          Đăng xuất
        </button>
      </header>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!data && !error && <p style={{ color: "var(--muted)" }}>Đang tải danh mục từ backend...</p>}

      {data && (
        <div style={{ display: "grid", gap: 10 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
            Kết nối backend thành công — danh mục học thuật đã seed:
          </p>
          <StatRow label="Khối lớp" value={data.gradeCount} />
          <StatRow label="Unit (Global Success)" value={data.unitCount} />
          <StatRow label="Thì / cấu trúc câu" value={data.grammarPointCount} />
          <StatRow label="Dạng bài" value={data.exerciseTypeCount} />
          <div style={{ marginTop: 8, padding: 12, borderRadius: 10, background: "var(--page)", fontSize: 13 }}>
            <strong>Lớp 7 · Unit 3:</strong> {data.grade7Unit3Title ?? "—"}
          </div>
        </div>
      )}
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "8px 12px",
        border: "1px solid var(--border)",
        borderRadius: 8,
        fontSize: 14,
      }}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}


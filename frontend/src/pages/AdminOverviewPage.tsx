import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listKnowledgeDocuments, listTeachers } from "../api/admin";
import { listAuditLogs } from "../api/audit";
import { ACTION_LABELS } from "../types/audit";
import type { AuditLogOut } from "../types/audit";

type Stat = { status: "loading" } | { status: "success"; value: number } | { status: "error" };

const UPCOMING_SECTIONS = [
  { title: "Danh mục học thuật", description: "Khối lớp, cấp học, bộ sách, Unit và bảng ánh xạ trình độ — đã seed sẵn, chưa có màn chỉnh sửa." },
  { title: "Dạng bài & template chuẩn", description: "Schema, prompt, validation rule và renderer của từng dạng — chờ Giai đoạn 1D." },
  { title: "Cấu hình AI", description: "Provider, model, API key, embedding và reranker — chờ Giai đoạn 1D." },
];

function StatCard({ label, stat, suffix }: { label: string; stat: Stat; suffix: string }) {
  const text =
    stat.status === "loading" ? "Đang tải..." : stat.status === "error" ? "Không tải được dữ liệu" : `${stat.value} ${suffix}`;
  return (
    <div style={{ padding: 16, border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface)" }}>
      <p style={{ margin: "0 0 6px", fontSize: 12.5, color: "var(--muted)" }}>{label}</p>
      <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{text}</p>
    </div>
  );
}

export function AdminOverviewPage() {
  const [teacherStat, setTeacherStat] = useState<Stat>({ status: "loading" });
  const [knowledgeStat, setKnowledgeStat] = useState<Stat>({ status: "loading" });
  const [recentLogs, setRecentLogs] = useState<AuditLogOut[] | null>(null);
  const [logsError, setLogsError] = useState<string | null>(null);

  useEffect(() => {
    listTeachers()
      .then((teachers) => setTeacherStat({ status: "success", value: teachers.filter((t) => t.is_active).length }))
      .catch(() => setTeacherStat({ status: "error" }));
  }, []);

  useEffect(() => {
    listKnowledgeDocuments()
      .then((documents) => setKnowledgeStat({ status: "success", value: documents.filter((d) => d.is_published).length }))
      .catch(() => setKnowledgeStat({ status: "error" }));
  }, []);

  useEffect(() => {
    listAuditLogs(5, 0)
      .then((page) => setRecentLogs(page.items))
      .catch(() => setLogsError("Không tải được hoạt động gần đây"));
  }, []);

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div>
        <h2 style={{ margin: "0 0 4px" }}>Quản trị hệ thống</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>Tổng quan hoạt động — dùng menu bên trái để vào từng phân hệ.</p>
      </div>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}>
        <StatCard label="Giáo viên đang hoạt động" stat={teacherStat} suffix="giáo viên" />
        <StatCard label="Tài liệu kho kiến thức đã xuất bản" stat={knowledgeStat} suffix="tài liệu" />
      </div>

      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <h3 style={{ margin: 0 }}>Hoạt động gần đây</h3>
          <Link to="/admin/audit-logs" className="button secondary compact">
            Xem tất cả
          </Link>
        </div>

        {logsError && <p style={{ color: "var(--danger)" }}>{logsError}</p>}
        {!recentLogs && !logsError && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
        {recentLogs && recentLogs.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có hoạt động nào.</p>}
        {recentLogs && recentLogs.length > 0 && (
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
            {recentLogs.map((log) => (
              <li key={log.id} style={{ fontSize: 13, display: "flex", gap: 8, justifyContent: "space-between" }}>
                <span>
                  <strong>{log.actor_email}</strong> — {ACTION_LABELS[log.action] ?? log.action}
                  {log.target_label ? ` (${log.target_label})` : ""}
                </span>
                <span style={{ color: "var(--muted)", whiteSpace: "nowrap" }}>
                  {new Date(log.created_at).toLocaleString("vi-VN")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h3 style={{ margin: "0 0 10px" }}>Sắp triển khai</h3>
        <div style={{ display: "grid", gap: 10 }}>
          {UPCOMING_SECTIONS.map((section) => (
            <div key={section.title}>
              <p style={{ margin: "0 0 2px", fontWeight: 600, fontSize: 13.5 }}>{section.title}</p>
              <p style={{ margin: 0, fontSize: 12.5, color: "var(--muted)" }}>{section.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

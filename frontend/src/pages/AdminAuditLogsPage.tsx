import { useEffect, useState } from "react";
import { listAuditLogs } from "../api/audit";
import { ACTION_LABELS } from "../types/audit";
import type { AuditLogOut, AuditLogPage } from "../types/audit";

const PAGE_SIZE = 20;

function describeDetails(log: AuditLogOut): string {
  const changedFields = log.details.changed_fields;
  if (Array.isArray(changedFields) && changedFields.includes("full_name")) {
    return "Thay đổi: họ tên";
  }
  return "—";
}

export function AdminAuditLogsPage() {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<AuditLogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listAuditLogs(PAGE_SIZE, offset)
      .then(setPage)
      .catch(() => {
        setPage(null);
        setError("Không tải được audit log");
      })
      .finally(() => setLoading(false));
  }, [offset]);

  const hasPrevious = offset > 0;
  const hasNext = page !== null && offset + page.items.length < page.total;
  const pageNumber = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
      <h2 style={{ marginTop: 0 }}>Audit log</h2>
      <p style={{ color: "var(--muted)", fontSize: 13 }}>
        Lịch sử chỉ đọc cho các thao tác quản trị tài khoản giáo viên.
      </p>

      {loading && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
      {!loading && error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!loading && !error && page?.items.length === 0 && <p>Chưa có hoạt động nào.</p>}

      {!loading && !error && page && page.items.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <th style={cellStyle}>Thời gian</th>
                <th style={cellStyle}>Người thực hiện</th>
                <th style={cellStyle}>Hành động</th>
                <th style={cellStyle}>Tài khoản đích</th>
                <th style={cellStyle}>Chi tiết</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((log) => (
                <tr key={log.id}>
                  <td style={cellStyle}>{new Date(log.created_at).toLocaleString("vi-VN")}</td>
                  <td style={cellStyle}>{log.actor_email}</td>
                  <td style={cellStyle}>{ACTION_LABELS[log.action] ?? log.action}</td>
                  <td style={cellStyle}>{log.target_label}</td>
                  <td style={cellStyle}>{describeDetails(log)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && page && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
          <button disabled={!hasPrevious} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Trang trước
          </button>
          <span>Trang {pageNumber}</span>
          <button disabled={!hasNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Trang sau
          </button>
        </div>
      )}
    </section>
  );
}

const cellStyle: React.CSSProperties = {
  borderBottom: "1px solid var(--border)",
  padding: "10px 8px",
  textAlign: "left",
  verticalAlign: "top",
};

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadExportUrl, getExam, saveExportConfig } from "../api/exams";
import { ApiError } from "../api/client";
import type { ExamDetailOut, ExportMode } from "../types/exam";

const VARIANT_CODES = ["A", "B", "C", "D"];

export function ExamExportPage() {
  const { examId } = useParams<{ examId: string }>();
  const [exam, setExam] = useState<ExamDetailOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [exportMode, setExportMode] = useState<ExportMode>("plain");
  const [variantCount, setVariantCount] = useState(1);

  function reload() {
    if (!examId) return;
    getExam(examId)
      .then((detail) => {
        setExam(detail);
        setExportMode(detail.export_mode ?? "plain");
        setVariantCount(detail.variant_count || 1);
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được đề"));
  }

  useEffect(reload, [examId]);

  if (!exam) {
    return <p style={{ color: error ? "var(--danger)" : "var(--muted)" }}>{error ?? "Đang tải..."}</p>;
  }

  async function handleSave() {
    if (!examId) return;
    setSaving(true);
    setError(null);
    try {
      await saveExportConfig(examId, { export_mode: exportMode, variant_count: variantCount });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chưa lưu được cấu hình xuất");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <Link to="/exams" style={{ fontSize: 13 }}>
        ← Đề của tôi
      </Link>

      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20, maxWidth: 520 }}>
        <h2 style={{ marginTop: 0 }}>Xuất DOCX</h2>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>{exam.title}</p>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        <div style={{ display: "grid", gap: 8, marginBottom: 14 }}>
          <label style={radioRowStyle}>
            <input
              type="radio"
              checked={exportMode === "plain"}
              onChange={() => setExportMode("plain")}
            />
            Chỉ đề (không kèm đáp án) — bản phát cho học sinh
          </label>
          <label style={radioRowStyle}>
            <input
              type="radio"
              checked={exportMode === "answer_key"}
              onChange={() => setExportMode("answer_key")}
            />
            Đề có đáp án <span style={{ color: "#c0392b", fontWeight: 700 }}>tô đỏ</span> — bản dành cho giáo viên
          </label>
        </div>

        <label style={{ display: "grid", gap: 4, fontSize: 13, fontWeight: 600, marginBottom: 14 }}>
          Số mã đề
          <select
            value={variantCount}
            onChange={(e) => setVariantCount(Number(e.target.value))}
            style={{ height: 36, borderRadius: 8, border: "1px solid var(--border)", padding: "0 8px" }}
          >
            <option value={1}>1 mã</option>
            <option value={2}>2 mã (A/B)</option>
            <option value={3}>3 mã (A/B/C)</option>
            <option value={4}>4 mã (A/B/C/D)</option>
          </select>
        </label>

        <button onClick={handleSave} disabled={saving} style={primaryButtonStyle}>
          {saving ? "Đang lưu..." : "Lưu vào Đề của tôi"}
        </button>

        {exam.status === "ready" && (
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Tải DOCX:</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {VARIANT_CODES.slice(0, exam.variant_count).map((code) => (
                <a key={code} href={downloadExportUrl(exam.id, code)} style={downloadLinkStyle}>
                  Mã đề {code}
                </a>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

const radioRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  fontSize: 13,
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "8px 10px",
};

const primaryButtonStyle: React.CSSProperties = {
  height: 40,
  padding: "0 16px",
  borderRadius: 8,
  border: "none",
  background: "var(--primary)",
  color: "#fff",
  fontWeight: 600,
};

const downloadLinkStyle: React.CSSProperties = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  textDecoration: "none",
  color: "var(--ink)",
  fontSize: 13,
  fontWeight: 600,
};

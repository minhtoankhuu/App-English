import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadExportUrl, getExam, saveExportConfig } from "../api/exams";
import { ApiError } from "../api/client";
import type { ExamDetailOut, ExportMode } from "../types/exam";
import { useRouteGeneration, type RouteGenerationToken } from "../routing/useRouteGeneration";
import { StepsIndicator } from "../components/StepsIndicator";

const VARIANT_CODES = ["A", "B", "C", "D"];

interface SaveOperation {
  id: number;
  route: RouteGenerationToken;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

export function ExamExportPage() {
  const { examId } = useParams<{ examId: string }>();
  const routeGeneration = useRouteGeneration(examId);
  const [exam, setExam] = useState<ExamDetailOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [exportMode, setExportMode] = useState<ExportMode>("plain");
  const [variantCount, setVariantCount] = useState(1);
  const activeSave = useRef<SaveOperation | null>(null);
  const nextOperationId = useRef(0);

  const reload = useCallback(async (targetExamId: string, token: RouteGenerationToken): Promise<boolean> => {
    try {
      const detail = await getExam(targetExamId);
      if (!routeGeneration.isCurrent(token) || detail.id !== targetExamId) return false;
      setExam(detail);
      setExportMode(detail.export_mode ?? "plain");
      setVariantCount(detail.variant_count || 1);
      setError(null);
      return true;
    } catch (err) {
      if (!routeGeneration.isCurrent(token)) return false;
      setError(errorMessage(err, "Không tải được đề"));
      return false;
    }
  }, [routeGeneration]);

  useEffect(() => {
    setExam(null);
    setError(null);
    setSaving(false);
    setExportMode("plain");
    setVariantCount(1);
    activeSave.current = null;
    if (!examId) return;
    const token = routeGeneration.capture();
    void reload(examId, token);
  }, [examId, reload, routeGeneration]);

  if (!exam || exam.id !== examId) {
    return <p style={{ color: error ? "var(--danger)" : "var(--muted)" }}>{error ?? "Đang tải..."}</p>;
  }

  async function handleSave() {
    if (!examId || activeSave.current) return;
    const targetExamId = examId;
    const targetMode = exportMode;
    const targetVariantCount = variantCount;
    const operation = { id: ++nextOperationId.current, route: routeGeneration.capture() };
    activeSave.current = operation;
    setSaving(true);
    setError(null);
    try {
      await saveExportConfig(targetExamId, { export_mode: targetMode, variant_count: targetVariantCount });
      if (!isCurrentSave(operation)) return;
      await reload(targetExamId, operation.route);
    } catch (err) {
      if (isCurrentSave(operation)) setError(errorMessage(err, "Chưa lưu được cấu hình xuất"));
    } finally {
      if (isCurrentSave(operation)) {
        activeSave.current = null;
        setSaving(false);
      }
    }
  }

  function isCurrentSave(operation: SaveOperation) {
    return routeGeneration.isCurrent(operation.route) && activeSave.current?.id === operation.id;
  }

  return (
    <>
      <StepsIndicator current={4} />
      <div style={{ display: "grid", gap: 14 }}>
        <Link to="/exams" className="button secondary compact" style={{ justifySelf: "start" }}>
          ← Đề của tôi
        </Link>

        <section className="configuration export-card">
          <div>
            <h2>Xuất DOCX</h2>
            <p className="export-meta">{exam.title}</p>
          </div>
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

          <div className="export-options" role="radiogroup" aria-label="Kiểu xuất">
            <label className="radio-row">
              <input type="radio" checked={exportMode === "plain"} onChange={() => setExportMode("plain")} />
              Chỉ đề (không kèm đáp án) — bản phát cho học sinh
            </label>
            <label className="radio-row">
              <input type="radio" checked={exportMode === "answer_key"} onChange={() => setExportMode("answer_key")} />
              Đề có đáp án <span className="answer-red">tô đỏ</span> — bản dành cho giáo viên
            </label>
          </div>

          <label>
            Số mã đề
            <select value={variantCount} onChange={(e) => setVariantCount(Number(e.target.value))}>
              <option value={1}>1 mã</option>
              <option value={2}>2 mã (A/B)</option>
              <option value={3}>3 mã (A/B/C)</option>
              <option value={4}>4 mã (A/B/C/D)</option>
            </select>
          </label>

          <div className="export-actions">
            <button type="button" onClick={handleSave} disabled={saving} className="button primary">
              {saving ? "Đang lưu..." : "Lưu vào Đề của tôi"}
            </button>
          </div>

          {exam.status === "ready" && (
            <div style={{ marginTop: 4, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
              <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Tải DOCX:</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {VARIANT_CODES.slice(0, exam.variant_count).map((code) => (
                  <a key={code} href={downloadExportUrl(exam.id, code)} className="button secondary compact">
                    Mã đề {code}
                  </a>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </>
  );
}

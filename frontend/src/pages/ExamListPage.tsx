import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { downloadExportUrl, listExams } from "../api/exams";
import { ApiError } from "../api/client";
import type { ExamSummaryOut } from "../types/exam";

const STATUS_LABEL: Record<string, string> = {
  draft: "Nháp",
  reviewed: "Đã kiểm duyệt",
  ready: "Sẵn sàng xuất",
};

const VARIANT_CODES = ["A", "B", "C", "D"];

export function ExamListPage() {
  const [exams, setExams] = useState<ExamSummaryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    listExams()
      .then(setExams)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được danh sách đề"));
  }

  useEffect(reload, []);

  return (
    <section className="configuration">
      <div className="section-heading">
        <div>
          <h2>Đề của tôi</h2>
          <p>Toàn bộ đề bạn đã tạo — chỉnh sửa, duyệt câu hoặc tải DOCX khi đề đã sẵn sàng xuất.</p>
        </div>
      </div>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!exams && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
      {exams && exams.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có đề nào. Bấm "Tạo đề" ở menu bên trái để bắt đầu.</p>}
      <div className="exam-list" style={{ marginTop: exams && exams.length > 0 ? 14 : 0 }}>
        {exams?.map((exam) => (
          <article key={exam.id} className="exam-row">
            <div className="exam-info">
              <h3>{exam.title}</h3>
              <p className="exam-meta">
                Lớp {exam.grade_number} · {exam.level_code} · {exam.total_questions} câu · {exam.total_points} điểm
              </p>
            </div>
            <span className={`status-pill${exam.status === "ready" ? " ready" : exam.status === "reviewed" ? " reviewed" : ""}`}>
              {STATUS_LABEL[exam.status]}
            </span>
            <div className="exam-actions">
              <Link to={`/exams/${exam.id}/builder`} className="button secondary compact">
                Chỉnh sửa
              </Link>
              <Link to={`/exams/${exam.id}/review`} className="button secondary compact">
                Duyệt câu
              </Link>
              {exam.status === "ready" ? (
                VARIANT_CODES.slice(0, exam.variant_count).map((code) => (
                  <a key={code} href={downloadExportUrl(exam.id, code)} className="button secondary compact">
                    Tải mã đề {code}
                  </a>
                ))
              ) : exam.status !== "draft" ? (
                <Link to={`/exams/${exam.id}/export`} className="button secondary compact">
                  Xuất
                </Link>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

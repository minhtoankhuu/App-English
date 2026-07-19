import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createExam, listExams } from "../api/exams";
import {
  listCambridgeCertificates,
  listGrades,
  listGrammarTopics,
  listProficiencyLevels,
  listUnitsForGrade,
} from "../api/catalog";
import { ApiError } from "../api/client";
import type { ExamSummaryOut, SourceType } from "../types/exam";
import type {
  CambridgeCertificateOut,
  GradeOut,
  GrammarTopicOut,
  ProficiencyLevelOut,
  UnitOut,
} from "../types/catalog";

const STATUS_LABEL: Record<string, string> = {
  draft: "Nháp",
  reviewed: "Đã kiểm duyệt",
  ready: "Sẵn sàng xuất",
};

export function ExamListPage() {
  const navigate = useNavigate();
  const [exams, setExams] = useState<ExamSummaryOut[] | null>(null);
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [levels, setLevels] = useState<ProficiencyLevelOut[]>([]);
  const [certificates, setCertificates] = useState<CambridgeCertificateOut[]>([]);
  const [grammarTopics, setGrammarTopics] = useState<GrammarTopicOut[]>([]);
  const [units, setUnits] = useState<UnitOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [title, setTitle] = useState("Đề kiểm tra mới");
  const [gradeId, setGradeId] = useState("");
  const [levelId, setLevelId] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("global_success");
  const [unitId, setUnitId] = useState("");
  const [grammarTopicId, setGrammarTopicId] = useState("");
  const [certificateId, setCertificateId] = useState("");

  function reload() {
    listExams()
      .then(setExams)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được danh sách đề"));
  }

  useEffect(() => {
    reload();
    Promise.all([listGrades(), listProficiencyLevels(), listGrammarTopics(), listCambridgeCertificates()]).then(
      ([g, l, topics, certs]) => {
        setGrades(g);
        setLevels(l);
        setGrammarTopics(topics);
        setCertificates(certs);
        if (g.length > 0) setGradeId(g[0]!.id);
        if (l.length > 0) setLevelId(l[0]!.id);
        if (topics.length > 0) setGrammarTopicId(topics[0]!.id);
        if (certs.length > 0) setCertificateId(certs[0]!.id);
      },
    );
  }, []);

  useEffect(() => {
    if (sourceType !== "global_success" || !gradeId) {
      setUnits([]);
      return;
    }
    listUnitsForGrade(gradeId).then((u) => {
      setUnits(u);
      setUnitId(u.length > 0 ? u[0]!.id : "");
    });
  }, [sourceType, gradeId]);

  const sourceReady =
    (sourceType === "global_success" && unitId !== "") ||
    (sourceType === "common_knowledge" && grammarTopicId !== "") ||
    (sourceType === "cambridge" && certificateId !== "");

  async function handleCreate() {
    if (!gradeId || !levelId || !sourceReady) return;
    setCreating(true);
    setError(null);
    try {
      const exam = await createExam({
        title,
        grade_id: gradeId,
        level_id: levelId,
        source_type: sourceType,
        unit_id: sourceType === "global_success" ? unitId : undefined,
        grammar_topic_id: sourceType === "common_knowledge" ? grammarTopicId : undefined,
        cambridge_certificate_id: sourceType === "cambridge" ? certificateId : undefined,
      });
      navigate(`/exams/${exam.id}/builder`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không tạo được đề");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <section className="configuration">
        <div className="section-heading">
          <div>
            <h2>Tạo đề mới</h2>
            <p>Chọn phạm vi kiến thức trước khi sang bước cấu trúc đề.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            Tên đề
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Khối lớp
            <select value={gradeId} onChange={(e) => setGradeId(e.target.value)}>
              {grades.map((g) => (
                <option key={g.id} value={g.id}>
                  Lớp {g.number}
                </option>
              ))}
            </select>
          </label>
          <label>
            Trình độ
            <select value={levelId} onChange={(e) => setLevelId(e.target.value)}>
              {levels.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code}
                </option>
              ))}
            </select>
          </label>
          <label>
            Nguồn kiến thức
            <select value={sourceType} onChange={(e) => setSourceType(e.target.value as SourceType)}>
              <option value="global_success">Global Success</option>
              <option value="common_knowledge">Kiến thức chung</option>
              <option value="cambridge">Cambridge</option>
            </select>
          </label>

          {sourceType === "global_success" && (
            <label>
              Unit
              <select value={unitId} onChange={(e) => setUnitId(e.target.value)}>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    Unit {u.order_no} — {u.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          {sourceType === "common_knowledge" && (
            <label>
              Chuyên đề
              <select value={grammarTopicId} onChange={(e) => setGrammarTopicId(e.target.value)}>
                {grammarTopics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {sourceType === "cambridge" && (
            <label>
              Chứng chỉ
              <select value={certificateId} onChange={(e) => setCertificateId(e.target.value)}>
                {certificates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="config-footer">
          <button type="button" onClick={handleCreate} disabled={creating || !sourceReady} className="button primary large">
            + Tạo đề
          </button>
        </div>
      </section>

      <section className="configuration">
        <div className="section-heading">
          <div>
            <h2>Đề của tôi</h2>
          </div>
        </div>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        {!exams && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
        {exams && exams.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có đề nào.</p>}
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
                {exam.status !== "draft" && (
                  <Link to={`/exams/${exam.id}/export`} className="button secondary compact">
                    Xuất
                  </Link>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

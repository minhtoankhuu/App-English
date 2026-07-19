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
      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Tạo đề mới</h2>
        <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <label style={fieldStyle}>
            Tên đề
            <input value={title} onChange={(e) => setTitle(e.target.value)} style={inputStyle} />
          </label>
          <label style={fieldStyle}>
            Khối lớp
            <select value={gradeId} onChange={(e) => setGradeId(e.target.value)} style={inputStyle}>
              {grades.map((g) => (
                <option key={g.id} value={g.id}>
                  Lớp {g.number}
                </option>
              ))}
            </select>
          </label>
          <label style={fieldStyle}>
            Trình độ
            <select value={levelId} onChange={(e) => setLevelId(e.target.value)} style={inputStyle}>
              {levels.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code}
                </option>
              ))}
            </select>
          </label>
          <label style={fieldStyle}>
            Nguồn kiến thức
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              style={inputStyle}
            >
              <option value="global_success">Global Success</option>
              <option value="common_knowledge">Kiến thức chung</option>
              <option value="cambridge">Cambridge</option>
            </select>
          </label>

          {sourceType === "global_success" && (
            <label style={fieldStyle}>
              Unit
              <select value={unitId} onChange={(e) => setUnitId(e.target.value)} style={inputStyle}>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    Unit {u.order_no} — {u.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          {sourceType === "common_knowledge" && (
            <label style={fieldStyle}>
              Chuyên đề
              <select value={grammarTopicId} onChange={(e) => setGrammarTopicId(e.target.value)} style={inputStyle}>
                {grammarTopics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {sourceType === "cambridge" && (
            <label style={fieldStyle}>
              Chứng chỉ
              <select value={certificateId} onChange={(e) => setCertificateId(e.target.value)} style={inputStyle}>
                {certificates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div style={{ marginTop: 12 }}>
          <button onClick={handleCreate} disabled={creating || !sourceReady} style={primaryButtonStyle}>
            {creating ? "Đang tạo..." : "+ Tạo đề"}
          </button>
        </div>
      </section>

      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Đề của tôi</h2>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        {!exams && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
        {exams && exams.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có đề nào.</p>}
        <div style={{ display: "grid", gap: 10 }}>
          {exams?.map((exam) => (
            <article
              key={exam.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "12px 14px",
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              <div>
                <strong>{exam.title}</strong>
                <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  Lớp {exam.grade_number} · {exam.level_code} · {exam.total_questions} câu · {exam.total_points} điểm
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    fontSize: 12,
                    padding: "3px 10px",
                    borderRadius: 999,
                    background: exam.status === "ready" ? "#e2f6ee" : "#eef1f6",
                    color: exam.status === "ready" ? "#0f8a62" : "#64748b",
                  }}
                >
                  {STATUS_LABEL[exam.status]}
                </span>
                <Link to={`/exams/${exam.id}/builder`} style={linkButtonStyle}>
                  Chỉnh sửa
                </Link>
                <Link to={`/exams/${exam.id}/review`} style={linkButtonStyle}>
                  Duyệt câu
                </Link>
                {exam.status !== "draft" && (
                  <Link to={`/exams/${exam.id}/export`} style={linkButtonStyle}>
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

const fieldStyle: React.CSSProperties = { display: "grid", gap: 4, fontSize: 13, fontWeight: 600 };

const inputStyle: React.CSSProperties = {
  height: 38,
  padding: "0 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 13,
};

const primaryButtonStyle: React.CSSProperties = {
  height: 38,
  padding: "0 16px",
  borderRadius: 8,
  border: "none",
  background: "var(--primary)",
  color: "#fff",
  fontWeight: 600,
};

const linkButtonStyle: React.CSSProperties = {
  fontSize: 13,
  padding: "6px 10px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  textDecoration: "none",
  color: "var(--ink)",
};

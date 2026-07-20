import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createExam } from "../api/exams";
import {
  listCambridgeCertificates,
  listGrades,
  listGrammarTopics,
  listProficiencyLevels,
  listUnitsForGrade,
} from "../api/catalog";
import { ApiError } from "../api/client";
import type { SourceType } from "../types/exam";
import type {
  CambridgeCertificateOut,
  GradeOut,
  GrammarTopicOut,
  ProficiencyLevelOut,
  UnitOut,
} from "../types/catalog";
import { StepsIndicator } from "../components/StepsIndicator";

type ExamCategory = "unit_revision" | "midterm1" | "final1" | "semester2";

const EXAM_CATEGORY_LABEL: Record<ExamCategory, string> = {
  unit_revision: "Ôn tập theo Unit",
  midterm1: "Kiểm tra giữa kì 1",
  final1: "Kiểm tra cuối kì 1",
  semester2: "Kiểm tra học kì 2",
};

export function ExamCreatePage() {
  const navigate = useNavigate();
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [levels, setLevels] = useState<ProficiencyLevelOut[]>([]);
  const [certificates, setCertificates] = useState<CambridgeCertificateOut[]>([]);
  const [grammarTopics, setGrammarTopics] = useState<GrammarTopicOut[]>([]);
  const [units, setUnits] = useState<UnitOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [examCategory, setExamCategory] = useState<ExamCategory>("unit_revision");
  const [title, setTitle] = useState("Đề kiểm tra mới");
  const [gradeId, setGradeId] = useState("");
  const [levelId, setLevelId] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("global_success");
  const [unitId, setUnitId] = useState("");
  const [grammarTopicId, setGrammarTopicId] = useState("");
  const [certificateId, setCertificateId] = useState("");

  useEffect(() => {
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

  const selectedGrade = grades.find((g) => g.id === gradeId);
  const selectedUnit = units.find((u) => u.id === unitId);
  const autoTitle =
    examCategory === "unit_revision" && sourceType === "global_success" && selectedGrade && selectedUnit
      ? `UNIT ${selectedUnit.order_no} REVISION EXERCISES – GLOBAL SUCCESS ${selectedGrade.number}`
      : null;

  useEffect(() => {
    if (autoTitle) setTitle(autoTitle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoTitle]);

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
    <>
      <StepsIndicator current={1} />
      <section className="configuration">
        <div className="section-heading">
          <div>
            <h2>Tạo đề mới</h2>
            <p>Chọn phạm vi kiến thức trước khi sang bước cấu trúc đề.</p>
          </div>
        </div>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        <div className="form-grid">
          <label>
            Loại đề
            <select value={examCategory} onChange={(e) => setExamCategory(e.target.value as ExamCategory)}>
              {(Object.keys(EXAM_CATEGORY_LABEL) as ExamCategory[]).map((category) => (
                <option key={category} value={category}>
                  {EXAM_CATEGORY_LABEL[category]}
                </option>
              ))}
            </select>
          </label>
        </div>

        {examCategory !== "unit_revision" ? (
          <p style={{ color: "var(--muted)" }}>
            "{EXAM_CATEGORY_LABEL[examCategory]}" sắp ra mắt — hiện tại chỉ dùng được "Ôn tập theo Unit".
          </p>
        ) : (
        <div className="form-grid">
          <label>
            Tên đề
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              readOnly={Boolean(autoTitle)}
              title={autoTitle ? "Tự động đặt theo Unit và Global Success đã chọn" : undefined}
            />
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
        )}
        <div className="config-footer">
          <button
            type="button"
            onClick={handleCreate}
            disabled={creating || !sourceReady || examCategory !== "unit_revision"}
            className="button primary large"
          >
            + Tạo đề
          </button>
        </div>
      </section>
    </>
  );
}

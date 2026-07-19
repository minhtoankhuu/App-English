import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  addBlock,
  deleteBlock,
  generateExam,
  getExam,
  reorderBlocks,
  setGrammarSelection,
  updateBlock,
} from "../api/exams";
import { listExerciseTypes, listGrammarTopics } from "../api/catalog";
import { ApiError } from "../api/client";
import type { ExamDetailOut, BlockOut, Difficulty } from "../types/exam";
import type { ExerciseTypeOut, GrammarTopicOut } from "../types/catalog";
import { useUsage } from "../usage/UsageContext";

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  nhan_biet: "Nhận biết",
  thong_hieu: "Thông hiểu",
  van_dung: "Vận dụng",
  hon_hop: "Hỗn hợp",
};

export function ExamBuilderPage() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const { refresh: refreshUsage } = useUsage();
  const [exam, setExam] = useState<ExamDetailOut | null>(null);
  const [exerciseTypes, setExerciseTypes] = useState<ExerciseTypeOut[]>([]);
  const [grammarTopics, setGrammarTopics] = useState<GrammarTopicOut[]>([]);
  const [selectedPoints, setSelectedPoints] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const [newTypeId, setNewTypeId] = useState("");
  const [newCount, setNewCount] = useState(5);
  const [newPoints, setNewPoints] = useState(1);

  function reload() {
    if (!examId) return;
    getExam(examId)
      .then((detail) => {
        setExam(detail);
        setSelectedPoints(new Set(detail.grammar_point_ids));
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được đề"));
  }

  useEffect(() => {
    reload();
    listExerciseTypes().then((types) => {
      setExerciseTypes(types);
      if (types.length > 0) setNewTypeId(types[0]!.id);
    });
    listGrammarTopics().then(setGrammarTopics);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  if (!exam) {
    return <p style={{ color: error ? "var(--danger)" : "var(--muted)" }}>{error ?? "Đang tải..."}</p>;
  }

  async function handleAddBlock() {
    if (!examId || !newTypeId) return;
    const type = exerciseTypes.find((t) => t.id === newTypeId);
    try {
      await addBlock(examId, {
        exercise_type_id: newTypeId,
        title: type ? type.name : "Phần mới",
        question_count: newCount,
        points: newPoints,
      });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thêm được phần");
    }
  }

  async function handleDeleteBlock(blockId: string) {
    if (!examId) return;
    await deleteBlock(examId, blockId);
    reload();
  }

  async function handleMove(block: BlockOut, direction: -1 | 1) {
    if (!examId || !exam) return;
    const ordered = [...exam.blocks].sort((a, b) => a.order_no - b.order_no);
    const idx = ordered.findIndex((b) => b.id === block.id);
    const swapIdx = idx + direction;
    if (swapIdx < 0 || swapIdx >= ordered.length) return;
    [ordered[idx], ordered[swapIdx]] = [ordered[swapIdx]!, ordered[idx]!];
    await reorderBlocks(
      examId,
      ordered.map((b) => b.id),
    );
    reload();
  }

  async function handleBlockField(block: BlockOut, field: "question_count" | "points", value: number) {
    if (!examId) return;
    await updateBlock(examId, block.id, { [field]: value });
    reload();
  }

  function togglePoint(pointId: string) {
    setSelectedPoints((prev) => {
      const next = new Set(prev);
      if (next.has(pointId)) next.delete(pointId);
      else next.add(pointId);
      return next;
    });
  }

  async function handleSaveGrammarSelection() {
    if (!examId) return;
    await setGrammarSelection(examId, Array.from(selectedPoints));
    reload();
  }

  async function handleGenerate() {
    if (!examId) return;
    setGenerating(true);
    setError(null);
    try {
      await generateExam(examId);
      await refreshUsage();
      navigate(`/exams/${examId}/review`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không sinh được đề");
    } finally {
      setGenerating(false);
    }
  }

  const activeTopic = grammarTopics.find((t) => t.id === exam.grammar_topic_id);
  const orderedBlocks = [...exam.blocks].sort((a, b) => a.order_no - b.order_no);

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>{exam.title}</h2>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        {activeTopic && (
          <div style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 8, fontSize: 15 }}>Chọn {activeTopic.name.split(" — ")[0]}</h3>
            {activeTopic.groups.map((group) => (
              <div key={group.id} style={{ marginBottom: 8 }}>
                <p style={{ margin: "0 0 4px", fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>
                  {group.name}
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {group.points.map((point) => (
                    <label
                      key={point.id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 10px",
                        borderRadius: 999,
                        border: "1px solid var(--border)",
                        fontSize: 12,
                        background: selectedPoints.has(point.id) ? "#ecf1fe" : "#fff",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedPoints.has(point.id)}
                        onChange={() => togglePoint(point.id)}
                      />
                      {point.name} ({point.min_level.code})
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button onClick={handleSaveGrammarSelection} style={secondaryButtonStyle}>
              Lưu lựa chọn
            </button>
          </div>
        )}

        <h3 style={{ fontSize: 15 }}>Các phần của đề</h3>
        <div style={{ display: "grid", gap: 8 }}>
          {orderedBlocks.map((block, idx) => (
            <article key={block.id} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <div>
                  <strong>
                    {idx + 1}. {block.title}
                  </strong>
                  <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>
                    {block.exercise_type.name} · {DIFFICULTY_LABEL[block.difficulty]}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  <button onClick={() => handleMove(block, -1)} style={iconButtonStyle} aria-label="Lên">
                    ↑
                  </button>
                  <button onClick={() => handleMove(block, 1)} style={iconButtonStyle} aria-label="Xuống">
                    ↓
                  </button>
                  <button onClick={() => handleDeleteBlock(block.id)} style={iconButtonStyle} aria-label="Xóa">
                    ✕
                  </button>
                </div>
              </div>
              <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                <label style={{ fontSize: 12 }}>
                  Số câu{" "}
                  <input
                    type="number"
                    min={1}
                    max={50}
                    defaultValue={block.question_count}
                    onBlur={(e) => handleBlockField(block, "question_count", Number(e.target.value))}
                    style={{ width: 60, marginLeft: 4 }}
                  />
                </label>
                <label style={{ fontSize: 12 }}>
                  Điểm{" "}
                  <input
                    type="number"
                    min={0}
                    max={10}
                    step={0.5}
                    defaultValue={block.points}
                    onBlur={(e) => handleBlockField(block, "points", Number(e.target.value))}
                    style={{ width: 60, marginLeft: 4 }}
                  />
                </label>
              </div>
            </article>
          ))}
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 14, flexWrap: "wrap" }}>
          <label style={{ display: "grid", gap: 4, fontSize: 12 }}>
            Dạng bài
            <select value={newTypeId} onChange={(e) => setNewTypeId(e.target.value)} style={inputStyle}>
              {exerciseTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "grid", gap: 4, fontSize: 12 }}>
            Số câu
            <input
              type="number"
              min={1}
              max={50}
              value={newCount}
              onChange={(e) => setNewCount(Number(e.target.value))}
              style={{ ...inputStyle, width: 70 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4, fontSize: 12 }}>
            Điểm
            <input
              type="number"
              min={0}
              max={10}
              step={0.5}
              value={newPoints}
              onChange={(e) => setNewPoints(Number(e.target.value))}
              style={{ ...inputStyle, width: 70 }}
            />
          </label>
          <button onClick={handleAddBlock} style={secondaryButtonStyle}>
            + Thêm phần
          </button>
        </div>

        <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
          <button onClick={handleGenerate} disabled={generating || exam.blocks.length === 0} style={primaryButtonStyle}>
            {generating ? "Đang sinh đề..." : "✦ Sinh đề bằng AI"}
          </button>
        </div>
      </section>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  height: 34,
  padding: "0 8px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 13,
};

const primaryButtonStyle: React.CSSProperties = {
  height: 42,
  padding: "0 18px",
  borderRadius: 8,
  border: "none",
  background: "var(--primary)",
  color: "#fff",
  fontWeight: 600,
};

const secondaryButtonStyle: React.CSSProperties = {
  height: 34,
  padding: "0 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "#fff",
  fontWeight: 600,
  fontSize: 13,
};

const iconButtonStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  border: "1px solid var(--border)",
  borderRadius: 6,
  background: "#fff",
};

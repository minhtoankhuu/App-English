import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  addBlock,
  deleteBlock,
  generateExam,
  getExam,
  getExamPreview,
  reorderBlocks,
  setGrammarSelection,
  updateBlock,
} from "../api/exams";
import { listExerciseTypes, listGrammarTopics } from "../api/catalog";
import { ApiError } from "../api/client";
import type { ExamDetailOut, BlockOut } from "../types/exam";
import type { ExerciseTypeOut, GrammarTopicOut } from "../types/catalog";
import type { ExamPreviewOut } from "../types/examPreview";
import { SortableBlockList } from "../exam-builder/SortableBlockList";
import { ExamPreview } from "../exam-preview/ExamPreview";
import { useUsage } from "../usage/UsageContext";

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
  const [preview, setPreview] = useState<ExamPreviewOut | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [mutationSaving, setMutationSaving] = useState(false);
  const examRequestId = useRef(0);
  const previewRequestId = useRef(0);

  const [newTypeId, setNewTypeId] = useState("");
  const [newCount, setNewCount] = useState(5);
  const [newPoints, setNewPoints] = useState(1);

  async function reload() {
    if (!examId) return;
    const requestId = ++examRequestId.current;
    try {
      const detail = await getExam(examId);
      if (requestId !== examRequestId.current) return;
      setExam(detail);
      setSelectedPoints(new Set(detail.grammar_point_ids));
    } catch (err) {
      if (requestId !== examRequestId.current) return;
      setError(err instanceof ApiError ? err.message : "Không tải được đề");
    }
  }

  async function loadPreview() {
    if (!examId) return;
    const requestId = ++previewRequestId.current;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const nextPreview = await getExamPreview(examId);
      if (requestId !== previewRequestId.current) return;
      setPreview(nextPreview);
    } catch (err) {
      if (requestId !== previewRequestId.current) return;
      setPreviewError(err instanceof ApiError ? err.message : "Không tải được bản xem trước");
    } finally {
      if (requestId === previewRequestId.current) setPreviewLoading(false);
    }
  }

  async function refreshBuilder() {
    await Promise.all([reload(), loadPreview()]);
  }

  useEffect(() => {
    void reload();
    void loadPreview();
    listExerciseTypes().then((types) => {
      setExerciseTypes(types);
      if (types.length > 0) setNewTypeId(types[0]!.id);
    });
    listGrammarTopics().then(setGrammarTopics);
    return () => {
      examRequestId.current += 1;
      previewRequestId.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  if (!exam) {
    return <p style={{ color: error ? "var(--danger)" : "var(--muted)" }}>{error ?? "Đang tải..."}</p>;
  }

  async function handleAddBlock() {
    if (!examId || !newTypeId || mutationSaving) return;
    const type = exerciseTypes.find((t) => t.id === newTypeId);
    setMutationSaving(true);
    try {
      await addBlock(examId, {
        exercise_type_id: newTypeId,
        title: type ? type.name : "Phần mới",
        question_count: newCount,
        points: newPoints,
      });
      setError(null);
      await refreshBuilder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thêm được phần");
    } finally {
      setMutationSaving(false);
    }
  }

  async function handleDeleteBlock(blockId: string) {
    if (!examId || mutationSaving) return;
    setMutationSaving(true);
    try {
      await deleteBlock(examId, blockId);
      setError(null);
      await refreshBuilder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không xóa được phần");
    } finally {
      setMutationSaving(false);
    }
  }

  async function handleReorder(blockIds: string[]) {
    if (!examId || !exam || mutationSaving) return;
    const snapshot = exam;
    const blocksById = new Map(exam.blocks.map((block) => [block.id, block]));
    const reorderedBlocks = blockIds.map((id, index) => ({ ...blocksById.get(id)!, order_no: index + 1 }));
    setExam({ ...exam, blocks: reorderedBlocks });
    setMutationSaving(true);
    setError(null);
    try {
      setExam(await reorderBlocks(examId, blockIds));
      await loadPreview();
    } catch (err) {
      setExam(snapshot);
      setError(err instanceof ApiError ? err.message : "Không lưu được thứ tự");
    } finally {
      setMutationSaving(false);
    }
  }

  async function handleBlockField(block: BlockOut, field: "question_count" | "points", value: number) {
    if (!examId || mutationSaving) return;
    setMutationSaving(true);
    try {
      await updateBlock(examId, block.id, { [field]: value });
      setError(null);
      await refreshBuilder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không cập nhật được phần");
    } finally {
      setMutationSaving(false);
    }
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
    if (!examId || mutationSaving) return;
    setMutationSaving(true);
    try {
      await setGrammarSelection(examId, Array.from(selectedPoints));
      setError(null);
      await refreshBuilder();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không lưu được lựa chọn ngữ pháp");
    } finally {
      setMutationSaving(false);
    }
  }

  async function handleGenerate() {
    if (!examId || mutationSaving) return;
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
    <div className="exam-builder-layout">
      <section className="exam-builder-editor" style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
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
                        disabled={mutationSaving}
                        onChange={() => togglePoint(point.id)}
                      />
                      {point.name} ({point.min_level.code})
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button onClick={handleSaveGrammarSelection} disabled={mutationSaving} style={secondaryButtonStyle}>
              Lưu lựa chọn
            </button>
          </div>
        )}

        <h3 style={{ fontSize: 15 }}>Các phần của đề</h3>
        <SortableBlockList
          blocks={orderedBlocks}
          saving={mutationSaving}
          onReorder={handleReorder}
          onDelete={handleDeleteBlock}
          onUpdateField={handleBlockField}
        />

        <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 14, flexWrap: "wrap" }}>
          <label style={{ display: "grid", gap: 4, fontSize: 12 }}>
            Dạng bài
            <select
              value={newTypeId}
              disabled={mutationSaving}
              onChange={(e) => setNewTypeId(e.target.value)}
              style={inputStyle}
            >
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
              disabled={mutationSaving}
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
              disabled={mutationSaving}
              onChange={(e) => setNewPoints(Number(e.target.value))}
              style={{ ...inputStyle, width: 70 }}
            />
          </label>
          <button onClick={handleAddBlock} disabled={mutationSaving} style={secondaryButtonStyle}>
            + Thêm phần
          </button>
        </div>

        <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
          <button
            onClick={handleGenerate}
            disabled={generating || mutationSaving || exam.blocks.length === 0}
            style={primaryButtonStyle}
          >
            {generating ? "Đang sinh đề..." : "✦ Sinh đề bằng AI"}
          </button>
        </div>
      </section>
      <aside className="exam-builder-preview">
        <ExamPreview preview={preview} loading={previewLoading} error={previewError} onRetry={loadPreview} />
      </aside>
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

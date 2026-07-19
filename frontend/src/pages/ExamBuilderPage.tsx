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

interface RouteToken {
  examId: string;
  generation: number;
}

interface MutationToken extends RouteToken {
  operationId: number;
  kind: "edit" | "generate";
}

interface RouteValue<T> {
  generation: number;
  value: T;
}

export function ExamBuilderPage() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const { refresh: refreshUsage } = useUsage();
  const routeRef = useRef<{ examId: string | undefined; generation: number }>({ examId, generation: 0 });
  if (routeRef.current.examId !== examId) {
    routeRef.current = { examId, generation: routeRef.current.generation + 1 };
  }
  const routeGeneration = routeRef.current.generation;

  const [examState, setExamState] = useState<RouteValue<ExamDetailOut> | null>(null);
  const [exerciseTypes, setExerciseTypes] = useState<ExerciseTypeOut[]>([]);
  const [grammarTopics, setGrammarTopics] = useState<GrammarTopicOut[]>([]);
  const [selectedPoints, setSelectedPoints] = useState<Set<string>>(new Set());
  const [error, setError] = useState<RouteValue<string> | null>(null);
  const [previewState, setPreviewState] = useState<RouteValue<ExamPreviewOut> | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<RouteValue<string> | null>(null);
  const [mutationLock, setMutationLock] = useState<MutationToken | null>(null);
  const examRequestId = useRef(0);
  const previewRequestId = useRef(0);
  const nextOperationId = useRef(0);
  const activeMutationRef = useRef<MutationToken | null>(null);

  const [newTypeId, setNewTypeId] = useState("");
  const [newCount, setNewCount] = useState(5);
  const [newPoints, setNewPoints] = useState(1);

  function isActiveRoute(target: RouteToken) {
    return routeRef.current.examId === target.examId && routeRef.current.generation === target.generation;
  }

  function isActiveOperation(target: MutationToken) {
    return (
      isActiveRoute(target) &&
      activeMutationRef.current?.generation === target.generation &&
      activeMutationRef.current.operationId === target.operationId
    );
  }

  function beginMutation(kind: MutationToken["kind"] = "edit"): MutationToken | null {
    const route = routeRef.current;
    if (!route.examId) return null;
    const active = activeMutationRef.current;
    if (active && active.examId === route.examId && active.generation === route.generation) return null;
    const target = { ...route, examId: route.examId, operationId: ++nextOperationId.current, kind };
    activeMutationRef.current = target;
    setMutationLock(target);
    setError(null);
    return target;
  }

  function finishMutation(target: MutationToken) {
    if (!isActiveOperation(target)) return;
    activeMutationRef.current = null;
    setMutationLock((current) => (current?.operationId === target.operationId ? null : current));
  }

  async function reload(target: RouteToken): Promise<boolean> {
    const requestId = ++examRequestId.current;
    try {
      const detail = await getExam(target.examId);
      if (!isActiveRoute(target) || requestId !== examRequestId.current || detail.id !== target.examId) return false;
      setExamState({ generation: target.generation, value: detail });
      setSelectedPoints(new Set(detail.grammar_point_ids));
      setError(null);
      return true;
    } catch (err) {
      if (!isActiveRoute(target) || requestId !== examRequestId.current) return false;
      setError({ generation: target.generation, value: err instanceof ApiError ? err.message : "Không tải được đề" });
      return false;
    }
  }

  async function loadPreview(target: RouteToken) {
    const requestId = ++previewRequestId.current;
    if (!isActiveRoute(target)) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const nextPreview = await getExamPreview(target.examId);
      if (
        !isActiveRoute(target) ||
        requestId !== previewRequestId.current ||
        nextPreview.exam_id !== target.examId
      )
        return;
      setPreviewState({ generation: target.generation, value: nextPreview });
      setPreviewError(null);
    } catch (err) {
      if (!isActiveRoute(target) || requestId !== previewRequestId.current) return;
      setPreviewError({
        generation: target.generation,
        value: err instanceof ApiError ? err.message : "Không tải được bản xem trước",
      });
    } finally {
      if (isActiveRoute(target) && requestId === previewRequestId.current) setPreviewLoading(false);
    }
  }

  async function refreshBuilder(target: RouteToken): Promise<boolean> {
    if (!isActiveRoute(target)) return false;
    const [examReloaded] = await Promise.all([reload(target), loadPreview(target)]);
    return examReloaded;
  }

  useEffect(() => {
    let route = routeRef.current;
    if (route.examId !== examId) {
      route = { examId, generation: route.generation + 1 };
      routeRef.current = route;
    }
    if (!route.examId) return;
    const target: RouteToken = { examId: route.examId, generation: route.generation };
    setExamState(null);
    setPreviewState(null);
    setError(null);
    setPreviewError(null);
    setPreviewLoading(true);
    setSelectedPoints(new Set());
    setMutationLock(null);
    void reload(target);
    void loadPreview(target);
    void listExerciseTypes().then((types) => {
      if (!isActiveRoute(target)) return;
      setExerciseTypes(types);
      if (types.length > 0) setNewTypeId(types[0]!.id);
    });
    void listGrammarTopics().then((topics) => {
      if (isActiveRoute(target)) setGrammarTopics(topics);
    });
    return () => {
      examRequestId.current += 1;
      previewRequestId.current += 1;
      if (isActiveRoute(target)) {
        routeRef.current = { examId: undefined, generation: target.generation + 1 };
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  const exam =
    examState?.generation === routeGeneration && examState.value.id === examId ? examState.value : null;
  const activeError = error?.generation === routeGeneration ? error.value : null;
  const preview =
    previewState?.generation === routeGeneration && previewState.value.exam_id === examId ? previewState.value : null;
  const activePreviewError = previewError?.generation === routeGeneration ? previewError.value : null;
  const mutationSaving = mutationLock?.generation === routeGeneration && mutationLock.examId === examId;
  const generating = mutationSaving && mutationLock?.kind === "generate";

  function retryPreview() {
    const route = routeRef.current;
    if (route.examId) void loadPreview({ examId: route.examId, generation: route.generation });
  }

  if (!exam) {
    return (
      <div className="exam-builder-layout">
        <section className="exam-builder-editor" style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
          <p style={{ margin: 0, color: activeError ? "var(--danger)" : "var(--muted)" }}>
            {activeError ?? "Đang tải..."}
          </p>
        </section>
        <aside className="exam-builder-preview">
          <ExamPreview preview={preview} loading={previewLoading} error={activePreviewError} onRetry={retryPreview} />
        </aside>
      </div>
    );
  }

  async function handleAddBlock() {
    if (!newTypeId || mutationSaving) return;
    const type = exerciseTypes.find((t) => t.id === newTypeId);
    const target = beginMutation();
    if (!target) return;
    try {
      await addBlock(target.examId, {
        exercise_type_id: newTypeId,
        title: type ? type.name : "Phần mới",
        question_count: newCount,
        points: newPoints,
      });
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không thêm được phần",
        });
      }
    } finally {
      finishMutation(target);
    }
  }

  async function handleDeleteBlock(blockId: string) {
    if (mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    try {
      await deleteBlock(target.examId, blockId);
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({ generation: target.generation, value: err instanceof ApiError ? err.message : "Không xóa được phần" });
      }
    } finally {
      finishMutation(target);
    }
  }

  async function handleReorder(blockIds: string[]) {
    if (!exam || mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    const snapshot = exam;
    const blocksById = new Map(exam.blocks.map((block) => [block.id, block]));
    const reorderedBlocks = blockIds.map((id, index) => ({ ...blocksById.get(id)!, order_no: index + 1 }));
    setExamState({ generation: target.generation, value: { ...exam, blocks: reorderedBlocks } });
    try {
      const reorderedExam = await reorderBlocks(target.examId, blockIds);
      if (!isActiveOperation(target)) return;
      if (reorderedExam.id === target.examId) {
        setExamState({ generation: target.generation, value: reorderedExam });
      }
      await loadPreview(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setExamState({ generation: target.generation, value: snapshot });
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không lưu được thứ tự",
        });
      }
    } finally {
      finishMutation(target);
    }
  }

  async function handleBlockField(block: BlockOut, field: "question_count" | "points", value: number) {
    if (mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    try {
      await updateBlock(target.examId, block.id, { [field]: value });
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không cập nhật được phần",
        });
      }
    } finally {
      finishMutation(target);
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
    if (mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    const grammarPointIds = Array.from(selectedPoints);
    try {
      await setGrammarSelection(target.examId, grammarPointIds);
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không lưu được lựa chọn ngữ pháp",
        });
      }
    } finally {
      finishMutation(target);
    }
  }

  async function handleGenerate() {
    if (mutationSaving) return;
    const target = beginMutation("generate");
    if (!target) return;
    try {
      await generateExam(target.examId);
      if (!isActiveOperation(target)) return;
      await refreshUsage();
      if (!isActiveOperation(target)) return;
      navigate(`/exams/${target.examId}/review`);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({ generation: target.generation, value: err instanceof ApiError ? err.message : "Không sinh được đề" });
      }
    } finally {
      finishMutation(target);
    }
  }

  const activeTopic = grammarTopics.find((t) => t.id === exam.grammar_topic_id);
  const orderedBlocks = [...exam.blocks].sort((a, b) => a.order_no - b.order_no);

  return (
    <div className="exam-builder-layout">
      <section className="exam-builder-editor" style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>{exam.title}</h2>
        {activeError && <p style={{ color: "var(--danger)" }}>{activeError}</p>}

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
        <ExamPreview
          preview={preview}
          loading={previewLoading}
          error={activePreviewError}
          onRetry={retryPreview}
        />
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

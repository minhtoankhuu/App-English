import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  addBlock,
  addBlockPart,
  deleteBlock,
  deleteBlockPart,
  generateExam,
  getExam,
  getExamPreview,
  reorderBlocks,
  setGrammarSelection,
  updateBlock,
  updateBlockPart,
  updateExam,
} from "../api/exams";
import { listExerciseTypes, listGrades, listGrammarTopics, listPassageLengthRules, listProficiencyLevels } from "../api/catalog";
import { ApiError } from "../api/client";
import type { BlockPartOut, ExamDetailOut, BlockOut, Difficulty } from "../types/exam";
import type { ExerciseTypeOut, GradeOut, GrammarTopicOut, PassageLengthRuleOut, ProficiencyLevelOut } from "../types/catalog";
import type { ExamPreviewOut } from "../types/examPreview";
import { SortableBlockList } from "../exam-builder/SortableBlockList";
import { ExamPreview } from "../exam-preview/ExamPreview";
import { StepsIndicator } from "../components/StepsIndicator";
import { Modal } from "../components/Modal";
import { PencilIcon } from "../icons/Icon";
import { useUsage } from "../usage/UsageContext";

// Tiêu đề mặc định cho phần đề (hiển thị trong đề xuất ra) theo đúng quy ước tiếng Anh
// của đề thi thật — nhãn tiếng Việt ở lưới chọn dạng bài chỉ dùng cho UI giáo viên.
// Giáo viên vẫn đổi được qua ô "Tiêu đề phần" trong popup chỉnh sửa.
const DEFAULT_BLOCK_TITLE_BY_CODE: Record<string, string> = {
  pronunciation: "PRONUNCIATION",
  stress: "STRESS",
  multiple_choice: "MULTIPLE CHOICE",
  matching: "MATCHING",
  gap_fill: "GAP FILL",
  cloze_test: "CLOZE TEST",
  reading_true_false: "READING COMPREHENSION",
  sign_reading: "PICTURE / SIGN READING",
  word_form: "WORD FORM",
  sentence_rewrite: "SENTENCE TRANSFORMATION",
};

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

  const [levels, setLevels] = useState<ProficiencyLevelOut[]>([]);
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [passageLengthRules, setPassageLengthRules] = useState<PassageLengthRuleOut[]>([]);

  const [editingBlock, setEditingBlock] = useState<BlockOut | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [editDifficulty, setEditDifficulty] = useState<Difficulty>("hon_hop");
  const [editCount, setEditCount] = useState<number | "">(1);
  const [editPoints, setEditPoints] = useState<number | "">(1);
  const [editPassageWordTarget, setEditPassageWordTarget] = useState<number | "">(100);
  const [editLevelOverrideId, setEditLevelOverrideId] = useState("");
  const [editShuffleQuestions, setEditShuffleQuestions] = useState(true);
  const [editShuffleAnswers, setEditShuffleAnswers] = useState(true);
  const [editPromptOverride, setEditPromptOverride] = useState("");

  const [editingExamTitle, setEditingExamTitle] = useState(false);
  const [examTitleDraft, setExamTitleDraft] = useState("");

  const [partTitle, setPartTitle] = useState("");
  const [partInstruction, setPartInstruction] = useState("");
  const [partCount, setPartCount] = useState<number | "">(5);
  const [partPromptOverride, setPartPromptOverride] = useState("");
  const [editingPartId, setEditingPartId] = useState<string | null>(null);

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
    });
    void listGrammarTopics().then((topics) => {
      if (isActiveRoute(target)) setGrammarTopics(topics);
    });
    void listProficiencyLevels().then((data) => {
      if (isActiveRoute(target)) setLevels(data);
    });
    void listGrades().then((data) => {
      if (isActiveRoute(target)) setGrades(data);
    });
    void listPassageLengthRules().then((data) => {
      if (isActiveRoute(target)) setPassageLengthRules(data);
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
      <>
        <StepsIndicator current={2} />
        <div className="builder-grid">
          <section className="configuration">
            <p style={{ margin: 0, color: activeError ? "var(--danger)" : "var(--muted)" }}>
              {activeError ?? "Đang tải..."}
            </p>
          </section>
          <ExamPreview preview={preview} loading={previewLoading} error={activePreviewError} onRetry={retryPreview} />
        </div>
      </>
    );
  }

  async function handleToggleType(type: ExerciseTypeOut, existingBlocks: BlockOut[]) {
    if (mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    try {
      if (existingBlocks.length > 0) {
        await Promise.all(existingBlocks.map((block) => deleteBlock(target.examId, block.id)));
      } else {
        await addBlock(target.examId, {
          exercise_type_id: type.id,
          title: DEFAULT_BLOCK_TITLE_BY_CODE[type.code] ?? type.name,
          question_count: 5,
          points: 1,
        });
      }
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không cập nhật được dạng bài",
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

  function openEditBlock(block: BlockOut) {
    const gradeNumber = exam ? grades.find((g) => g.id === exam.grade_id)?.number : undefined;
    const range = passageRangeFor(gradeNumber);
    setEditingBlock(block);
    setEditTitle(block.title);
    setEditInstruction(block.instruction ?? "");
    setEditDifficulty(block.difficulty);
    setEditCount(block.question_count);
    setEditPoints(Number(block.points));
    setEditPassageWordTarget(block.passage_word_target ?? (range ? Math.round((range[0] + range[1]) / 2 / 10) * 10 : 100));
    setEditLevelOverrideId(block.level_override?.id ?? "");
    setEditShuffleQuestions(block.shuffle_questions);
    setEditShuffleAnswers(block.shuffle_answers);
    setEditPromptOverride(block.prompt_override ?? "");
    resetPartForm();
  }

  function resetPartForm() {
    setEditingPartId(null);
    setPartTitle("");
    setPartInstruction("");
    setPartCount(5);
    setPartPromptOverride("");
  }

  function openEditPart(part: BlockPartOut) {
    setEditingPartId(part.id);
    setPartTitle(part.title);
    setPartInstruction(part.instruction ?? "");
    setPartCount(part.question_count);
    setPartPromptOverride(part.prompt_override ?? "");
  }

  async function handleSavePart() {
    if (!editingBlock || mutationSaving || !partTitle.trim() || partCount === "") return;
    const target = beginMutation();
    if (!target) return;
    const payload = {
      title: partTitle.trim(),
      instruction: partInstruction.trim() || null,
      question_count: partCount,
      prompt_override: partPromptOverride.trim() || null,
    };
    try {
      const updatedBlock = editingPartId
        ? await updateBlockPart(target.examId, editingBlock.id, editingPartId, payload)
        : await addBlockPart(target.examId, editingBlock.id, payload);
      if (!isActiveOperation(target)) return;
      setEditingBlock(updatedBlock);
      setEditCount(updatedBlock.question_count);
      resetPartForm();
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không lưu được phần con",
        });
      }
    } finally {
      finishMutation(target);
    }
  }

  async function handleDeletePart(partId: string) {
    if (!editingBlock || mutationSaving) return;
    const target = beginMutation();
    if (!target) return;
    try {
      const updatedBlock = await deleteBlockPart(target.examId, editingBlock.id, partId);
      if (!isActiveOperation(target)) return;
      setEditingBlock(updatedBlock);
      setEditCount(updatedBlock.question_count);
      if (editingPartId === partId) resetPartForm();
      await refreshBuilder(target);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không xóa được phần con",
        });
      }
    } finally {
      finishMutation(target);
    }
  }

  function passageRangeFor(gradeNumber: number | undefined): [number, number] | null {
    if (!gradeNumber) return null;
    const rule = passageLengthRules.find((r) => gradeNumber >= r.grade_min && gradeNumber <= r.grade_max);
    return rule ? [rule.min_words, rule.max_words] : null;
  }

  const editFieldsValid =
    editCount !== "" && editPoints !== "" && (!editingBlock?.exercise_type.has_passage || editPassageWordTarget !== "");

  async function handleSaveBlockEdit() {
    if (!editingBlock || mutationSaving || !editTitle.trim()) return;
    if (editCount === "" || editPoints === "") return;
    if (editingBlock.exercise_type.has_passage && editPassageWordTarget === "") return;
    const target = beginMutation();
    if (!target) return;
    try {
      await updateBlock(target.examId, editingBlock.id, {
        title: editTitle.trim(),
        instruction: editInstruction.trim() || null,
        difficulty: editDifficulty,
        question_count: editCount,
        points: editPoints,
        level_override_id: editLevelOverrideId || null,
        shuffle_questions: editShuffleQuestions,
        shuffle_answers: editShuffleAnswers,
        prompt_override: editPromptOverride.trim() || null,
        passage_word_target:
          editingBlock.exercise_type.has_passage && editPassageWordTarget !== "" ? editPassageWordTarget : null,
      });
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
      setEditingBlock(null);
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

  function startEditExamTitle() {
    if (!exam) return;
    setExamTitleDraft(exam.title);
    setEditingExamTitle(true);
  }

  async function handleSaveExamTitle() {
    if (mutationSaving || !examTitleDraft.trim()) return;
    const target = beginMutation();
    if (!target) return;
    try {
      await updateExam(target.examId, { title: examTitleDraft.trim() });
      if (!isActiveOperation(target)) return;
      await refreshBuilder(target);
      setEditingExamTitle(false);
    } catch (err) {
      if (isActiveOperation(target)) {
        setError({
          generation: target.generation,
          value: err instanceof ApiError ? err.message : "Không cập nhật được tiêu đề đề",
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
    <>
      <StepsIndicator current={2} />
      <div className="builder-grid">
        <section className="configuration">
          {editingExamTitle ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
              <input
                type="text"
                aria-label="Tiêu đề đề thi"
                value={examTitleDraft}
                onChange={(e) => setExamTitleDraft(e.target.value)}
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="button primary compact"
                onClick={handleSaveExamTitle}
                disabled={mutationSaving || !examTitleDraft.trim()}
              >
                Lưu
              </button>
              <button type="button" className="button secondary compact" onClick={() => setEditingExamTitle(false)}>
                Hủy
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>{exam.title}</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="Chỉnh sửa tiêu đề đề thi"
                onClick={startEditExamTitle}
                disabled={mutationSaving}
              >
                <PencilIcon />
              </button>
            </div>
          )}
          {activeError && <p style={{ color: "var(--danger)" }}>{activeError}</p>}

          {activeTopic && (
            <div style={{ marginBottom: 16 }}>
              <div className="section-heading block-heading">
                <div>
                  <h3>Chọn {activeTopic.name.split(" — ")[0]}</h3>
                </div>
              </div>
              {activeTopic.groups.map((group) => (
                <div key={group.id} style={{ marginTop: 12 }}>
                  <p style={{ margin: "0 0 4px", fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>
                    {group.name}
                  </p>
                  <div className="type-grid">
                    {group.points.map((point) => (
                      <label key={point.id} className="type-option">
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
              <button
                type="button"
                onClick={handleSaveGrammarSelection}
                disabled={mutationSaving}
                className="button secondary compact"
                style={{ marginTop: 12 }}
              >
                Lưu lựa chọn
              </button>
            </div>
          )}

          <div className="section-heading block-heading">
            <div>
              <h2>Dạng bài tập</h2>
              <p>Tick để thêm block dạng đó (5 câu/1 điểm mặc định); bỏ tick sẽ xóa block tương ứng.</p>
            </div>
          </div>
          <div className="type-grid">
            {exerciseTypes.map((type) => {
              const blocksOfType = exam.blocks.filter((block) => block.exercise_type.id === type.id);
              return (
                <label key={type.id} className="type-option">
                  <input
                    type="checkbox"
                    checked={blocksOfType.length > 0}
                    disabled={mutationSaving}
                    onChange={() => handleToggleType(type, blocksOfType)}
                  />
                  {type.name}
                </label>
              );
            })}
          </div>

          <div className="section-heading block-heading">
            <div>
              <h2>Các phần của đề</h2>
              <p>Kéo thả, sửa số câu/điểm hoặc xóa riêng từng khối.</p>
            </div>
          </div>
          <SortableBlockList
            blocks={orderedBlocks}
            saving={mutationSaving}
            onReorder={handleReorder}
            onDelete={handleDeleteBlock}
            onEdit={openEditBlock}
          />

          <div className="config-footer">
            <button
              type="button"
              onClick={() => navigate("/exams")}
              disabled={mutationSaving}
              className="button secondary"
            >
              Lưu vào nháp
            </button>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={generating || mutationSaving || exam.blocks.length === 0}
              className="button primary large"
            >
              {generating ? "Đang sinh đề..." : "✦ Sinh đề bằng AI"}
            </button>
          </div>
        </section>
        <ExamPreview preview={preview} loading={previewLoading} error={activePreviewError} onRetry={retryPreview} />
      </div>

      <Modal open={editingBlock !== null} onClose={() => setEditingBlock(null)} title="Chỉnh sửa phần" size="lg">
        {editingBlock && (
          <div className="app-modal-body">
            <p style={{ margin: 0 }}>
              <span className="chip">{editingBlock.exercise_type.name}</span>
              <span style={{ marginLeft: 8, color: "var(--muted)", fontSize: 12.5 }}>
                — dạng bài chọn ở checklist bên ngoài. Câu đã khóa không bị sinh lại.
              </span>
            </p>

            <label>
              Tiêu đề phần
              <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required />
            </label>

            <label>
              Hướng dẫn làm bài
              <input
                type="text"
                placeholder="Ví dụ: Choose the best answer A, B, C or D."
                value={editInstruction}
                onChange={(e) => setEditInstruction(e.target.value)}
              />
            </label>

            <div className="editor-grid">
              <label>
                Độ khó
                <select value={editDifficulty} onChange={(e) => setEditDifficulty(e.target.value as Difficulty)}>
                  <option value="nhan_biet">Nhận biết</option>
                  <option value="thong_hieu">Thông hiểu</option>
                  <option value="van_dung">Vận dụng</option>
                  <option value="hon_hop">Hỗn hợp</option>
                </select>
              </label>
              <label>
                Số câu
                {editingBlock.parts.length > 0 ? (
                  <input type="number" value={editCount} disabled title="Tự động tính theo phần con bên dưới" />
                ) : (
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={editCount}
                    onChange={(e) => setEditCount(e.target.value === "" ? "" : Number(e.target.value))}
                  />
                )}
              </label>
              <label>
                Điểm
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.5}
                  value={editPoints}
                  onChange={(e) => setEditPoints(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </label>
            </div>

            <div>
              <div className="section-heading block-heading">
                <div>
                  <h3>Phần con</h3>
                  <p>Chia thành các phần đánh số 1., 2., 3. khi dạng bài cần nhiều chủ đề/mẫu câu riêng (ví dụ so sánh kép, cụm động từ).</p>
                </div>
              </div>
              {editingBlock.parts.length > 0 && (
                <ul style={{ listStyle: "none", margin: "0 0 12px", padding: 0, display: "grid", gap: 8 }}>
                  {[...editingBlock.parts]
                    .sort((a, b) => a.order_no - b.order_no)
                    .map((part) => (
                      <li
                        key={part.id}
                        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}
                      >
                        <span>
                          {part.order_no}. {part.title} <span style={{ color: "var(--muted)" }}>({part.question_count} câu)</span>
                        </span>
                        <span style={{ display: "flex", gap: 6 }}>
                          <button type="button" className="button secondary compact" onClick={() => openEditPart(part)}>
                            Sửa
                          </button>
                          <button
                            type="button"
                            className="button secondary compact"
                            onClick={() => handleDeletePart(part.id)}
                            disabled={mutationSaving}
                          >
                            Xóa
                          </button>
                        </span>
                      </li>
                    ))}
                </ul>
              )}

              <div style={{ display: "grid", gap: 8, padding: 12, borderRadius: 8, background: "var(--surface)" }}>
                <label>
                  Tiêu đề phần con
                  <input
                    type="text"
                    placeholder="Ví dụ: So sánh kép"
                    value={partTitle}
                    onChange={(e) => setPartTitle(e.target.value)}
                  />
                </label>
                <label>
                  Hướng dẫn riêng (tuỳ chọn)
                  <input
                    type="text"
                    value={partInstruction}
                    onChange={(e) => setPartInstruction(e.target.value)}
                  />
                </label>
                <div className="editor-grid">
                  <label>
                    Số câu của phần con
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={partCount}
                      onChange={(e) => setPartCount(e.target.value === "" ? "" : Number(e.target.value))}
                    />
                  </label>
                </div>
                <label>
                  Prompt bổ sung cho phần con (tuỳ chọn)
                  <textarea
                    rows={2}
                    value={partPromptOverride}
                    onChange={(e) => setPartPromptOverride(e.target.value)}
                  />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={handleSavePart}
                    disabled={mutationSaving || !partTitle.trim() || partCount === ""}
                  >
                    {editingPartId ? "Lưu phần con" : "+ Thêm phần con"}
                  </button>
                  {editingPartId && (
                    <button type="button" className="button secondary compact" onClick={resetPartForm}>
                      Hủy sửa
                    </button>
                  )}
                </div>
              </div>
            </div>

            {editingBlock.exercise_type.has_passage &&
              (() => {
                const gradeNumber = grades.find((g) => g.id === exam.grade_id)?.number;
                const range = passageRangeFor(gradeNumber);
                return (
                  <div>
                    <label>
                      Số từ bài đọc (≈)
                      <input
                        type="number"
                        min={10}
                        max={500}
                        step={10}
                        value={editPassageWordTarget}
                        onChange={(e) => setEditPassageWordTarget(e.target.value === "" ? "" : Number(e.target.value))}
                      />
                    </label>
                    {range && (
                      <small className="field-hint">
                        Gợi ý {range[0]}–{range[1]} từ cho Lớp {gradeNumber} — theo bảng độ dài bài đọc.
                      </small>
                    )}
                  </div>
                );
              })()}

            <div>
              <label>
                Trình độ của phần này
                <select value={editLevelOverrideId} onChange={(e) => setEditLevelOverrideId(e.target.value)}>
                  <option value="">Theo trình độ của đề</option>
                  {levels.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.code}
                    </option>
                  ))}
                </select>
              </label>
              <small className="field-hint">Chỉ ghi đè khi phần này cần khác với trình độ chung.</small>
            </div>

            <div className="editor-checks">
              <label className="type-option">
                <input
                  type="checkbox"
                  checked={editShuffleQuestions}
                  onChange={(e) => setEditShuffleQuestions(e.target.checked)}
                />
                Cho phép đảo thứ tự câu
              </label>
              <label className="type-option">
                <input
                  type="checkbox"
                  checked={editShuffleAnswers}
                  onChange={(e) => setEditShuffleAnswers(e.target.checked)}
                />
                Cho phép đảo đáp án
              </label>
            </div>

            <label>
              Prompt bổ sung cho phần này
              <textarea
                rows={2}
                placeholder="Ví dụ: Ưu tiên từ vựng về hoạt động tình nguyện trong Unit 3."
                value={editPromptOverride}
                onChange={(e) => setEditPromptOverride(e.target.value)}
              />
            </label>
          </div>
        )}
        <div className="app-modal-footer">
          <button type="button" className="button secondary" onClick={() => setEditingBlock(null)}>
            Hủy
          </button>
          <button
            type="button"
            className="button primary"
            onClick={handleSaveBlockEdit}
            disabled={mutationSaving || !editTitle.trim() || !editFieldsValid}
          >
            Lưu
          </button>
        </div>
      </Modal>
    </>
  );
}

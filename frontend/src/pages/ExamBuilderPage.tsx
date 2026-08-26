import { Fragment, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  addBlock,
  addBlockPart,
  deleteBlock,
  generateExam,
  getExam,
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
import { SortableBlockList } from "../exam-builder/SortableBlockList";
import { StepsIndicator } from "../components/StepsIndicator";
import { Modal } from "../components/Modal";
import { PencilIcon } from "../icons/Icon";
import { useUsage } from "../usage/UsageContext";

// Tiêu đề mặc định cho phần đề (hiển thị trong đề xuất ra) theo đúng quy ước tiếng Anh
// của đề thi thật — nhãn tiếng Việt ở lưới chọn dạng bài chỉ dùng cho UI giáo viên.
// Giáo viên vẫn đổi được qua ô "Tiêu đề phần" trong popup chỉnh sửa.
// 3 kiểu Pronunciation không trộn được trong cùng 1 lần sinh (xem
// app/services/prompts.py) — tick "Pronunciation" tạo 1 block chung "PRONUNCIATION"
// (đánh số I/II/III như dạng bài khác) kèm sẵn 3 Phần con đánh số 1/2/3 bên trong,
// mỗi phần ghim đúng 1 kiểu qua prompt_override, thay vì bắt giáo viên tự thêm.
const PRONUNCIATION_PART_PRESETS: { title: string; promptOverride: string }[] = [
  { title: "Đuôi -s/-es", promptOverride: "Chỉ dùng kiểu (1) đuôi -s/-es cho toàn bộ các câu." },
  { title: "Đuôi -ed", promptOverride: "Chỉ dùng kiểu (2) đuôi -ed cho toàn bộ các câu." },
  {
    title: "Âm trong từ",
    promptOverride:
      "Chỉ dùng kiểu (3) so sánh âm chung trong từ (không phải đuôi -s/-es hay -ed) cho toàn bộ các câu.",
  },
];

// WORD FORMATION theo format đề thật gồm 2 phần không trộn được trong 1 lần sinh
// (xem prompts.py): Phần A gom câu theo họ từ (dòng "❖ adore (v) → adorable (adj) → ..."),
// Phần B đặt từ gốc trong ngoặc canh sát lề phải. Tiêu đề Phần con chính là câu lệnh
// in ra đề (docx_renderer không đánh số "1./2." cho phần con của word form).
// Mỗi họ từ ở Phần A làm 5 câu (khớp WORD_FORM_QUESTIONS_PER_FAMILY ở generation.py):
// giáo viên chọn SỐ HỌC TỪ, còn `question_count` lưu theo số CÂU để không lệch với
// tổng số câu của block (xem _sync_block_question_count ở routers/exams.py).
const WORD_FORM_QUESTIONS_PER_FAMILY = 5;
const WORD_FORM_MIN_PER_FAMILY = 3;
const WORD_FORM_MAX_PER_FAMILY = 10;
// Số câu mỗi họ từ đi kèm prompt_override của Phần con (nơi đã ghim sẵn "kiểu (A)")
// thay vì thêm cột DB — backend đọc lại bằng word_form_questions_per_family().
const PER_FAMILY_RE = /mỗi họ từ\s+(\d+)\s*câu/i;

function readPerFamily(promptOverride: string | null): number {
  const match = PER_FAMILY_RE.exec(promptOverride ?? "");
  if (!match) return WORD_FORM_QUESTIONS_PER_FAMILY;
  const value = Number(match[1]);
  return Math.max(WORD_FORM_MIN_PER_FAMILY, Math.min(WORD_FORM_MAX_PER_FAMILY, value));
}

function writePerFamily(promptOverride: string | null, perFamily: number): string {
  const base = (promptOverride ?? "").replace(PER_FAMILY_RE, "").replace(/\s+/g, " ").trim();
  return `${base} Mỗi họ từ ${perFamily} câu.`.trim();
}

const WORD_FORM_PART_PRESETS: { title: string; promptOverride: string }[] = [
  {
    title: "Part A. Fill in the blanks with the correct form of the words",
    promptOverride: "Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.",
  },
  {
    title: "Part B. Fill in the blanks with the correct form of the word in brackets.",
    promptOverride: "Chỉ dùng kiểu (B) từ gốc trong ngoặc ở cuối câu cho toàn bộ các câu.",
  },
];

const DEFAULT_BLOCK_TITLE_BY_CODE: Record<string, string> = {
  pronunciation: "PRONUNCIATION",
  stress: "STRESS",
  multiple_choice: "VOCABULARY AND GRAMMAR",
  matching: "MATCHING",
  gap_fill: "GAP FILL",
  cloze_test: "CLOZE TEST",
  reading_true_false: "READING COMPREHENSION",
  sign_reading: "PICTURE / SIGN READING",
  word_form: "WORD FORMATION",
  sentence_rewrite: "SENTENCE TRANSFORMATION",
};

// Mỗi phần con quy đổi bao nhiêu câu trên một "từ": Phần A word form là 1 họ từ = 5 câu,
// còn lại 1 đơn vị = 1 câu. Nhận diện qua prompt_override — cùng dấu hiệu mà
// detect_word_form_kind ở backend dùng.
function isWordFormFamilyPart(block: BlockOut, part: BlockPartOut): boolean {
  return block.exercise_type.code === "word_form" && /\(a\)|họ từ/i.test(part.prompt_override ?? "");
}

function partCountLabel(block: BlockOut, part: BlockPartOut): string {
  if (block.exercise_type.code !== "word_form") return `${part.order_no}. ${part.title}`;
  return isWordFormFamilyPart(block, part) ? "Phần A — Số họ từ" : "Phần B — Số từ";
}

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
  const [mutationLock, setMutationLock] = useState<MutationToken | null>(null);
  const examRequestId = useRef(0);
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

  // Số câu đang soạn cho từng phần con, khoa theo part.id. Phần con không còn thêm/xóa
  // được từ giao diện — mỗi dạng bài đã có sẵn các phần theo format đề thật, giáo viên
  // chỉ chỉnh số lượng ngay trong form chính (chốt 24/08/2026).
  const [partCounts, setPartCounts] = useState<Record<string, number | "">>({});
  const [partPerFamily, setPartPerFamily] = useState<Record<string, number | "">>({});

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


  async function refreshBuilder(target: RouteToken): Promise<boolean> {
    if (!isActiveRoute(target)) return false;
    return reload(target);
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
    setError(null);
    setSelectedPoints(new Set());
    setMutationLock(null);
    void reload(target);
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
      if (isActiveRoute(target)) {
        routeRef.current = { examId: undefined, generation: target.generation + 1 };
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  const exam =
    examState?.generation === routeGeneration && examState.value.id === examId ? examState.value : null;
  const activeError = error?.generation === routeGeneration ? error.value : null;
  const mutationSaving = mutationLock?.generation === routeGeneration && mutationLock.examId === examId;
  const generating = mutationSaving && mutationLock?.kind === "generate";


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
      } else if (type.code === "word_form") {
        // Giống Pronunciation: tạo sẵn 2 Phần con, mỗi phần ghim 1 kiểu qua prompt_override.
        const created = await addBlock(target.examId, {
          exercise_type_id: type.id,
          title: DEFAULT_BLOCK_TITLE_BY_CODE[type.code] ?? type.name,
          question_count: 3 * WORD_FORM_QUESTIONS_PER_FAMILY,
          points: 2,
        });
        for (const preset of WORD_FORM_PART_PRESETS) {
          await addBlockPart(target.examId, created.id, {
            title: preset.title,
            question_count: 3 * WORD_FORM_QUESTIONS_PER_FAMILY,
            prompt_override: preset.promptOverride,
          });
        }
      } else if (type.code === "pronunciation") {
        // Phát âm có 3 kiểu không trộn được trong 1 lần sinh (xem prompts.py) — tạo 1
        // block chung "PRONUNCIATION" kèm sẵn 3 Phần con (5 câu/phần, tự đánh số
        // 1/2/3), mỗi phần ghim đúng 1 kiểu qua prompt_override — question_count của
        // block tự đồng bộ theo tổng các phần con sau khi thêm.
        const created = await addBlock(target.examId, {
          exercise_type_id: type.id,
          title: DEFAULT_BLOCK_TITLE_BY_CODE[type.code] ?? type.name,
          question_count: 5,
          points: 3,
        });
        for (const preset of PRONUNCIATION_PART_PRESETS) {
          await addBlockPart(target.examId, created.id, {
            title: preset.title,
            question_count: 5,
            prompt_override: preset.promptOverride,
          });
        }
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
    setPartCounts(Object.fromEntries(block.parts.map((part) => [part.id, part.question_count])));
    setPartPerFamily(Object.fromEntries(block.parts.map((part) => [part.id, readPerFamily(part.prompt_override)])));
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
      // Phần con không còn nút lưu riêng — số câu của từng phần lưu chung với khối.
      for (const part of editingBlock.parts) {
        const value = partCounts[part.id];
        const isFamily = isWordFormFamilyPart(editingBlock, part);
        const stored = partPerFamily[part.id];
        const perFamily = stored === "" || stored === undefined ? readPerFamily(part.prompt_override) : stored;
        const promptOverride = isFamily
          ? writePerFamily(part.prompt_override, perFamily)
          : part.prompt_override;
        const count = value === "" || value === undefined ? part.question_count : value;
        if (count === part.question_count && promptOverride === part.prompt_override) continue;
        await updateBlockPart(target.examId, editingBlock.id, part.id, {
          title: part.title,
          instruction: part.instruction,
          question_count: count,
          prompt_override: promptOverride,
        });
      }
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
  const sortedParts = editingBlock ? [...editingBlock.parts].sort((a, b) => a.order_no - b.order_no) : [];
  // "Số câu" của khối = tổng các phần con, tính lại ngay khi gõ chứ không đợi bấm Lưu
  // (số không nhúch thì giáo viên tưởng hỏng — báo cáo 24/08/2026).
  const pendingPartCount = sortedParts.length
    ? sortedParts.reduce((total, part) => {
        const value = partCounts[part.id];
        return total + (value === "" || value === undefined ? part.question_count : value);
      }, 0)
    : null;

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
                {editingBlock.parts.length > 0 || pendingPartCount !== null ? (
                  <>
                    {/* aria-label cố định: dòng chú thích bên dưới nằm trong <label> nên tên
                        nhãn suy từ text sẽ đổi theo trạng thái. */}
                    <input
                      type="number"
                      aria-label="Số câu"
                      value={pendingPartCount ?? editCount}
                      disabled
                      title="Tự động tính theo phần con bên dưới"
                    />
                    {pendingPartCount !== null && pendingPartCount !== editCount && (
                      <span style={{ color: "var(--muted)", fontSize: 12 }}>
                        Sau khi lưu phần con (đang là {editCount})
                      </span>
                    )}
                  </>
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

            {editingBlock.parts.length > 0 && (
              <div>
                <div className="section-heading block-heading">
                  <div>
                    <h3>Số lượng từng phần</h3>
                    <p>
                      Dạng bài này chia sẵn theo format đề thật — chỉ cần chỉnh số lượng, không
                      phải thêm/xóa phần nào.
                    </p>
                  </div>
                </div>
                <div className="editor-grid">
                  {sortedParts.map((part) => {
                    const isFamily = isWordFormFamilyPart(editingBlock, part);
                    // Để trống được khi đang gõ (nếu chặn rỗng thì xóa không được, gõ "7" vào "5"
                    // thành 57); lúc tính toán thì quay về giá trị đã lưu.
                    const perFamilyRaw = isFamily
                      ? (partPerFamily[part.id] ?? readPerFamily(part.prompt_override))
                      : 1;
                    // Ô đang rỗng thì quay về giá trị đã lưu, KHÔNG về 1 — về 1 sẽ làm ô "Số họ từ"
                    // nhảy từ 3 lên 15 ngay giữa lúc gõ.
                    const perWord = !isFamily
                      ? 1
                      : perFamilyRaw === ""
                        ? readPerFamily(part.prompt_override)
                        : perFamilyRaw;
                    const raw = partCounts[part.id] ?? part.question_count;
                    return (
                      <Fragment key={part.id}>
                        <label>
                          {partCountLabel(editingBlock, part)}
                          <input
                            type="number"
                            min={1}
                            max={20}
                            value={raw === "" ? "" : Math.max(1, Math.round(raw / perWord))}
                            onChange={(e) =>
                              setPartCounts((prev) => ({
                                ...prev,
                                [part.id]: e.target.value === "" ? "" : Number(e.target.value) * perWord,
                              }))
                            }
                          />
                          <span style={{ color: "var(--muted)", fontSize: 12 }}>
                            {isFamily
                              ? `Mỗi họ từ ${perWord} câu — ${raw === "" ? 0 : raw} câu`
                              : `${raw === "" ? 0 : raw} câu`}
                          </span>
                        </label>
                        {isFamily && (
                          <label>
                            Số câu mỗi họ từ
                            <input
                              type="number"
                              min={WORD_FORM_MIN_PER_FAMILY}
                              max={WORD_FORM_MAX_PER_FAMILY}
                              value={perFamilyRaw}
                              onChange={(e) => {
                                if (e.target.value === "") {
                                  setPartPerFamily((prev) => ({ ...prev, [part.id]: "" }));
                                  return;
                                }
                                const next = Number(e.target.value);
                                if (!next) return;
                                const families = raw === "" ? 1 : Math.max(1, Math.round(raw / perWord));
                                setPartPerFamily((prev) => ({ ...prev, [part.id]: next }));
                                setPartCounts((prev) => ({ ...prev, [part.id]: families * next }));
                              }}
                            />
                            <span style={{ color: "var(--muted)", fontSize: 12 }}>
                              Câu trong một họ từ được đảo ngẫu nhiên khi xuất đề
                            </span>
                          </label>
                        )}
                      </Fragment>
                    );
                  })}
                </div>
              </div>
            )}

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

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { completeReview, getExam, regenerateQuestion, updateQuestionFlags } from "../api/exams";
import { ApiError } from "../api/client";
import type { ExamDetailOut, QuestionOut } from "../types/exam";
import { useUsage } from "../usage/UsageContext";
import { useRouteGeneration, type RouteGenerationToken } from "../routing/useRouteGeneration";
import { StepsIndicator } from "../components/StepsIndicator";

interface ReviewOperation {
  id: number;
  route: RouteGenerationToken;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

const UNDERLINE_MARKUP_RE = /<u>(.*?)<\/u>/g;

/** LLM đánh dấu phần gạch chân (dạng phát âm/trọng âm) bằng <u>...</u> trong option
 * text (xem app/services/prompts.py + docx_renderer.py — cùng 1 quy ước render). */
function UnderlineText({ text }: { text: string }) {
  const parts: (string | { underlined: string })[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(UNDERLINE_MARKUP_RE)) {
    if (match.index! > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push({ underlined: match[1]! });
    lastIndex = match.index! + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));

  return (
    <>
      {parts.map((part, i) =>
        typeof part === "string" ? <span key={i}>{part}</span> : <u key={i}>{part.underlined}</u>,
      )}
    </>
  );
}

export function ExamReviewPage() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const { refresh: refreshUsage } = useUsage();
  const routeGeneration = useRouteGeneration(examId);
  const [exam, setExam] = useState<ExamDetailOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyQuestionId, setBusyQuestionId] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [activeOperationId, setActiveOperationId] = useState<number | null>(null);
  const activeOperation = useRef<ReviewOperation | null>(null);
  const nextOperationId = useRef(0);

  const reload = useCallback(async (targetExamId: string, token: RouteGenerationToken): Promise<boolean> => {
    try {
      const detail = await getExam(targetExamId);
      if (!routeGeneration.isCurrent(token) || detail.id !== targetExamId) return false;
      setExam(detail);
      setError(null);
      return true;
    } catch (err) {
      if (!routeGeneration.isCurrent(token)) return false;
      setError(errorMessage(err, "Không tải được đề"));
      return false;
    }
  }, [routeGeneration]);

  function beginOperation(): ReviewOperation | null {
    if (!examId || activeOperation.current) return null;
    const operation = { id: ++nextOperationId.current, route: routeGeneration.capture() };
    activeOperation.current = operation;
    setActiveOperationId(operation.id);
    setError(null);
    return operation;
  }

  function isCurrentOperation(operation: ReviewOperation) {
    return routeGeneration.isCurrent(operation.route) && activeOperation.current?.id === operation.id;
  }

  function finishOperation(operation: ReviewOperation) {
    if (!isCurrentOperation(operation)) return;
    activeOperation.current = null;
    setActiveOperationId(null);
    setBusyQuestionId(null);
    setFinishing(false);
  }

  useEffect(() => {
    setExam(null);
    setError(null);
    setBusyQuestionId(null);
    setFinishing(false);
    setActiveOperationId(null);
    activeOperation.current = null;
    if (!examId) return;
    const token = routeGeneration.capture();
    void reload(examId, token);
  }, [examId, reload, routeGeneration]);

  if (!exam || exam.id !== examId) {
    return <p style={{ color: error ? "var(--danger)" : "var(--muted)" }}>{error ?? "Đang tải..."}</p>;
  }

  const allQuestions = exam.blocks.flatMap((b) => b.questions);
  const approvedCount = allQuestions.filter((q) => q.is_approved).length;

  async function handleApproveToggle(question: QuestionOut) {
    if (!examId) return;
    const operation = beginOperation();
    if (!operation) return;
    const targetExamId = examId;
    setBusyQuestionId(question.id);
    try {
      await updateQuestionFlags(targetExamId, question.id, { is_approved: !question.is_approved });
      if (!isCurrentOperation(operation)) return;
      await reload(targetExamId, operation.route);
    } catch (err) {
      if (isCurrentOperation(operation)) setError(errorMessage(err, "Không cập nhật được câu hỏi"));
    } finally {
      finishOperation(operation);
    }
  }

  async function handleLockToggle(question: QuestionOut) {
    if (!examId) return;
    const operation = beginOperation();
    if (!operation) return;
    const targetExamId = examId;
    setBusyQuestionId(question.id);
    try {
      await updateQuestionFlags(targetExamId, question.id, { is_locked: !question.is_locked });
      if (!isCurrentOperation(operation)) return;
      await reload(targetExamId, operation.route);
    } catch (err) {
      if (isCurrentOperation(operation)) setError(errorMessage(err, "Không cập nhật được câu hỏi"));
    } finally {
      finishOperation(operation);
    }
  }

  async function handleRegenerate(question: QuestionOut) {
    if (!examId) return;
    const operation = beginOperation();
    if (!operation) return;
    const targetExamId = examId;
    setBusyQuestionId(question.id);
    try {
      await regenerateQuestion(targetExamId, question.id);
      if (!isCurrentOperation(operation)) return;
      await refreshUsage();
      if (!isCurrentOperation(operation)) return;
      await reload(targetExamId, operation.route);
    } catch (err) {
      if (isCurrentOperation(operation)) setError(errorMessage(err, "Không sinh lại được câu này"));
    } finally {
      finishOperation(operation);
    }
  }

  async function handleFinish() {
    if (!examId) return;
    const operation = beginOperation();
    if (!operation) return;
    const targetExamId = examId;
    setFinishing(true);
    try {
      await completeReview(targetExamId);
      if (!isCurrentOperation(operation)) return;
      navigate(`/exams/${targetExamId}/export`);
    } catch (err) {
      if (isCurrentOperation(operation)) setError(errorMessage(err, "Chưa thể hoàn tất kiểm duyệt"));
    } finally {
      finishOperation(operation);
    }
  }

  const mutationBusy = activeOperationId !== null;

  return (
    <>
      <StepsIndicator current={3} />
      <div style={{ display: "grid", gap: 14 }}>
        <div className="review-head">
          <Link to={`/exams/${examId}/builder`} className="button secondary compact">
            ← Sửa cấu trúc
          </Link>
          <p className="review-progress">
            <strong>{approvedCount}</strong>/{allQuestions.length} câu đã duyệt
          </p>
        </div>

        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        {exam.blocks
          .slice()
          .sort((a, b) => a.order_no - b.order_no)
          .map((block) => (
            <section key={block.id} className="review-block">
              <h3 className="review-block-title">
                {block.title} · {block.questions.length} câu
              </h3>
              <div style={{ display: "grid", gap: 10 }}>
                {block.questions
                  .slice()
                  .sort((a, b) => a.order_no - b.order_no)
                  .map((q) => (
                    <article
                      key={q.id}
                      className={`q-card${q.is_approved ? " approved" : ""}${q.is_locked ? " locked" : ""}${busyQuestionId === q.id ? " busy" : ""}`}
                    >
                      <header className="q-head">
                        <span className="q-no">Câu {q.order_no}</span>
                        <span className="chip">{q.target_knowledge}</span>
                        <span className="chip">{q.level.code}</span>
                        <span className="chip">Nguồn: {q.source_ref}</span>
                        <span className="q-status">{q.is_approved ? "Đã duyệt" : "Chờ duyệt"}</span>
                      </header>

                      {q.passage_text && <p className="q-passage">{q.passage_text}</p>}
                      <p className="q-text">{q.prompt_text}</p>
                      {q.options && (
                        <ul className="q-options">
                          {q.options.map((opt) => (
                            <li key={opt.label} className={opt.is_correct ? "correct" : undefined}>
                              {opt.label}. <UnderlineText text={opt.text} />
                            </li>
                          ))}
                        </ul>
                      )}
                      <p className="q-answer">
                        <strong>Đáp án: {q.answer_text}</strong> — {q.explanation}
                      </p>
                      {q.warnings.length > 0 &&
                        q.warnings.map((w, i) => (
                          <p key={i} className="q-warning">
                            Cảnh báo: {w}
                          </p>
                        ))}
                      <footer className="q-actions">
                        <button type="button" onClick={() => handleApproveToggle(q)} disabled={mutationBusy}>
                          {q.is_approved ? "Bỏ duyệt" : "Duyệt"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRegenerate(q)}
                          disabled={mutationBusy || q.is_locked || q.is_approved}
                          title={q.is_locked ? "Câu đã khóa" : q.is_approved ? "Bỏ duyệt trước khi sinh lại" : ""}
                        >
                          Sinh lại
                        </button>
                        <button type="button" onClick={() => handleLockToggle(q)} disabled={mutationBusy}>
                          {q.is_locked ? "Đã khóa" : "Khóa"}
                        </button>
                      </footer>
                    </article>
                  ))}
              </div>
            </section>
          ))}

        <div className="review-footer">
          <p>100% câu phải được duyệt trước khi xuất. Câu đã khóa không đổi khi sinh lại.</p>
          <button
            type="button"
            onClick={handleFinish}
            disabled={mutationBusy || finishing || allQuestions.length === 0 || approvedCount !== allQuestions.length}
            className="button primary"
          >
            {finishing ? "Đang lưu..." : "Hoàn tất kiểm duyệt → Xuất"}
          </button>
        </div>
      </div>
    </>
  );
}

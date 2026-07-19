import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { completeReview, getExam, regenerateQuestion, updateQuestionFlags } from "../api/exams";
import { ApiError } from "../api/client";
import type { ExamDetailOut, QuestionOut } from "../types/exam";
import { useUsage } from "../usage/UsageContext";
import { useRouteGeneration, type RouteGenerationToken } from "../routing/useRouteGeneration";

interface ReviewOperation {
  id: number;
  route: RouteGenerationToken;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
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
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link to={`/exams/${examId}/builder`} style={{ fontSize: 13 }}>
          ← Sửa cấu trúc
        </Link>
        <p style={{ margin: 0, fontSize: 13 }}>
          <strong>{approvedCount}</strong>/{allQuestions.length} câu đã duyệt
        </p>
      </div>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

      {exam.blocks
        .slice()
        .sort((a, b) => a.order_no - b.order_no)
        .map((block) => (
          <section key={block.id} style={{ background: "var(--surface)", borderRadius: 14, padding: 18 }}>
            <h3 style={{ marginTop: 0, fontSize: 15 }}>
              {block.title} · {block.questions.length} câu
            </h3>
            <div style={{ display: "grid", gap: 10 }}>
              {block.questions
                .slice()
                .sort((a, b) => a.order_no - b.order_no)
                .map((q) => (
                  <article
                    key={q.id}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                      padding: 12,
                      background: q.is_approved ? "#f4fbf8" : "#fff",
                      opacity: busyQuestionId === q.id ? 0.6 : 1,
                    }}
                  >
                    {q.passage_text && (
                      <p style={{ fontStyle: "italic", fontSize: 13, color: "var(--muted)" }}>{q.passage_text}</p>
                    )}
                    <p style={{ margin: "0 0 6px", fontSize: 14 }}>
                      <strong>Câu {q.order_no}.</strong> {q.prompt_text}
                    </p>
                    {q.options && (
                      <ul style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, margin: "0 0 8px", paddingLeft: 0, listStyle: "none" }}>
                        {q.options.map((opt) => (
                          <li
                            key={opt.label}
                            style={{
                              fontSize: 13,
                              padding: "4px 8px",
                              borderRadius: 6,
                              border: "1px solid var(--border)",
                              fontWeight: opt.is_correct ? 700 : 400,
                              background: opt.is_correct ? "#f0faf5" : "transparent",
                            }}
                          >
                            {opt.label}. {opt.text}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p style={{ margin: "0 0 6px", fontSize: 12, background: "#ecf1fe", padding: "6px 10px", borderRadius: 6 }}>
                      Đáp án: {q.answer_text} — {q.explanation}
                    </p>
                    <p style={{ margin: "0 0 8px", fontSize: 11, color: "var(--muted)" }}>
                      {q.target_knowledge} · Level {q.level.code} · Nguồn: {q.source_ref}
                    </p>
                    {q.warnings.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        {q.warnings.map((w, i) => (
                          <p
                            key={i}
                            style={{
                              margin: "2px 0",
                              fontSize: 12,
                              color: "#8a5a06",
                              background: "#fdf3e2",
                              padding: "5px 8px",
                              borderRadius: 6,
                            }}
                          >
                            Cảnh báo: {w}
                          </p>
                        ))}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => handleApproveToggle(q)} style={smallButtonStyle} disabled={mutationBusy}>
                        {q.is_approved ? "Bỏ duyệt" : "Duyệt"}
                      </button>
                      <button
                        onClick={() => handleRegenerate(q)}
                        style={smallButtonStyle}
                        disabled={mutationBusy || q.is_locked || q.is_approved}
                        title={q.is_locked ? "Câu đã khóa" : q.is_approved ? "Bỏ duyệt trước khi sinh lại" : ""}
                      >
                        Sinh lại
                      </button>
                      <button onClick={() => handleLockToggle(q)} style={smallButtonStyle} disabled={mutationBusy}>
                        {q.is_locked ? "Đã khóa" : "Khóa"}
                      </button>
                    </div>
                  </article>
                ))}
            </div>
          </section>
        ))}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "var(--surface)",
          borderRadius: 14,
          padding: 16,
        }}
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          100% câu phải được duyệt trước khi xuất. Câu đã khóa không đổi khi sinh lại.
        </p>
        <button
          onClick={handleFinish}
          disabled={mutationBusy || finishing || allQuestions.length === 0 || approvedCount !== allQuestions.length}
          style={primaryButtonStyle}
        >
          {finishing ? "Đang lưu..." : "Hoàn tất kiểm duyệt → Xuất"}
        </button>
      </div>
    </div>
  );
}

const smallButtonStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "#fff",
  fontSize: 12,
  fontWeight: 600,
};

const primaryButtonStyle: React.CSSProperties = {
  height: 40,
  padding: "0 16px",
  borderRadius: 8,
  border: "none",
  background: "var(--primary)",
  color: "#fff",
  fontWeight: 600,
};

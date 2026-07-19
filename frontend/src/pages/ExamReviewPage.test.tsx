import { useState } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as examApi from "../api/exams";
import type { ExamDetailOut, QuestionOut } from "../types/exam";
import { ApiError } from "../api/client";
import { ExamReviewPage } from "./ExamReviewPage";

vi.mock("../api/exams", () => ({
  getExam: vi.fn(),
  updateQuestionFlags: vi.fn(),
  regenerateQuestion: vi.fn(),
  completeReview: vi.fn(),
}));

const refreshUsage = vi.fn();
vi.mock("../usage/UsageContext", () => ({ useUsage: () => ({ refresh: refreshUsage }) }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function makeExam(id: string, prompt: string, approved = false): ExamDetailOut {
  return {
    id, title: `Exam ${id}`, status: "draft", source_type: "global_success", grade_id: "grade-1",
    level: { id: "level-1", code: "A2" }, unit_id: "unit-1", grammar_topic_id: null,
    cambridge_certificate_id: null, extra_prompt: null, export_mode: null, variant_count: 0,
    grammar_point_ids: [],
    blocks: [{
      id: `block-${id}`, order_no: 1,
      exercise_type: { id: "type-1", code: "multiple_choice", name: "Multiple choice", has_passage: false },
      title: "Grammar", instruction: null, question_count: 1, points: "1.0", difficulty: "hon_hop",
      level_override: null, shuffle_questions: true, shuffle_answers: true, prompt_override: null,
      passage_word_target: null,
      questions: [{
        id: `question-${id}`, order_no: 1, prompt_text: prompt, passage_text: null, options: null,
        answer_text: "A", explanation: "Because", target_knowledge: "Grammar",
        level: { id: "level-1", code: "A2" }, source_ref: "fixture", warnings: [],
        is_approved: approved, is_locked: false,
      }],
    }],
  };
}

function NavigationControls() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState("exam-1");
  return (
    <button onClick={() => { const next = current === "exam-1" ? "exam-2" : "exam-1"; setCurrent(next); navigate(`/exams/${next}/review`); }}>
      Đổi đề
    </button>
  );
}

function renderReview(initialId = "exam-1") {
  return render(
    <MemoryRouter initialEntries={[`/exams/${initialId}/review`]}>
      <NavigationControls />
      <Routes>
        <Route path="/exams/:examId/review" element={<ExamReviewPage />} />
        <Route path="/exams/:examId/export" element={<p>Trang xuất đề</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ExamReviewPage route isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(examApi.updateQuestionFlags).mockResolvedValue({} as QuestionOut);
    vi.mocked(examApi.regenerateQuestion).mockResolvedValue({} as QuestionOut);
    vi.mocked(examApi.completeReview).mockResolvedValue(makeExam("exam-1", "Old prompt", true));
  });

  it("ignores an old exam response after navigation", async () => {
    const oldLoad = deferred<ExamDetailOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) =>
      id === "exam-1" ? oldLoad.promise : Promise.resolve(makeExam("exam-2", "New prompt")),
    );
    const user = userEvent.setup();
    renderReview();

    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New prompt")).toBeInTheDocument();
    await act(async () => oldLoad.resolve(makeExam("exam-1", "Old prompt")));

    await waitFor(() => expect(screen.queryByText("Old prompt")).not.toBeInTheDocument());
  });

  it("does not reload or refresh usage when old regeneration resolves", async () => {
    const oldRegeneration = deferred<QuestionOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) => Promise.resolve(makeExam(id, id === "exam-1" ? "Old prompt" : "New prompt")));
    vi.mocked(examApi.regenerateQuestion).mockReturnValueOnce(oldRegeneration.promise);
    const user = userEvent.setup();
    renderReview();
    await user.click(await screen.findByRole("button", { name: "Sinh lại" }));

    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New prompt")).toBeInTheDocument();
    await act(async () => oldRegeneration.resolve(makeExam("exam-1", "Old prompt").blocks[0]!.questions[0]!));

    await waitFor(() => expect(refreshUsage).not.toHaveBeenCalled());
    expect(examApi.getExam).toHaveBeenCalledTimes(2);
  });

  it("does not navigate when old complete-review resolves", async () => {
    const oldComplete = deferred<ExamDetailOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) => Promise.resolve(makeExam(id, id === "exam-1" ? "Old prompt" : "New prompt", true)));
    vi.mocked(examApi.completeReview).mockReturnValueOnce(oldComplete.promise);
    const user = userEvent.setup();
    renderReview();
    await user.click(await screen.findByRole("button", { name: /Hoàn tất kiểm duyệt/ }));

    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New prompt")).toBeInTheDocument();
    await act(async () => oldComplete.resolve(makeExam("exam-1", "Old prompt", true)));

    await waitFor(() => expect(screen.queryByText("Trang xuất đề")).not.toBeInTheDocument());
  });

  it("keeps current questions and shows a reload error after mutation", async () => {
    vi.mocked(examApi.getExam)
      .mockResolvedValueOnce(makeExam("exam-1", "Current prompt"))
      .mockRejectedValueOnce(new ApiError(500, "Không tải lại được đề"));
    const user = userEvent.setup();
    renderReview();

    await user.click(await screen.findByRole("button", { name: "Duyệt" }));

    expect(await screen.findByText("Không tải lại được đề")).toBeInTheDocument();
    expect(screen.getByText("Current prompt")).toBeInTheDocument();
  });
});

import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { ExamDetailOut } from "../types/exam";
import type { ExamPreviewOut } from "../types/examPreview";
import { ExamBuilderPage } from "./ExamBuilderPage";

const examApi = vi.hoisted(() => ({
  addBlock: vi.fn(),
  deleteBlock: vi.fn(),
  generateExam: vi.fn(),
  getExam: vi.fn(),
  getExamPreview: vi.fn(),
  reorderBlocks: vi.fn(),
  setGrammarSelection: vi.fn(),
  updateBlock: vi.fn(),
}));

const catalogApi = vi.hoisted(() => ({
  listExerciseTypes: vi.fn(),
  listGrammarTopics: vi.fn(),
}));

vi.mock("../api/exams", () => examApi);
vi.mock("../api/catalog", () => catalogApi);
vi.mock("../usage/UsageContext", () => ({
  useUsage: () => ({ refresh: vi.fn() }),
}));

const blocks: ExamDetailOut["blocks"] = [
  {
    id: "a",
    order_no: 1,
    exercise_type: { id: "type-1", code: "multiple_choice", name: "Trắc nghiệm", has_passage: false },
    title: "A",
    instruction: null,
    question_count: 5,
    points: "1.0",
    difficulty: "nhan_biet",
    level_override: null,
    shuffle_questions: false,
    shuffle_answers: false,
    prompt_override: null,
    passage_word_target: null,
    questions: [],
  },
  {
    id: "b",
    order_no: 2,
    exercise_type: { id: "type-1", code: "multiple_choice", name: "Trắc nghiệm", has_passage: false },
    title: "B",
    instruction: null,
    question_count: 5,
    points: "1.0",
    difficulty: "nhan_biet",
    level_override: null,
    shuffle_questions: false,
    shuffle_answers: false,
    prompt_override: null,
    passage_word_target: null,
    questions: [],
  },
];

const exam: ExamDetailOut = {
  id: "exam-1",
  title: "Đề kiểm tra",
  status: "draft",
  source_type: "common_knowledge",
  grade_id: "grade-1",
  level: { id: "level-1", code: "A2" },
  unit_id: null,
  grammar_topic_id: "topic-1",
  cambridge_certificate_id: null,
  extra_prompt: null,
  export_mode: null,
  variant_count: 1,
  grammar_point_ids: [],
  blocks,
};

const preview: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra",
  total_questions: 10,
  total_points: "2.0",
  page_count: 1,
  pages: [
    {
      page_number: 1,
      blocks: [
        {
          block_id: "a",
          section_number: 1,
          section_label: "I",
          title: "A",
          instruction: null,
          question_start: 1,
          question_end: 5,
          question_count: 5,
          points: "1.0",
          continuation: false,
          questions: [{ question_number: 1, prompt_text: null, passage_text: null, is_placeholder: true }],
        },
      ],
    },
  ],
};

function renderBuilder() {
  return render(
    <MemoryRouter initialEntries={["/exams/exam-1/builder"]}>
      <Routes>
        <Route path="/exams/:examId/builder" element={<ExamBuilderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function blockOrder() {
  return screen.getAllByTestId(/block-/).map((element) => element.dataset.testid);
}

describe("ExamBuilderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    examApi.getExam.mockResolvedValue(exam);
    examApi.getExamPreview.mockResolvedValue(preview);
    examApi.addBlock.mockResolvedValue(blocks[0]);
    examApi.deleteBlock.mockResolvedValue(undefined);
    examApi.updateBlock.mockResolvedValue(blocks[0]);
    examApi.setGrammarSelection.mockResolvedValue(exam);
    examApi.reorderBlocks.mockResolvedValue(exam);
    catalogApi.listExerciseTypes.mockResolvedValue([blocks[0]!.exercise_type]);
    catalogApi.listGrammarTopics.mockResolvedValue([
      {
        id: "topic-1",
        name: "Ngữ pháp — A2",
        groups: [
          {
            id: "group-1",
            name: "Thì",
            points: [{ id: "point-1", name: "Hiện tại đơn", min_level: { id: "level-1", code: "A2" } }],
          },
        ],
      },
    ]);
  });

  it("loads exam and preview together", async () => {
    renderBuilder();

    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
    expect(examApi.getExam).toHaveBeenCalledWith("exam-1");
    expect(examApi.getExamPreview).toHaveBeenCalledWith("exam-1");
    expect(screen.getByLabelText("Bản xem trước đề A4")).toBeInTheDocument();
  });

  it("ignores an older preview response that resolves after a mutation refresh", async () => {
    const user = userEvent.setup();
    let resolveInitialPreview!: (value: ExamPreviewOut) => void;
    let resolveRefreshedPreview!: (value: ExamPreviewOut) => void;
    examApi.getExamPreview
      .mockReturnValueOnce(
        new Promise<ExamPreviewOut>((resolve) => {
          resolveInitialPreview = resolve;
        }),
      )
      .mockReturnValueOnce(
        new Promise<ExamPreviewOut>((resolve) => {
          resolveRefreshedPreview = resolve;
        }),
      );
    renderBuilder();
    await screen.findByRole("heading", { name: "Đề kiểm tra" });

    await user.click(screen.getByRole("button", { name: "+ Thêm phần" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));
    await act(async () => resolveRefreshedPreview({ ...preview, title: "Bản mới" }));
    expect(await screen.findAllByText("Bản mới")).toHaveLength(2);

    await act(async () => resolveInitialPreview({ ...preview, title: "Bản cũ" }));
    await waitFor(() => expect(screen.queryByText("Bản cũ")).not.toBeInTheDocument());
    expect(screen.getAllByText("Bản mới")).toHaveLength(2);
  });

  it("rolls back reorder and keeps preview after API failure", async () => {
    const user = userEvent.setup();
    examApi.reorderBlocks.mockRejectedValueOnce(new ApiError(500, "Không lưu được thứ tự"));
    renderBuilder();

    await user.click(await screen.findByRole("button", { name: "Xuống A" }));

    expect(await screen.findByText("Không lưu được thứ tự")).toBeInTheDocument();
    expect(blockOrder()).toEqual(["block-a", "block-b"]);
    expect(examApi.getExamPreview).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Trang 1/1")).toBeInTheDocument();
  });

  it("applies reorder immediately, blocks overlap, then uses the API result and refreshes preview", async () => {
    const user = userEvent.setup();
    let resolveReorder!: (value: ExamDetailOut) => void;
    examApi.reorderBlocks.mockReturnValueOnce(
      new Promise<ExamDetailOut>((resolve) => {
        resolveReorder = resolve;
      }),
    );
    const reorderedExam = {
      ...exam,
      blocks: [
        { ...blocks[1]!, order_no: 1, title: "B đã lưu" },
        { ...blocks[0]!, order_no: 2 },
      ],
    };
    renderBuilder();

    await user.click(await screen.findByRole("button", { name: "Xuống A" }));

    expect(blockOrder()).toEqual(["block-b", "block-a"]);
    expect(screen.getByRole("button", { name: "Lên A" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "+ Thêm phần" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lưu lựa chọn" })).toBeDisabled();
    expect(examApi.reorderBlocks).toHaveBeenCalledWith("exam-1", ["b", "a"]);

    await act(async () => resolveReorder(reorderedExam));

    expect(await screen.findByText("1. B đã lưu")).toBeInTheDocument();
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));
  });

  it("refreshes exam and preview after add, delete, update, and grammar mutations", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("button", { name: "+ Thêm phần" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole("button", { name: "Xóa A" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(3));

    const questionCount = screen.getByLabelText("Số câu A");
    await user.clear(questionCount);
    await user.type(questionCount, "8");
    act(() => questionCount.blur());
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(4));

    await user.click(screen.getByRole("checkbox", { name: /Hiện tại đơn/ }));
    await user.click(screen.getByRole("button", { name: "Lưu lựa chọn" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(5));

    expect(examApi.getExam).toHaveBeenCalledTimes(5);
    expect(examApi.updateBlock).toHaveBeenCalledWith("exam-1", "a", { question_count: 8 });
    expect(examApi.setGrammarSelection).toHaveBeenCalledWith("exam-1", ["point-1"]);
  });
});

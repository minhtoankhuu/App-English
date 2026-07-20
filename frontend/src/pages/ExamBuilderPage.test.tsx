import { StrictMode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { ExerciseTypeOut, GrammarTopicOut } from "../types/catalog";
import type { ExamDetailOut } from "../types/exam";
import type { ExamPreviewOut } from "../types/examPreview";
import { ExamBuilderPage } from "./ExamBuilderPage";

const examApi = vi.hoisted(() => ({
  addBlock: vi.fn(),
  addBlockPart: vi.fn(),
  deleteBlock: vi.fn(),
  deleteBlockPart: vi.fn(),
  generateExam: vi.fn(),
  getExam: vi.fn(),
  getExamPreview: vi.fn(),
  reorderBlocks: vi.fn(),
  setGrammarSelection: vi.fn(),
  updateBlock: vi.fn(),
  updateBlockPart: vi.fn(),
}));

const catalogApi = vi.hoisted(() => ({
  listExerciseTypes: vi.fn(),
  listGrammarTopics: vi.fn(),
  listProficiencyLevels: vi.fn(),
  listGrades: vi.fn(),
  listPassageLengthRules: vi.fn(),
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
    parts: [],
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
    parts: [],
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
  grade_number: 7,
  level_code: "A2",
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
          questions: [
            {
              question_number: 1,
              prompt_text: null,
              passage_text: null,
              is_placeholder: true,
              part_number: null,
              part_title: null,
              part_instruction: null,
            },
          ],
        },
      ],
    },
  ],
};

const wordFormType: ExerciseTypeOut = {
  id: "type-2",
  code: "word_form",
  name: "Word form",
  default_instruction: "",
  has_passage: false,
  order_no: 2,
};

const examTwo: ExamDetailOut = {
  ...exam,
  id: "exam-2",
  title: "Đề số hai",
  grammar_point_ids: ["point-1"],
  blocks: blocks.map((block, index) => ({
    ...block,
    id: index === 0 ? "c" : "d",
    title: index === 0 ? "C" : "D",
  })),
};

const previewTwo: ExamPreviewOut = {
  ...preview,
  exam_id: "exam-2",
  title: "Đề số hai",
  pages: preview.pages.map((page) => ({
    ...page,
    blocks: page.blocks.map((block) => ({ ...block, block_id: "c", title: "C" })),
  })),
};

function NavigationControl() {
  const navigate = useNavigate();
  return (
    <button type="button" onClick={() => navigate("/exams/exam-2/builder")}>
      Mở đề số hai
    </button>
  );
}

function renderBuilder() {
  return render(
    <MemoryRouter initialEntries={["/exams/exam-1/builder"]}>
      <NavigationControl />
      <Routes>
        <Route path="/exams/:examId/builder" element={<ExamBuilderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderBuilderStrict() {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={["/exams/exam-1/builder"]}>
        <Routes>
          <Route path="/exams/:examId/builder" element={<ExamBuilderPage />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
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
    catalogApi.listExerciseTypes.mockResolvedValue([blocks[0]!.exercise_type, wordFormType]);
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
    catalogApi.listProficiencyLevels.mockResolvedValue([{ id: "level-1", code: "A2", rank: 2 }]);
    catalogApi.listGrades.mockResolvedValue([
      { id: "grade-1", number: 7, school_stage: { id: "s1", code: "secondary", name: "THCS", order_no: 2 }, suggested_level: { id: "level-1", code: "A2", rank: 2 } },
    ]);
    catalogApi.listPassageLengthRules.mockResolvedValue([{ grade_min: 6, grade_max: 7, min_words: 80, max_words: 150 }]);
    examApi.addBlockPart.mockResolvedValue(blocks[0]);
    examApi.updateBlockPart.mockResolvedValue(blocks[0]);
    examApi.deleteBlockPart.mockResolvedValue(blocks[0]);
  });

  it("loads exam and preview together", async () => {
    renderBuilder();

    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
    expect(examApi.getExam).toHaveBeenCalledWith("exam-1");
    expect(examApi.getExamPreview).toHaveBeenCalledWith("exam-1");
    expect(screen.getByLabelText("Bản xem trước đề A4")).toBeInTheDocument();
  });

  it("reloads the active route during StrictMode effect replay", async () => {
    renderBuilderStrict();

    expect(await screen.findByTestId("block-a")).toBeInTheDocument();
    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
  });

  it("renders the editor while the initial preview is still loading", async () => {
    let resolvePreview!: (value: ExamPreviewOut) => void;
    examApi.getExamPreview.mockReturnValueOnce(
      new Promise<ExamPreviewOut>((resolve) => {
        resolvePreview = resolve;
      }),
    );
    renderBuilder();

    expect(await screen.findByTestId("block-a")).toBeInTheDocument();
    expect(screen.getByText("Đang dựng bản xem trước...")).toBeInTheDocument();

    await act(async () => resolvePreview(preview));
    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
  });

  it("renders the preview while the initial exam is still loading", async () => {
    examApi.getExam.mockReturnValueOnce(new Promise<ExamDetailOut>(() => undefined));
    renderBuilder();

    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
    expect(screen.queryByTestId("block-a")).not.toBeInTheDocument();
  });

  it("retries preview loading in the Builder and clears the active error", async () => {
    const user = userEvent.setup();
    let resolveRetry!: (value: ExamPreviewOut) => void;
    examApi.getExamPreview
      .mockRejectedValueOnce(new ApiError(503, "Không tải được bản xem trước"))
      .mockReturnValueOnce(
        new Promise<ExamPreviewOut>((resolve) => {
          resolveRetry = resolve;
        }),
      );
    renderBuilder();
    expect(await screen.findByText("Không tải được bản xem trước")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(screen.queryByText("Không tải được bản xem trước")).not.toBeInTheDocument();
    expect(screen.getByText("Đang dựng bản xem trước...")).toBeInTheDocument();

    await act(async () => resolveRetry(preview));
    expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
    expect(examApi.getExamPreview).toHaveBeenCalledTimes(2);
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

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));
    await act(async () => resolveRefreshedPreview({ ...preview, title: "Bản mới" }));
    expect(await screen.findAllByText("BẢN MỚI")).toHaveLength(1);

    await act(async () => resolveInitialPreview({ ...preview, title: "Bản cũ" }));
    await waitFor(() => expect(screen.queryByText("BẢN CŨ")).not.toBeInTheDocument());
    expect(screen.getAllByText("BẢN MỚI")).toHaveLength(1);
  });

  it("ignores deferred exam and preview responses from the previous route", async () => {
    const user = userEvent.setup();
    let resolveOldExam!: (value: ExamDetailOut) => void;
    let resolveNewExam!: (value: ExamDetailOut) => void;
    let resolveOldPreview!: (value: ExamPreviewOut) => void;
    let resolveNewPreview!: (value: ExamPreviewOut) => void;
    examApi.getExam.mockImplementation(
      (targetId: string) =>
        new Promise<ExamDetailOut>((resolve) => {
          if (targetId === "exam-1") resolveOldExam = resolve;
          else resolveNewExam = resolve;
        }),
    );
    examApi.getExamPreview.mockImplementation(
      (targetId: string) =>
        new Promise<ExamPreviewOut>((resolve) => {
          if (targetId === "exam-1") resolveOldPreview = resolve;
          else resolveNewPreview = resolve;
        }),
    );
    renderBuilder();
    await user.click(screen.getByRole("button", { name: "Mở đề số hai" }));

    await act(async () => {
      resolveNewExam(examTwo);
      resolveNewPreview(previewTwo);
    });
    expect(await screen.findByTestId("block-c")).toBeInTheDocument();

    await act(async () => {
      resolveOldExam(exam);
      resolveOldPreview({ ...preview, title: "Đề cũ về muộn" });
    });
    expect(screen.getByTestId("block-c")).toBeInTheDocument();
    expect(screen.queryByTestId("block-a")).not.toBeInTheDocument();
    expect(screen.queryByText("Đề cũ về muộn")).not.toBeInTheDocument();
  });

  it("ignores stale catalog responses after the route changes", async () => {
    const user = userEvent.setup();
    let resolveOldTypes!: (value: ExerciseTypeOut[]) => void;
    let resolveNewTypes!: (value: ExerciseTypeOut[]) => void;
    let resolveOldTopics!: (value: GrammarTopicOut[]) => void;
    let resolveNewTopics!: (value: GrammarTopicOut[]) => void;
    catalogApi.listExerciseTypes
      .mockReturnValueOnce(new Promise((resolve) => (resolveOldTypes = resolve)))
      .mockReturnValueOnce(new Promise((resolve) => (resolveNewTypes = resolve)));
    catalogApi.listGrammarTopics
      .mockReturnValueOnce(new Promise((resolve) => (resolveOldTopics = resolve)))
      .mockReturnValueOnce(new Promise((resolve) => (resolveNewTopics = resolve)));
    examApi.getExam.mockImplementation((targetId: string) => Promise.resolve(targetId === "exam-1" ? exam : examTwo));
    examApi.getExamPreview.mockImplementation((targetId: string) =>
      Promise.resolve(targetId === "exam-1" ? preview : previewTwo),
    );
    renderBuilder();
    await screen.findByTestId("block-a");
    await user.click(screen.getByRole("button", { name: "Mở đề số hai" }));
    await screen.findByTestId("block-c");

    const newType: ExerciseTypeOut = {
      ...blocks[0]!.exercise_type,
      id: "type-new",
      name: "Dạng mới",
      default_instruction: "",
      order_no: 1,
    };
    const oldType: ExerciseTypeOut = {
      ...blocks[0]!.exercise_type,
      id: "type-old",
      name: "Dạng cũ",
      default_instruction: "",
      order_no: 1,
    };
    await act(async () => {
      resolveNewTypes([newType]);
      resolveNewTopics([
        {
          id: "topic-1",
          code: "topic-new",
          name: "Ngữ pháp mới — A2",
          groups: [],
        },
      ]);
    });
    expect(await screen.findByRole("checkbox", { name: "Dạng mới" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chọn Ngữ pháp mới" })).toBeInTheDocument();

    await act(async () => {
      resolveOldTypes([oldType]);
      resolveOldTopics([
        {
          id: "topic-1",
          code: "topic-old",
          name: "Ngữ pháp cũ — A2",
          groups: [],
        },
      ]);
    });
    expect(screen.queryByRole("checkbox", { name: "Dạng cũ" })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Dạng mới" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chọn Ngữ pháp mới" })).toBeInTheDocument();
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
    expect(screen.getByRole("checkbox", { name: "Trắc nghiệm" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lưu lựa chọn" })).toBeDisabled();
    expect(examApi.reorderBlocks).toHaveBeenCalledWith("exam-1", ["b", "a"]);

    await act(async () => resolveReorder(reorderedExam));

    expect(await screen.findByText("B đã lưu")).toBeInTheDocument();
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));
  });

  it("isolates old route fetches, mutations, and locks after navigation", async () => {
    const user = userEvent.setup();
    let resolveOldReorder!: (value: ExamDetailOut) => void;
    let resolveNewReorder!: (value: ExamDetailOut) => void;
    let resolveExamTwo!: (value: ExamDetailOut) => void;
    let resolvePreviewTwo!: (value: ExamPreviewOut) => void;
    let examTwoPreviewCalls = 0;
    examApi.getExam.mockImplementation((examId: string) => {
      if (examId === "exam-1") return Promise.resolve(exam);
      return new Promise<ExamDetailOut>((resolve) => {
        resolveExamTwo = resolve;
      });
    });
    examApi.getExamPreview.mockImplementation((examId: string) => {
      if (examId === "exam-2") {
        examTwoPreviewCalls += 1;
        if (examTwoPreviewCalls > 1) return Promise.resolve(previewTwo);
        return new Promise<ExamPreviewOut>((resolve) => {
          resolvePreviewTwo = resolve;
        });
      }
      return Promise.resolve(preview);
    });
    examApi.reorderBlocks.mockImplementation((examId: string) =>
      new Promise<ExamDetailOut>((resolve) => {
        if (examId === "exam-1") resolveOldReorder = resolve;
        else resolveNewReorder = resolve;
      }),
    );
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Xuống A" }));
    await user.click(screen.getByRole("button", { name: "Mở đề số hai" }));

    expect(screen.queryByTestId("block-a")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Xóa A" })).not.toBeInTheDocument();
    expect(screen.getByText("Đang tải...")).toBeInTheDocument();

    await act(async () => {
      resolvePreviewTwo(previewTwo);
      resolveExamTwo(examTwo);
    });
    expect(await screen.findByTestId("block-c")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Đề số hai" })).toBeInTheDocument();
    expect(screen.getByText("ĐỀ SỐ HAI")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Xuống C" }));
    expect(screen.getByRole("checkbox", { name: "Trắc nghiệm" })).toBeDisabled();

    await act(async () => resolveOldReorder({ ...exam, blocks: [...blocks].reverse() }));

    expect(screen.getByTestId("block-c")).toBeInTheDocument();
    expect(screen.queryByTestId("block-a")).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Trắc nghiệm" })).toBeDisabled();

    await act(async () => resolveNewReorder(examTwo));
    await waitFor(() => expect(screen.getByRole("checkbox", { name: "Trắc nghiệm" })).toBeEnabled());
    expect(screen.getByTestId("block-c")).toBeInTheDocument();
  });

  it("clears an active Builder error when the next mutation starts", async () => {
    const user = userEvent.setup();
    let resolveAdd!: (value: ExamDetailOut["blocks"][number]) => void;
    examApi.reorderBlocks.mockRejectedValueOnce(new ApiError(500, "Không lưu được thứ tự"));
    examApi.addBlock.mockReturnValueOnce(
      new Promise<ExamDetailOut["blocks"][number]>((resolve) => {
        resolveAdd = resolve;
      }),
    );
    renderBuilder();
    await user.click(await screen.findByRole("button", { name: "Xuống A" }));
    expect(await screen.findByText("Không lưu được thứ tự")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));
    expect(screen.queryByText("Không lưu được thứ tự")).not.toBeInTheDocument();

    await act(async () => resolveAdd(blocks[0]!));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("Không lưu được thứ tự")).not.toBeInTheDocument();
  });

  it("keeps the stale editor and shows the reload error after a successful mutation", async () => {
    const user = userEvent.setup();
    examApi.getExam.mockResolvedValueOnce(exam).mockRejectedValueOnce(new Error("network down"));
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));

    expect(await screen.findByText("Không tải được đề")).toBeInTheDocument();
    expect(screen.getByTestId("block-a")).toBeInTheDocument();
    expect(screen.getByText("Trang 1/1")).toBeInTheDocument();
  });

  it("refreshes exam and preview after add, delete, update, and grammar mutations", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole("button", { name: "Xóa A" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(3));

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));
    const questionCount = screen.getByLabelText("Số câu");
    await user.clear(questionCount);
    await user.type(questionCount, "8");
    await user.click(screen.getByRole("button", { name: "Lưu" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(4));

    await user.click(screen.getByRole("checkbox", { name: /Hiện tại đơn/ }));
    await user.click(screen.getByRole("button", { name: "Lưu lựa chọn" }));
    await waitFor(() => expect(examApi.getExamPreview).toHaveBeenCalledTimes(5));

    expect(examApi.getExam).toHaveBeenCalledTimes(5);
    expect(examApi.updateBlock).toHaveBeenCalledWith("exam-1", "a", {
      title: "A",
      instruction: null,
      difficulty: "nhan_biet",
      question_count: 8,
      points: 1,
      level_override_id: null,
      shuffle_questions: false,
      shuffle_answers: false,
      prompt_override: null,
      passage_word_target: null,
    });
    expect(examApi.setGrammarSelection).toHaveBeenCalledWith("exam-1", ["point-1"]);
  });

  it("ticking an exercise type without a block adds one with default count and points", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));

    expect(examApi.addBlock).toHaveBeenCalledWith("exam-1", {
      exercise_type_id: "type-2",
      title: "Word form",
      question_count: 5,
      points: 1,
    });
  });

  it("unticking an exercise type deletes every block of that type", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("checkbox", { name: "Trắc nghiệm" }));

    expect(examApi.deleteBlock).toHaveBeenCalledWith("exam-1", "a");
    expect(examApi.deleteBlock).toHaveBeenCalledWith("exam-1", "b");
  });

  it("shows passage word hint for passage-based types and saves full block edit", async () => {
    const user = userEvent.setup();
    const readingType = { id: "type-read", code: "reading_true_false", name: "Đọc hiểu True/False", has_passage: true };
    const readingBlock = {
      ...blocks[0]!,
      id: "r",
      title: "Đọc hiểu True/False",
      exercise_type: readingType,
      instruction: null,
      difficulty: "hon_hop" as const,
      level_override: null,
      passage_word_target: null,
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [readingBlock] });
    renderBuilder();
    await screen.findByTestId("block-r");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa Đọc hiểu True/False" }));

    expect(screen.getByText(/Gợi ý 80–150 từ cho Lớp 7/)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Tiêu đề phần"));
    await user.type(screen.getByLabelText("Tiêu đề phần"), "III. Reading");
    await user.selectOptions(screen.getByLabelText("Trình độ của phần này"), "A2");
    await user.click(screen.getByRole("button", { name: "Lưu" }));

    expect(examApi.updateBlock).toHaveBeenCalledWith("exam-1", "r", {
      title: "III. Reading",
      instruction: null,
      difficulty: "hon_hop",
      question_count: 5,
      points: 1,
      level_override_id: "level-1",
      shuffle_questions: false,
      shuffle_answers: false,
      prompt_override: null,
      passage_word_target: 120,
    });
  });

  it("adds a sub-part and disables the block-level question count once a part exists", async () => {
    const user = userEvent.setup();
    const blockWithPart = {
      ...blocks[0]!,
      question_count: 5,
      parts: [{ id: "part-1", order_no: 1, title: "So sánh kép", instruction: null, question_count: 5, prompt_override: null }],
    };
    examApi.addBlockPart.mockResolvedValue(blockWithPart);
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));
    await user.type(screen.getByLabelText("Tiêu đề phần con"), "So sánh kép");
    await user.click(screen.getByRole("button", { name: "+ Thêm phần con" }));

    expect(examApi.addBlockPart).toHaveBeenCalledWith("exam-1", "a", {
      title: "So sánh kép",
      instruction: null,
      question_count: 5,
      prompt_override: null,
    });
    expect(await screen.findByText(/1\. So sánh kép/)).toBeInTheDocument();
    expect(screen.getByLabelText("Số câu")).toBeDisabled();
  });

  it("edits and deletes an existing sub-part", async () => {
    const user = userEvent.setup();
    const existingPart = { id: "part-1", order_no: 1, title: "So sánh kép", instruction: null, question_count: 5, prompt_override: null };
    const blockWithPart = { ...blocks[0]!, question_count: 5, parts: [existingPart] };
    const blockWithoutPart = { ...blocks[0]!, parts: [] };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [blockWithPart, blocks[1]!] });
    examApi.updateBlockPart.mockResolvedValue({ ...blockWithPart, parts: [{ ...existingPart, question_count: 8 }] });
    examApi.deleteBlockPart.mockResolvedValue(blockWithoutPart);
    renderBuilder();
    await screen.findByText("Trang 1/1");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));
    await user.click(screen.getByRole("button", { name: "Sửa" }));
    expect(screen.getByLabelText("Tiêu đề phần con")).toHaveValue("So sánh kép");

    await user.clear(screen.getByLabelText("Số câu của phần con"));
    await user.type(screen.getByLabelText("Số câu của phần con"), "8");
    await user.click(screen.getByRole("button", { name: "Lưu phần con" }));

    expect(examApi.updateBlockPart).toHaveBeenCalledWith("exam-1", "a", "part-1", {
      title: "So sánh kép",
      instruction: null,
      question_count: 8,
      prompt_override: null,
    });

    await user.click(await screen.findByRole("button", { name: "Xóa" }));
    expect(examApi.deleteBlockPart).toHaveBeenCalledWith("exam-1", "a", "part-1");
  });
});

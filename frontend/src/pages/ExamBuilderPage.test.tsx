import { StrictMode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { ExerciseTypeOut, GrammarTopicOut } from "../types/catalog";
import type { ExamDetailOut } from "../types/exam";
import { ExamBuilderPage } from "./ExamBuilderPage";

const examApi = vi.hoisted(() => ({
  addBlock: vi.fn(),
  addBlockPart: vi.fn(),
  deleteBlock: vi.fn(),
  deleteBlockPart: vi.fn(),
  generateExam: vi.fn(),
  getExam: vi.fn(),
  reorderBlocks: vi.fn(),
  setGrammarSelection: vi.fn(),
  updateBlock: vi.fn(),
  updateExam: vi.fn(),
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

const wordFormType: ExerciseTypeOut = {
  id: "type-2",
  code: "word_form",
  name: "Word form",
  default_instruction: "",
  has_passage: false,
  order_no: 2,
};

const matchingType: ExerciseTypeOut = {
  id: "type-3",
  code: "matching",
  name: "Nối câu",
  default_instruction: "",
  has_passage: false,
  order_no: 4,
};

const stressType: ExerciseTypeOut = {
  id: "type-stress",
  code: "stress",
  name: "Trọng âm",
  default_instruction: "",
  has_passage: false,
  order_no: 5,
};

const pronunciationType: ExerciseTypeOut = {
  id: "type-pron",
  code: "pronunciation",
  name: "Phát âm",
  default_instruction: "",
  has_passage: false,
  order_no: 3,
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
    examApi.addBlock.mockResolvedValue(blocks[0]);
    examApi.deleteBlock.mockResolvedValue(undefined);
    examApi.updateBlock.mockResolvedValue(blocks[0]);
    examApi.updateExam.mockResolvedValue({ ...exam, title: "Đề kiểm tra (đã sửa)" });
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

  it("loads the exam", async () => {
    renderBuilder();

    expect(await screen.findByTestId("block-a")).toBeInTheDocument();
    expect(examApi.getExam).toHaveBeenCalledWith("exam-1");
    // Khung xem trước A4 đã bỏ khỏi giao diện (chốt 24/08/2026).
    expect(screen.queryByLabelText("Bản xem trước đề A4")).not.toBeInTheDocument();
  });

  it("edits the exam title inline and refreshes the exam", async () => {
    const user = userEvent.setup();
    examApi.getExam.mockResolvedValueOnce(exam).mockResolvedValueOnce({ ...exam, title: "Đề kiểm tra (đã sửa)" });
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa tiêu đề đề thi" }));
    const titleInput = screen.getByLabelText("Tiêu đề đề thi");
    await user.clear(titleInput);
    await user.type(titleInput, "Đề kiểm tra (đã sửa)");
    await user.click(screen.getByRole("button", { name: "Lưu" }));

    expect(examApi.updateExam).toHaveBeenCalledWith("exam-1", { title: "Đề kiểm tra (đã sửa)" });
    expect(await screen.findByRole("heading", { name: "Đề kiểm tra (đã sửa)" })).toBeInTheDocument();
  });

  it("cancels exam title editing without calling the API", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa tiêu đề đề thi" }));
    await user.click(screen.getByRole("button", { name: "Hủy" }));

    expect(examApi.updateExam).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Đề kiểm tra" })).toBeInTheDocument();
  });

  it("reloads the active route during StrictMode effect replay", async () => {
    renderBuilderStrict();

    expect(await screen.findByTestId("block-a")).toBeInTheDocument();
    expect(await screen.findByTestId("block-a")).toBeInTheDocument();
  });

  it("ignores deferred exam responses from the previous route", async () => {
    const user = userEvent.setup();
    let resolveOldExam!: (value: ExamDetailOut) => void;
    let resolveNewExam!: (value: ExamDetailOut) => void;
    examApi.getExam.mockImplementation(
      (targetId: string) =>
        new Promise<ExamDetailOut>((resolve) => {
          if (targetId === "exam-1") resolveOldExam = resolve;
          else resolveNewExam = resolve;
        }),
    );
    renderBuilder();
    await user.click(screen.getByRole("button", { name: "Mở đề số hai" }));

    await act(async () => {
      resolveNewExam(examTwo);
    });
    expect(await screen.findByTestId("block-c")).toBeInTheDocument();

    await act(async () => {
      resolveOldExam(exam);
    });
    expect(screen.getByTestId("block-c")).toBeInTheDocument();
    expect(screen.queryByTestId("block-a")).not.toBeInTheDocument();
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

  it("rolls back reorder after API failure", async () => {
    const user = userEvent.setup();
    examApi.reorderBlocks.mockRejectedValueOnce(new ApiError(500, "Không lưu được thứ tự"));
    renderBuilder();

    await user.click(await screen.findByRole("button", { name: "Xuống A" }));

    expect(await screen.findByText("Không lưu được thứ tự")).toBeInTheDocument();
    expect(blockOrder()).toEqual(["block-a", "block-b"]);
    expect(examApi.getExam).toHaveBeenCalledTimes(1);
  });

  it("applies reorder immediately, blocks overlap, then uses the API result", async () => {
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
    // Kết quả sắp xếp dùng thẳng phản hồi của API — không tải lại đề.
    expect(examApi.getExam).toHaveBeenCalledTimes(1);
  });

  it("isolates old route fetches, mutations, and locks after navigation", async () => {
    const user = userEvent.setup();
    let resolveOldReorder!: (value: ExamDetailOut) => void;
    let resolveNewReorder!: (value: ExamDetailOut) => void;
    let resolveExamTwo!: (value: ExamDetailOut) => void;
    examApi.getExam.mockImplementation((examId: string) => {
      if (examId === "exam-1") return Promise.resolve(exam);
      return new Promise<ExamDetailOut>((resolve) => {
        resolveExamTwo = resolve;
      });
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
      resolveExamTwo(examTwo);
    });
    expect(await screen.findByTestId("block-c")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Đề số hai" })).toBeInTheDocument();
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
    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(2));
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
  });

  it("refreshes the exam after add, delete, update, and grammar mutations", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));
    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(2));

    await user.click(screen.getByRole("button", { name: "Xóa A" }));
    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(3));

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));
    const questionCount = screen.getByLabelText("Số câu");
    await user.clear(questionCount);
    await user.type(questionCount, "8");
    await user.click(screen.getByRole("button", { name: "Lưu" }));
    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(4));

    await user.click(screen.getByRole("checkbox", { name: /Hiện tại đơn/ }));
    await user.click(screen.getByRole("button", { name: "Lưu lựa chọn" }));
    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(5));

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
    catalogApi.listExerciseTypes.mockResolvedValue([blocks[0]!.exercise_type, matchingType]);
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Nối câu" }));

    expect(examApi.addBlock).toHaveBeenCalledWith("exam-1", {
      exercise_type_id: "type-3",
      title: "MATCHING",
      question_count: 5,
      points: 1,
    });
  });

  it("ticking Word form creates 1 block with Phần A/B pinned to one kiểu each", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Word form" }));

    expect(examApi.addBlock).toHaveBeenCalledWith("exam-1", {
      exercise_type_id: "type-2",
      title: "WORD FORMATION",
      question_count: 15,  // 3 họ từ × 5 câu
      points: 2,
    });
    await waitFor(() => expect(examApi.addBlockPart).toHaveBeenCalledTimes(2));
    const kinds = vi.mocked(examApi.addBlockPart).mock.calls.map(([, , part]) => part.prompt_override);
    // Hai phần phải ghim HAI kiểu khác nhau — nếu trùng thì Part B ra đề giống hệt Part A.
    expect(new Set(kinds).size).toBe(2);
    expect(kinds[0]).toContain("(A)");
    expect(kinds[1]).toContain("(B)");
    // Phần A lưu theo SỐ CÂU (3 họ từ × 5) để khớp tổng số câu của block.
    const counts = vi.mocked(examApi.addBlockPart).mock.calls.map(([, , part]) => part.question_count);
    expect(counts).toEqual([15, 15]);
  });

  it("ticking Pronunciation creates 1 block with 4 Phần con, stress pinned to its own type", async () => {
    // Đề thật (13/13) ghép trọng âm vào cùng mục "I. PRONUNCIATION" chứ không tách
    // thành mục La Mã riêng — phần con thứ 4 ghi đè dạng bài sang "stress".
    const user = userEvent.setup();
    catalogApi.listExerciseTypes.mockResolvedValue([
      blocks[0]!.exercise_type, wordFormType, pronunciationType, stressType,
    ]);
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Phát âm" }));

    await waitFor(() => expect(examApi.addBlockPart).toHaveBeenCalledTimes(4));
    const parts = vi.mocked(examApi.addBlockPart).mock.calls.map(([, , p]) => p);
    expect(parts.map((p) => p.title)).toEqual(["Đuôi -s/-es", "Đuôi -ed", "Âm trong từ", "Trọng âm"]);
    // Ba phần đầu dùng dạng bài của khối cha, mỗi phần ghim một kiểu phát âm
    expect(parts.slice(0, 3).every((p) => p.exercise_type_id === null)).toBe(true);
    expect(new Set(parts.slice(0, 3).map((p) => p.prompt_override)).size).toBe(3);
    // Phần trọng âm ghi đè dạng bài, không cần ghim kiểu
    expect(parts[3]!.exercise_type_id).toBe("type-stress");
    expect(parts[3]!.prompt_override).toBeNull();
  });

  it("unticking an exercise type deletes every block of that type", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("checkbox", { name: "Trắc nghiệm" }));

    expect(examApi.deleteBlock).toHaveBeenCalledWith("exam-1", "a");
    expect(examApi.deleteBlock).toHaveBeenCalledWith("exam-1", "b");
  });

  it("lets the question count field go empty instead of snapping back to 0 while retyping", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));
    const questionCount = screen.getByLabelText("Số câu");
    await user.clear(questionCount);

    expect(questionCount).toHaveValue(null);
    expect(screen.getByRole("button", { name: "Lưu" })).toBeDisabled();

    await user.type(questionCount, "10");
    expect(questionCount).toHaveValue(10);
    expect(screen.getByRole("button", { name: "Lưu" })).toBeEnabled();
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

  it("edits sub-part counts inside the main block form, with no add/delete UI", async () => {
    // Chốt 24/08/2026: bỏ hẳn khu "Phần con" — mỗi dạng bài đã chia sẵn theo format đề
    // thật, giáo viên chỉ chỉnh số lượng ngay trong form chính.
    const user = userEvent.setup();
    const pronunciationParts = [
      { id: "p1", order_no: 1, title: "Đuôi -s/-es", instruction: null, question_count: 5, prompt_override: "Chỉ dùng kiểu (1) đuôi -s/-es." },
      { id: "p2", order_no: 2, title: "Đuôi -ed", instruction: null, question_count: 5, prompt_override: "Chỉ dùng kiểu (2) đuôi -ed." },
    ];
    const pronunciationBlock = {
      ...blocks[0]!, id: "pron-block", title: "PRONUNCIATION", exercise_type: pronunciationType,
      question_count: 10, parts: pronunciationParts,
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [pronunciationBlock, blocks[1]!] });
    renderBuilder();
    await screen.findByTestId("block-pron-block");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa PRONUNCIATION" }));

    // Không còn thêm/xóa/sửa riêng phần con
    expect(screen.queryByRole("button", { name: "+ Thêm phần con" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lưu phần con" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sửa" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Tiêu đề phần con")).not.toBeInTheDocument();

    // Mỗi phần con là một ô số ngay trong form chính
    expect(screen.getByLabelText(/Đuôi -s\/-es/)).toHaveValue(5);
    expect(screen.getByLabelText(/Đuôi -ed/)).toHaveValue(5);
  });

  it("updates the block question total live while typing a sub-part count", async () => {
    const user = userEvent.setup();
    const parts = [
      { id: "p1", order_no: 1, title: "Đuôi -s/-es", instruction: null, question_count: 5, prompt_override: null },
      { id: "p2", order_no: 2, title: "Đuôi -ed", instruction: null, question_count: 5, prompt_override: null },
    ];
    const block = {
      ...blocks[0]!, id: "pron-block", title: "PRONUNCIATION", exercise_type: pronunciationType,
      question_count: 10, parts,
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [block, blocks[1]!] });
    renderBuilder();
    await screen.findByTestId("block-pron-block");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa PRONUNCIATION" }));
    expect(screen.getByLabelText("Số câu")).toHaveValue(10);

    await user.clear(screen.getByLabelText(/Đuôi -ed/));
    await user.type(screen.getByLabelText(/Đuôi -ed/), "8");

    // 5 + 8 = 13, cập nhật ngay chứ không đợi bấm Lưu
    expect(screen.getByLabelText("Số câu")).toHaveValue(13);
  });

  it("saves changed sub-part counts together with the block", async () => {
    const user = userEvent.setup();
    const parts = [
      { id: "p1", order_no: 1, title: "Đuôi -s/-es", instruction: null, question_count: 5, prompt_override: "kiểu (1)" },
      { id: "p2", order_no: 2, title: "Đuôi -ed", instruction: null, question_count: 5, prompt_override: "kiểu (2)" },
    ];
    const block = {
      ...blocks[0]!, id: "pron-block", title: "PRONUNCIATION", exercise_type: pronunciationType,
      question_count: 10, parts,
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [block, blocks[1]!] });
    renderBuilder();
    await screen.findByTestId("block-pron-block");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa PRONUNCIATION" }));
    await user.clear(screen.getByLabelText(/Đuôi -ed/));
    await user.type(screen.getByLabelText(/Đuôi -ed/), "8");
    await user.click(screen.getByRole("button", { name: "Lưu" }));

    // Chỉ phần đổi mới được gửi đi; tiêu đề/prompt giữ nguyên
    await waitFor(() => expect(examApi.updateBlockPart).toHaveBeenCalledTimes(1));
    expect(examApi.updateBlockPart).toHaveBeenCalledWith("exam-1", "pron-block", "p2", {
      title: "Đuôi -ed",
      instruction: null,
      question_count: 8,
      prompt_override: "kiểu (2)",
    });
  });

  it("word form asks for Số họ từ / Số từ, not số câu (1 họ từ = 5 câu)", async () => {
    // Giáo viên nghĩ theo "bài này ra mấy từ" (chốt 24/08/2026); DB vẫn lưu theo số câu
    // vì block.question_count = tổng question_count các phần con.
    const user = userEvent.setup();
    const partA = {
      id: "part-a", order_no: 1, title: "Part A. Fill in the blanks with the correct form of the words",
      instruction: null, question_count: 15,
      prompt_override: "Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.",
    };
    const partB = {
      id: "part-b", order_no: 2, title: "Part B. Fill in the blanks with the correct form of the word in brackets.",
      instruction: null, question_count: 6,
      prompt_override: "Chỉ dùng kiểu (B) từ gốc trong ngoặc ở cuối câu cho toàn bộ các câu.",
    };
    const wfBlock = {
      ...blocks[0]!, title: "WORD FORMATION", exercise_type: wordFormType,
      question_count: 21, parts: [partA, partB],
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [wfBlock, blocks[1]!] });
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa WORD FORMATION" }));

    // Phần A hiện 3 (họ từ) chứ không phải 15 (câu); Phần B 1 từ = 1 câu
    expect(screen.getByLabelText(/Phần A — Số họ từ/)).toHaveValue(3);
    expect(screen.getByLabelText(/Phần B — Số từ/)).toHaveValue(6);

    await user.clear(screen.getByLabelText(/Phần A — Số họ từ/));
    await user.type(screen.getByLabelText(/Phần A — Số họ từ/), "4");

    // 4 họ từ = 20 câu, tổng khối 20 + 6
    expect(screen.getByLabelText("Số câu")).toHaveValue(26);

    await user.click(screen.getByRole("button", { name: "Lưu" }));
    await waitFor(() =>
      expect(examApi.updateBlockPart).toHaveBeenCalledWith("exam-1", "a", "part-a",
        expect.objectContaining({ question_count: 20 })),
    );
  });

  it("lets the teacher set how many questions each word family gets", async () => {
    // Chốt 24/08/2026: 1 set word form là 5-7 câu do giáo viên đặt, không cố định 5.
    const user = userEvent.setup();
    const partA = {
      id: "part-a", order_no: 1, title: "Part A", instruction: null, question_count: 15,
      prompt_override: "Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.",
    };
    const wfBlock = {
      ...blocks[0]!, title: "WORD FORMATION", exercise_type: wordFormType,
      question_count: 15, parts: [partA],
    };
    examApi.getExam.mockResolvedValue({ ...exam, blocks: [wfBlock, blocks[1]!] });
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa WORD FORMATION" }));
    expect(screen.getByLabelText(/Số câu mỗi họ từ/)).toHaveValue(5);

    await user.clear(screen.getByLabelText(/Số câu mỗi họ từ/));
    await user.type(screen.getByLabelText(/Số câu mỗi họ từ/), "7");

    // Giữ nguyên 3 họ từ -> tổng thành 21 câu
    expect(screen.getByLabelText(/Phần A — Số họ từ/)).toHaveValue(3);
    expect(screen.getByLabelText("Số câu")).toHaveValue(21);

    await user.click(screen.getByRole("button", { name: "Lưu" }));
    await waitFor(() =>
      expect(examApi.updateBlockPart).toHaveBeenCalledWith("exam-1", "a", "part-a",
        expect.objectContaining({
          question_count: 21,
          prompt_override: expect.stringContaining("Mỗi họ từ 7 câu."),
        })),
    );
  });

  it("shows no sub-part section for types without parts", async () => {
    const user = userEvent.setup();
    renderBuilder();
    await screen.findByTestId("block-a");

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa A" }));

    expect(screen.queryByText("Số lượng từng phần")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Số câu")).toBeEnabled();
  });
});

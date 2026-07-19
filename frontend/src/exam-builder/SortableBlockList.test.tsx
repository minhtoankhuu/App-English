import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SortableBlockList } from "./SortableBlockList";
import * as blockOrder from "./blockOrder";
import type { BlockOut } from "../types/exam";

const blocks: BlockOut[] = [
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
  {
    id: "c",
    order_no: 3,
    exercise_type: { id: "type-1", code: "multiple_choice", name: "Trắc nghiệm", has_passage: false },
    title: "C",
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

const onReorder = vi.fn();
const onDelete = vi.fn();
const onUpdateField = vi.fn();

const defaultProps = {
  blocks,
  saving: false,
  onReorder,
  onDelete,
  onUpdateField,
};

describe("SortableBlockList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("reorders with drag and drop", () => {
    render(<SortableBlockList {...defaultProps} />);

    fireEvent.dragStart(screen.getByLabelText("Kéo để sắp xếp A"));
    fireEvent.dragOver(screen.getByTestId("block-c"));
    fireEvent.drop(screen.getByTestId("block-c"));

    expect(onReorder).toHaveBeenCalledWith(["b", "a", "c"]);
  });

  it("keeps arrow controls and disables boundaries", async () => {
    const user = userEvent.setup();
    render(<SortableBlockList {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Lên A" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Xuống C" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Xuống A" }));

    expect(onReorder).toHaveBeenCalledWith(["b", "a", "c"]);
  });

  it("delegates a downward arrow move to the shared block ordering helper", async () => {
    const user = userEvent.setup();
    const moveBlock = vi.spyOn(blockOrder, "moveBlock");
    render(<SortableBlockList {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Xuống A" }));

    expect(moveBlock).toHaveBeenCalledWith(blocks, "b", "a");
    expect(onReorder).toHaveBeenCalledWith(["b", "a", "c"]);
  });

  it("preserves delete and field update callbacks", async () => {
    const user = userEvent.setup();
    render(<SortableBlockList {...defaultProps} />);

    const questionCount = screen.getByLabelText("Số câu A");
    await user.clear(questionCount);
    await user.type(questionCount, "8");
    fireEvent.blur(questionCount);
    await user.click(screen.getByRole("button", { name: "Xóa A" }));

    expect(onUpdateField).toHaveBeenCalledWith(blocks[0], "question_count", 8);
    expect(onDelete).toHaveBeenCalledWith("a");
  });

  it("disables reordering controls while saving", () => {
    render(<SortableBlockList {...defaultProps} saving />);

    expect(screen.getByRole("button", { name: "Kéo để sắp xếp A" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lên B" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Xuống B" })).toBeDisabled();
  });
});

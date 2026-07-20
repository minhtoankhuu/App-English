import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExamPreview } from "./ExamPreview";
import type { ExamPreviewOut } from "../types/examPreview";

const retry = vi.fn();

const emptyPreview: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra",
  grade_number: 7,
  level_code: "A2",
  total_questions: 0,
  total_points: "0.0",
  page_count: 1,
  pages: [{ page_number: 1, blocks: [] }],
};

const twoPagePreview: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra học kỳ",
  grade_number: 9,
  level_code: "B1",
  total_questions: 3,
  total_points: "2.0",
  page_count: 2,
  pages: [
    {
      page_number: 1,
      blocks: [
        {
          block_id: "block-1",
          section_number: 1,
          section_label: "I",
          title: "Đọc hiểu",
          instruction: "Đọc đoạn văn và trả lời câu hỏi.",
          question_start: 1,
          question_end: 2,
          question_count: 2,
          points: "1.0",
          continuation: false,
          questions: [
            {
              question_number: 1,
              prompt_text: "Ý chính của đoạn văn là gì?",
              passage_text: "Đây là đoạn văn dùng chung.",
              is_placeholder: false,
              part_number: null,
              part_title: null,
              part_instruction: null,
            },
            {
              question_number: 2,
              prompt_text: "Tác giả đề cập đến điều gì?",
              passage_text: "Đây là đoạn văn dùng chung.",
              is_placeholder: false,
              part_number: null,
              part_title: null,
              part_instruction: null,
            },
          ],
        },
      ],
    },
    {
      page_number: 2,
      blocks: [
        {
          block_id: "block-2",
          section_number: 2,
          section_label: "II",
          title: "Ngữ pháp",
          instruction: null,
          question_start: 3,
          question_end: 3,
          question_count: 1,
          points: "1.0",
          continuation: false,
          questions: [
            {
              question_number: 3,
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

describe("ExamPreview", () => {
  it("renders loading and retry states", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ExamPreview preview={null} loading error={null} onRetry={retry} />);

    expect(screen.getByText("Đang dựng bản xem trước...")).toBeInTheDocument();

    rerender(<ExamPreview preview={null} loading={false} error="Không tải được" onRetry={retry} />);
    expect(screen.getByText("Không tải được")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("renders an empty preview", () => {
    render(<ExamPreview preview={emptyPreview} loading={false} error={null} onRetry={retry} />);

    const page = screen.getByRole("article", { name: "Trang 1/1" });
    expect(within(page).getByText("ĐỀ KIỂM TRA")).toBeInTheDocument();
    expect(within(page).getByText(/English 7 · Level A2 · Time: 45 minutes/)).toBeInTheDocument();
    expect(within(page).getByText("School: ..........................................")).toBeInTheDocument();
    expect(within(page).getByText("Mark")).toBeInTheDocument();
    expect(within(page).getByText("Thêm phần để xem trước đề")).toBeInTheDocument();
    expect(within(page).getByText("Trang 1/1")).toBeInTheDocument();
  });

  it("renders numbered A4 pages with placeholders", () => {
    render(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);

    expect(screen.getByText("Trang 1/2")).toBeInTheDocument();
    expect(screen.getByText("Trang 2/2")).toBeInTheDocument();
    const firstPage = screen.getByRole("article", { name: "Trang 1/2" });
    expect(firstPage).toHaveClass("paper");
    expect(screen.getByText("Câu 3. ................................................................")).toBeInTheDocument();
  });

  it("renders each block question range and points", () => {
    render(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);

    expect(screen.getByText("Câu 1–2 · 1.0 điểm")).toBeInTheDocument();
    expect(screen.getByText("Câu 3–3 · 1.0 điểm")).toBeInTheDocument();
  });

  it("renders actual questions and shows a repeated passage once per block", () => {
    render(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);

    expect(screen.getByText("Câu 1. Ý chính của đoạn văn là gì?")).toBeInTheDocument();
    expect(screen.getByText("Câu 2. Tác giả đề cập đến điều gì?")).toBeInTheDocument();
    expect(screen.getAllByText("Đây là đoạn văn dùng chung.")).toHaveLength(1);
  });
});

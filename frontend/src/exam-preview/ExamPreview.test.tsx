import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExamPreview } from "./ExamPreview";
import type { ExamPreviewOut } from "../types/examPreview";

const retry = vi.fn();

const emptyPreview: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra",
  total_questions: 0,
  total_points: "0.0",
  page_count: 1,
  pages: [{ page_number: 1, blocks: [] }],
};

const twoPagePreview: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra học kỳ",
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
            },
            {
              question_number: 2,
              prompt_text: "Tác giả đề cập đến điều gì?",
              passage_text: "Đây là đoạn văn dùng chung.",
              is_placeholder: false,
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

    expect(screen.getByText("Thêm phần để xem trước đề")).toBeInTheDocument();
  });

  it("renders numbered A4 pages with placeholders", () => {
    render(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);

    expect(screen.getByText("Trang 1/2")).toBeInTheDocument();
    expect(screen.getByText("Trang 2/2")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Trang 1/2" })).toHaveStyle({ aspectRatio: "210 / 297" });
    expect(screen.getByText("Câu 3. Chưa có nội dung")).toBeInTheDocument();
  });

  it("renders actual questions and shows a repeated passage once per block", () => {
    render(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);

    expect(screen.getByText("Câu 1. Ý chính của đoạn văn là gì?")).toBeInTheDocument();
    expect(screen.getByText("Câu 2. Tác giả đề cập đến điều gì?")).toBeInTheDocument();
    expect(screen.getAllByText("Đây là đoạn văn dùng chung.")).toHaveLength(1);
  });
});

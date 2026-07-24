import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { approveAllQuestions, deleteExam, getExamPreview, listExams } from "../api/exams";
import type { ExamSummaryOut } from "../types/exam";
import type { ExamPreviewOut } from "../types/examPreview";
import { ExamListPage } from "./ExamListPage";

vi.mock("../api/exams", () => ({
  listExams: vi.fn(),
  deleteExam: vi.fn(),
  downloadExportUrl: vi.fn(() => "http://localhost:8000/exams/exam-1/export.docx?variant=A"),
  approveAllQuestions: vi.fn(),
  getExamPreview: vi.fn(),
}));

const draftExam: ExamSummaryOut = {
  id: "exam-1",
  title: "Đề kiểm tra mới",
  status: "draft",
  grade_number: 7,
  level_code: "A1",
  total_questions: 0,
  total_points: "3.0",
  export_mode: null,
  variant_count: 1,
  updated_at: "2026-07-20T04:00:00Z",
};

const draftExamWithQuestions: ExamSummaryOut = { ...draftExam, total_questions: 6 };

const previewData: ExamPreviewOut = {
  exam_id: "exam-1",
  title: "Đề kiểm tra mới",
  total_questions: 0,
  total_points: "3.0",
  page_count: 1,
  pages: [{ page_number: 1, blocks: [] }],
};

function renderList() {
  return render(
    <MemoryRouter>
      <ExamListPage />
    </MemoryRouter>,
  );
}

describe("ExamListPage", () => {
  beforeEach(() => {
    vi.mocked(listExams).mockReset();
    vi.mocked(deleteExam).mockReset();
    vi.mocked(approveAllQuestions).mockReset();
    vi.mocked(getExamPreview).mockReset();
    vi.mocked(getExamPreview).mockResolvedValue(previewData);
    vi.spyOn(window, "confirm").mockReset();
  });

  it("hiển thị danh sách đề", async () => {
    vi.mocked(listExams).mockResolvedValue([draftExam]);

    renderList();

    expect(await screen.findByText("Đề kiểm tra mới")).toBeInTheDocument();
    expect(screen.getByText("Lớp 7 · A1 · 0 câu · 3.0 điểm")).toBeInTheDocument();
  });

  it("xóa đề sau khi xác nhận và tải lại danh sách", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValueOnce([draftExam]).mockResolvedValueOnce([]);
    vi.mocked(deleteExam).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteExam).toHaveBeenCalledWith("exam-1");
    expect(listExams).toHaveBeenCalledTimes(2);
  });

  it("không xóa khi từ chối xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExam]);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(deleteExam).not.toHaveBeenCalled();
  });

  it("hiển thị lỗi khi xóa thất bại", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExam]);
    vi.mocked(deleteExam).mockRejectedValue(new Error("network down"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(await screen.findByText("Không xóa được đề")).toBeInTheDocument();
  });

  it("không hiện nút Duyệt toàn bộ khi đề chưa có câu hỏi", async () => {
    vi.mocked(listExams).mockResolvedValue([draftExam]);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    expect(screen.queryByRole("button", { name: "Duyệt toàn bộ" })).not.toBeInTheDocument();
  });

  it("duyệt toàn bộ sau khi xác nhận và tải lại danh sách", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValueOnce([draftExamWithQuestions]).mockResolvedValueOnce([]);
    vi.mocked(approveAllQuestions).mockResolvedValue({} as never);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Duyệt toàn bộ" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(approveAllQuestions).toHaveBeenCalledWith("exam-1");
    expect(listExams).toHaveBeenCalledTimes(2);
  });

  it("không duyệt toàn bộ khi từ chối xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExamWithQuestions]);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Duyệt toàn bộ" }));

    expect(approveAllQuestions).not.toHaveBeenCalled();
  });

  it("hiển thị lỗi khi duyệt toàn bộ thất bại", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExamWithQuestions]);
    vi.mocked(approveAllQuestions).mockRejectedValue(new Error("network down"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Duyệt toàn bộ" }));

    expect(await screen.findByText("Không duyệt được đề")).toBeInTheDocument();
  });

  it("mở modal xem trước A4 và gọi đúng API", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExam]);

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Xem A4" }));

    expect(getExamPreview).toHaveBeenCalledWith("exam-1");
    expect(await screen.findByText("Xem trước A4 — Đề kiểm tra mới")).toBeInTheDocument();
  });

  it("hiển thị lỗi trong modal khi xem trước A4 thất bại", async () => {
    const user = userEvent.setup();
    vi.mocked(listExams).mockResolvedValue([draftExam]);
    vi.mocked(getExamPreview).mockRejectedValue(new Error("network down"));

    renderList();
    await screen.findByText("Đề kiểm tra mới");

    await user.click(screen.getByRole("button", { name: "Xem A4" }));

    expect(await screen.findByText("Không dựng được bản xem trước")).toBeInTheDocument();
  });
});

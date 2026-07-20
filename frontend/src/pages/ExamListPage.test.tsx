import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { deleteExam, listExams } from "../api/exams";
import type { ExamSummaryOut } from "../types/exam";
import { ExamListPage } from "./ExamListPage";

vi.mock("../api/exams", () => ({
  listExams: vi.fn(),
  deleteExam: vi.fn(),
  downloadExportUrl: vi.fn(() => "http://localhost:8000/exams/exam-1/export.docx?variant=A"),
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
});

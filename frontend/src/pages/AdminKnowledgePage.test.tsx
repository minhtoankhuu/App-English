import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  updateKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../api/admin";
import { listGrades, listUnitsForGrade } from "../api/catalog";
import type { KnowledgeDocumentOut } from "../types/admin";
import { AdminKnowledgePage } from "./AdminKnowledgePage";

vi.mock("../api/admin", () => ({
  listKnowledgeDocuments: vi.fn(),
  uploadKnowledgeDocument: vi.fn(),
  updateKnowledgeDocument: vi.fn(),
  deleteKnowledgeDocument: vi.fn(),
}));

vi.mock("../api/catalog", () => ({
  listGrades: vi.fn(),
  listUnitsForGrade: vi.fn(),
}));

const document1: KnowledgeDocumentOut = {
  id: "doc-1",
  file_name: "GS7 - UNIT 3 - LESSON.docx",
  is_published: true,
  chunk_count: 24,
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:00Z",
  unit: { id: "unit-3", order_no: 3, title: "Community Service", grade_number: 7 },
};

describe("AdminKnowledgePage", () => {
  beforeEach(() => {
    vi.mocked(listKnowledgeDocuments).mockReset();
    vi.mocked(uploadKnowledgeDocument).mockReset();
    vi.mocked(updateKnowledgeDocument).mockReset();
    vi.mocked(deleteKnowledgeDocument).mockReset();
    vi.mocked(listGrades).mockReset();
    vi.mocked(listUnitsForGrade).mockReset();
    vi.mocked(listGrades).mockResolvedValue([
      { id: "grade-7", number: 7, school_stage: { id: "s1", code: "secondary", name: "THCS", order_no: 2 }, suggested_level: { id: "level-a2", code: "A2", rank: 2 } },
    ]);
    vi.mocked(listUnitsForGrade).mockResolvedValue([{ id: "unit-3", order_no: 3, title: "Community Service" }]);
    vi.spyOn(window, "confirm").mockReset();
  });

  it("hiển thị danh sách tài liệu", async () => {
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);

    render(<AdminKnowledgePage />);

    expect(await screen.findByText("GS7 - UNIT 3 - LESSON.docx")).toBeInTheDocument();
    expect(screen.getByText("Lớp 7 · Unit 3 — Community Service")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("Đã xuất bản")).toBeInTheDocument();
  });

  it("hiển thị trạng thái rỗng khi chưa có tài liệu", async () => {
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);

    render(<AdminKnowledgePage />);

    expect(await screen.findByText("Chưa có tài liệu nào.")).toBeInTheDocument();
  });

  it("mở popup nhập tài liệu và upload thành công", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue(document1);

    render(<AdminKnowledgePage />);
    await screen.findByText("Chưa có tài liệu nào.");

    await user.click(screen.getByRole("button", { name: "+ Nhập tài liệu" }));
    await screen.findByRole("option", { name: "Unit 3 — Community Service" });

    const file = new File(["nội dung"], "GS7 - UNIT 3 - LESSON.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const fileInput = screen.getByLabelText("File tài liệu (.docx)");
    await user.upload(fileInput, file);

    await user.click(screen.getByRole("button", { name: "Nhập tài liệu" }));

    expect(uploadKnowledgeDocument).toHaveBeenCalledWith("unit-3", file);
    expect(listKnowledgeDocuments).toHaveBeenCalledTimes(2);
  });

  it("ẩn/xuất bản tài liệu", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.mocked(updateKnowledgeDocument).mockResolvedValue({ ...document1, is_published: false });

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Ẩn" }));

    expect(updateKnowledgeDocument).toHaveBeenCalledWith("doc-1", false);
  });

  it("xóa tài liệu sau khi xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.mocked(deleteKnowledgeDocument).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteKnowledgeDocument).toHaveBeenCalledWith("doc-1");
  });

  it("không xóa khi từ chối xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(deleteKnowledgeDocument).not.toHaveBeenCalled();
  });

  it("hiển thị lỗi khi tải danh sách thất bại", async () => {
    vi.mocked(listKnowledgeDocuments).mockRejectedValue(new Error("network down"));

    render(<AdminKnowledgePage />);

    expect(await screen.findByText("Không tải được danh sách tài liệu")).toBeInTheDocument();
  });
});

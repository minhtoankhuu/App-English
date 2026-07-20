import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocumentChunks,
  listKnowledgeDocuments,
  updateKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../api/admin";
import { listGrades, listGrammarTopics, listUnitsForGrade } from "../api/catalog";
import type { KnowledgeDocumentOut } from "../types/admin";
import type { GrammarTopicOut } from "../types/catalog";
import { AdminKnowledgePage } from "./AdminKnowledgePage";

vi.mock("../api/admin", () => ({
  listKnowledgeDocuments: vi.fn(),
  uploadKnowledgeDocument: vi.fn(),
  updateKnowledgeDocument: vi.fn(),
  deleteKnowledgeDocument: vi.fn(),
  listKnowledgeDocumentChunks: vi.fn(),
}));

vi.mock("../api/catalog", () => ({
  listGrades: vi.fn(),
  listUnitsForGrade: vi.fn(),
  listGrammarTopics: vi.fn(),
}));

const document1: KnowledgeDocumentOut = {
  id: "doc-1",
  file_name: "GS7 - UNIT 3 - LESSON.docx",
  is_published: true,
  chunk_count: 24,
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:00Z",
  unit: { id: "unit-3", order_no: 3, title: "Community Service", grade_number: 7 },
  grammar_point: null,
};

const document2: KnowledgeDocumentOut = {
  id: "doc-2",
  file_name: "GS8 - UNIT 1 - LESSON.docx",
  is_published: true,
  chunk_count: 40,
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:00Z",
  unit: { id: "unit-8-1", order_no: 1, title: "Leisure Time", grade_number: 8 },
  grammar_point: null,
};

const grammarDocument: KnowledgeDocumentOut = {
  id: "doc-3",
  file_name: "present-simple.docx",
  is_published: true,
  chunk_count: 6,
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:00Z",
  unit: null,
  grammar_point: { id: "point-1", name: "Present Simple", group_name: "Hiện tại", topic_name: "Tense" },
};

const tenseTopic: GrammarTopicOut = {
  id: "topic-1",
  code: "tense",
  name: "Tense — 12 thì tiếng Anh",
  groups: [
    {
      id: "group-1",
      name: "Hiện tại",
      order_no: 1,
      points: [{ id: "point-1", name: "Present Simple", order_no: 1, min_level: { id: "level-a1", code: "A1", rank: 1 } }],
    },
  ],
};

describe("AdminKnowledgePage", () => {
  beforeEach(() => {
    vi.mocked(listKnowledgeDocuments).mockReset();
    vi.mocked(uploadKnowledgeDocument).mockReset();
    vi.mocked(updateKnowledgeDocument).mockReset();
    vi.mocked(deleteKnowledgeDocument).mockReset();
    vi.mocked(listKnowledgeDocumentChunks).mockReset();
    vi.mocked(listGrades).mockReset();
    vi.mocked(listUnitsForGrade).mockReset();
    vi.mocked(listGrammarTopics).mockReset();
    vi.mocked(listGrades).mockResolvedValue([
      { id: "grade-7", number: 7, school_stage: { id: "s1", code: "secondary", name: "THCS", order_no: 2 }, suggested_level: { id: "level-a2", code: "A2", rank: 2 } },
    ]);
    vi.mocked(listUnitsForGrade).mockResolvedValue([{ id: "unit-3", order_no: 3, title: "Community Service" }]);
    vi.mocked(listGrammarTopics).mockResolvedValue([tenseTopic]);
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

    expect(uploadKnowledgeDocument).toHaveBeenCalledWith({ unitId: "unit-3" }, file);
    expect(listKnowledgeDocuments).toHaveBeenCalledTimes(2);
  });

  it("nhập tài liệu ngữ pháp theo GrammarPoint", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue(grammarDocument);

    render(<AdminKnowledgePage />);
    await screen.findByText("Chưa có tài liệu nào.");

    await user.click(screen.getByRole("button", { name: "+ Nhập tài liệu" }));
    await user.selectOptions(screen.getByLabelText("Loại nguồn"), "Kiến thức chung (ngữ pháp)");
    await screen.findByRole("option", { name: "Present Simple" });

    const file = new File(["nội dung"], "present-simple.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await user.upload(screen.getByLabelText("File tài liệu (.docx)"), file);
    await user.click(screen.getByRole("button", { name: "Nhập tài liệu" }));

    expect(uploadKnowledgeDocument).toHaveBeenCalledWith({ grammarPointId: "point-1" }, file);
  });

  it("hiển thị nguồn Kiến thức chung và lọc theo loại nguồn", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1, grammarDocument]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    expect(screen.getByText(/Kiến thức chung · Present Simple/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Lọc theo loại nguồn"), "Global Success (theo Unit)");

    expect(screen.queryByText("present-simple.docx")).not.toBeInTheDocument();
    expect(screen.getByText("GS7 - UNIT 3 - LESSON.docx")).toBeInTheDocument();
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

  it("lọc danh sách theo khối lớp", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1, document2]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");
    expect(screen.getByText("GS8 - UNIT 1 - LESSON.docx")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Lọc theo khối lớp"), "Lớp 8");

    expect(screen.queryByText("GS7 - UNIT 3 - LESSON.docx")).not.toBeInTheDocument();
    expect(screen.getByText("GS8 - UNIT 1 - LESSON.docx")).toBeInTheDocument();
  });

  it("xem nội dung đoạn của tài liệu", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.mocked(listKnowledgeDocumentChunks).mockResolvedValue([
      {
        id: "chunk-1",
        order_no: 1,
        chunk_type: "vocabulary",
        section_title: "VOCABULARY",
        raw_text: "volunteer /ˈvɒləntɪə/ (n): a person who helps others without being paid",
        structured: null,
      },
    ]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Xem" }));

    expect(listKnowledgeDocumentChunks).toHaveBeenCalledWith("doc-1");
    expect(await screen.findByText(/volunteer/)).toBeInTheDocument();
    expect(screen.getByText("Từ vựng")).toBeInTheDocument();
  });

  it("hiển thị đoạn có bảng dưới dạng bảng thật thay vì gộp dấu |", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.mocked(listKnowledgeDocumentChunks).mockResolvedValue([
      {
        id: "chunk-table",
        order_no: 1,
        chunk_type: "grammar",
        section_title: "GRAMMAR AND STRUCTURES",
        raw_text: "Positive | Comparative\ngood | better",
        structured: { table: [["Positive", "Comparative"], ["good", "better"]] },
      },
    ]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Xem" }));

    const cell = await screen.findByRole("cell", { name: "Comparative" });
    expect(cell).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "good" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "better" })).toBeInTheDocument();
    expect(screen.queryByText("Positive | Comparative")).not.toBeInTheDocument();
  });

  it("mặc định sắp xếp theo Khối / Unit tăng dần", async () => {
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document2, document1]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    const rows = screen.getAllByRole("row");
    expect(within(rows[1]!).getByText("GS7 - UNIT 3 - LESSON.docx")).toBeInTheDocument();
    expect(within(rows[2]!).getByText("GS8 - UNIT 1 - LESSON.docx")).toBeInTheDocument();
  });

  it("đảo chiều sắp xếp khi bấm lại cùng cột", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1, document2]);

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: /Số đoạn/ }));
    await user.click(screen.getByRole("button", { name: /Số đoạn/ }));

    const rows = screen.getAllByRole("row");
    expect(within(rows[1]!).getByText("GS8 - UNIT 1 - LESSON.docx")).toBeInTheDocument();
    expect(within(rows[2]!).getByText("GS7 - UNIT 3 - LESSON.docx")).toBeInTheDocument();
  });

  it("hiển thị lỗi khi tải nội dung đoạn thất bại", async () => {
    const user = userEvent.setup();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([document1]);
    vi.mocked(listKnowledgeDocumentChunks).mockRejectedValue(new Error("network down"));

    render(<AdminKnowledgePage />);
    await screen.findByText("GS7 - UNIT 3 - LESSON.docx");

    await user.click(screen.getByRole("button", { name: "Xem" }));

    expect(await screen.findByText("Không tải được nội dung tài liệu")).toBeInTheDocument();
  });
});

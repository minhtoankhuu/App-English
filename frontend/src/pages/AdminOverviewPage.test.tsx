import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listKnowledgeDocuments, listTeachers } from "../api/admin";
import type { KnowledgeDocumentOut, TeacherOut } from "../types/admin";
import { AdminOverviewPage } from "./AdminOverviewPage";

vi.mock("../api/admin", () => ({
  listTeachers: vi.fn(),
  listKnowledgeDocuments: vi.fn(),
}));

const knowledgeDocuments: KnowledgeDocumentOut[] = [
  {
    id: "doc-1",
    file_name: "GS7 - UNIT 3 - LESSON.docx",
    is_published: true,
    chunk_count: 12,
    created_at: "2026-07-20T00:00:00Z",
    updated_at: "2026-07-20T00:00:00Z",
    unit: { id: "unit-3", order_no: 3, title: "Community Service", grade_number: 7 },
  },
];

const teachers: TeacherOut[] = [
  {
    id: "teacher-1",
    email: "one@example.com",
    full_name: "Teacher One",
    is_active: true,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    id: "teacher-2",
    email: "two@example.com",
    full_name: "Teacher Two",
    is_active: false,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    id: "teacher-3",
    email: "three@example.com",
    full_name: "Teacher Three",
    is_active: true,
    created_at: "2026-07-19T00:00:00Z",
  },
];

function renderPage() {
  render(
    <MemoryRouter>
      <AdminOverviewPage />
    </MemoryRouter>,
  );
}

describe("AdminOverviewPage", () => {
  beforeEach(() => {
    vi.mocked(listTeachers).mockReset();
    vi.mocked(listKnowledgeDocuments).mockReset();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
  });

  it("hiển thị trạng thái đang tải", () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getAllByText("Đang tải...").length).toBeGreaterThan(0);
  });

  it("hiển thị số giáo viên hoạt động", async () => {
    vi.mocked(listTeachers).mockResolvedValue(teachers);

    renderPage();

    expect(await screen.findByText("2 giáo viên hoạt động")).toBeInTheDocument();
  });

  it("hiển thị số tài liệu kho kiến thức đã xuất bản", async () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));
    vi.mocked(listKnowledgeDocuments).mockResolvedValue(knowledgeDocuments);

    renderPage();

    expect(await screen.findByText("1 tài liệu đã xuất bản")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kho kiến thức & RAG/ })).toHaveAttribute("href", "/admin/knowledge");
  });

  it("hiển thị lỗi thống kê mà không khóa liên kết tài khoản", async () => {
    vi.mocked(listTeachers).mockRejectedValue(new Error("network error"));

    renderPage();

    expect(await screen.findByText("Không tải được dữ liệu")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Tài khoản & phân quyền/ })).toHaveAttribute(
      "href",
      "/admin/teachers",
    );
  });

  it("không biến phân hệ chưa triển khai thành liên kết", () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getAllByRole("link")).toHaveLength(3);
    expect(screen.queryByRole("link", { name: /Dạng bài & template chuẩn/ })).not.toBeInTheDocument();
  });

  it("mở audit log từ dashboard", () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByText("3 khối bên dưới đã có chức năng thật.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Audit log/ })).toHaveAttribute("href", "/admin/audit-logs");
  });
});

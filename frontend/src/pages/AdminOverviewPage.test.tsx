import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getAIConfig, listKnowledgeDocuments, listTeachers } from "../api/admin";
import { listAuditLogs } from "../api/audit";
import type { AuditLogPage } from "../types/audit";
import type { AIProviderConfigOut, KnowledgeDocumentOut, TeacherOut } from "../types/admin";
import { AdminOverviewPage } from "./AdminOverviewPage";

vi.mock("../api/admin", () => ({
  listTeachers: vi.fn(),
  listKnowledgeDocuments: vi.fn(),
  getAIConfig: vi.fn(),
}));

vi.mock("../api/audit", () => ({
  listAuditLogs: vi.fn(),
}));

const teachers: TeacherOut[] = [
  { id: "teacher-1", email: "one@example.com", full_name: "Teacher One", is_active: true, created_at: "2026-07-19T00:00:00Z" },
  { id: "teacher-2", email: "two@example.com", full_name: "Teacher Two", is_active: false, created_at: "2026-07-19T00:00:00Z" },
];

const knowledgeDocuments: KnowledgeDocumentOut[] = [
  {
    id: "doc-1",
    file_name: "GS7 - UNIT 3 - LESSON.docx",
    is_published: true,
    chunk_count: 12,
    created_at: "2026-07-20T00:00:00Z",
    updated_at: "2026-07-20T00:00:00Z",
    unit: { id: "unit-3", order_no: 3, title: "Community Service", grade_number: 7 },
    grammar_point: null,
  },
];

const emptyAuditPage: AuditLogPage = { items: [], total: 0, limit: 5, offset: 0 };

const aiConfig: AIProviderConfigOut = {
  id: "config-1",
  provider: "openai",
  model: "gpt-4o-mini",
  embedding_model: "text-embedding-3-small",
  temperature: 0.7,
  duplicate_similarity_threshold: 0.9,
  is_active: true,
  api_key_masked: "sk-...ab12",
  updated_at: "2026-07-21T00:00:00Z",
};

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
    vi.mocked(getAIConfig).mockReset();
    vi.mocked(listAuditLogs).mockReset();
    vi.mocked(listAuditLogs).mockResolvedValue(emptyAuditPage);
    vi.mocked(getAIConfig).mockResolvedValue(null);
  });

  it("hiển thị trạng thái đang tải", () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));
    vi.mocked(listKnowledgeDocuments).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getAllByText("Đang tải...").length).toBeGreaterThan(0);
  });

  it("hiển thị số giáo viên hoạt động", async () => {
    vi.mocked(listTeachers).mockResolvedValue(teachers);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("1 giáo viên")).toBeInTheDocument();
  });

  it("hiển thị số tài liệu kho kiến thức đã xuất bản", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue(knowledgeDocuments);

    renderPage();

    expect(await screen.findByText("1 tài liệu")).toBeInTheDocument();
  });

  it("hiển thị lỗi thống kê riêng biệt mà không chặn phần còn lại", async () => {
    vi.mocked(listTeachers).mockRejectedValue(new Error("network error"));
    vi.mocked(listKnowledgeDocuments).mockResolvedValue(knowledgeDocuments);

    renderPage();

    expect(await screen.findByText("Không tải được dữ liệu")).toBeInTheDocument();
    expect(await screen.findByText("1 tài liệu")).toBeInTheDocument();
  });

  it("hiển thị hoạt động gần đây và liên kết xem tất cả", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
    vi.mocked(listAuditLogs).mockResolvedValue({
      items: [
        {
          id: "log-1",
          created_at: "2026-07-20T04:00:00Z",
          actor_user_id: "admin-1",
          actor_email: "admin@examcraft.dev",
          action: "teacher.created",
          target_type: "teacher",
          target_id: "teacher-1",
          target_label: "Teacher One",
          details: {},
        },
      ],
      total: 1,
      limit: 5,
      offset: 0,
    });

    renderPage();

    expect(await screen.findByText(/Tạo giáo viên/)).toBeInTheDocument();
    expect(screen.getByText(/admin@examcraft.dev/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Xem tất cả" })).toHaveAttribute("href", "/admin/audit-logs");
  });

  it("hiển thị trạng thái rỗng khi chưa có hoạt động", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("Chưa có hoạt động nào.")).toBeInTheDocument();
  });

  it("hiển thị danh sách phân hệ sắp triển khai", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("Danh mục học thuật")).toBeInTheDocument();
    expect(screen.getByText("Dạng bài & template chuẩn")).toBeInTheDocument();
  });

  it("hiển thị model AI đang dùng và liên kết tới trang cấu hình", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
    vi.mocked(getAIConfig).mockResolvedValue(aiConfig);

    renderPage();

    expect(await screen.findByText("gpt-4o-mini")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Cấu hình AI \(OpenAI\)/ })).toHaveAttribute("href", "/admin/ai-config");
  });

  it("hiển thị 'Chưa cấu hình' khi chưa thiết lập AI", async () => {
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(listKnowledgeDocuments).mockResolvedValue([]);
    vi.mocked(getAIConfig).mockResolvedValue(null);

    renderPage();

    expect(await screen.findByText("Chưa cấu hình")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listTeachers } from "../api/admin";
import type { TeacherOut } from "../types/admin";
import { AdminOverviewPage } from "./AdminOverviewPage";

vi.mock("../api/admin", () => ({
  listTeachers: vi.fn(),
}));

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
  });

  it("hiển thị trạng thái đang tải", () => {
    vi.mocked(listTeachers).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
  });

  it("hiển thị số giáo viên hoạt động", async () => {
    vi.mocked(listTeachers).mockResolvedValue(teachers);

    renderPage();

    expect(await screen.findByText("2 giáo viên hoạt động")).toBeInTheDocument();
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

    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.queryByRole("link", { name: /Kho kiến thức & RAG/ })).not.toBeInTheDocument();
  });
});

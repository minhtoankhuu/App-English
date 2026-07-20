import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { fetchCurrentUser } from "./api/auth";
import { adminUser, teacherUser } from "./test/fixtures";

vi.mock("./api/auth", () => ({
  fetchCurrentUser: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("./pages/ExamListPage", () => ({
  ExamListPage: () => <h2>Đề của tôi</h2>,
}));

vi.mock("./pages/ExamCreatePage", () => ({
  ExamCreatePage: () => <h2>Tạo đề mới</h2>,
}));

vi.mock("./pages/ExamBuilderPage", () => ({
  ExamBuilderPage: () => <h2>Trình dựng đề</h2>,
}));

vi.mock("./pages/ExamReviewPage", () => ({
  ExamReviewPage: () => <h2>Duyệt câu hỏi</h2>,
}));

vi.mock("./pages/ExamExportPage", () => ({
  ExamExportPage: () => <h2>Xuất đề</h2>,
}));

vi.mock("./pages/AdminOverviewPage", () => ({
  AdminOverviewPage: () => <h2>Quản trị hệ thống</h2>,
}));

vi.mock("./pages/AdminAuditLogsPage", () => ({
  AdminAuditLogsPage: () => <h2>Audit log quản trị</h2>,
}));

describe("App admin routes", () => {
  beforeEach(() => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(teacherUser);
    window.history.replaceState({}, "", "/admin");
  });

  it("chuyển giáo viên khỏi dashboard quản trị", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Đề của tôi" })).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/exams"));
    expect(screen.queryByRole("heading", { name: "Quản trị hệ thống" })).not.toBeInTheDocument();
  });

  it.each([
    "/",
    "/exams",
    "/exams/new",
    "/exams/exam-1/builder",
    "/exams/exam-1/review",
    "/exams/exam-1/export",
    "/khong-ton-tai",
  ])("chuyển Admin từ %s về dashboard", async (path) => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(adminUser);
    window.history.replaceState({}, "", path);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Quản trị hệ thống" })).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/admin"));
    expect(screen.queryByRole("heading", { name: "Đề của tôi" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Tạo đề mới" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Trình dựng đề" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Duyệt câu hỏi" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Xuất đề" })).not.toBeInTheDocument();
  });

  it("cho Admin mở audit log", async () => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(adminUser);
    window.history.replaceState({}, "", "/admin/audit-logs");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Audit log quản trị" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/admin/audit-logs");
  });

  it("chuyển giáo viên khỏi audit log", async () => {
    window.history.replaceState({}, "", "/admin/audit-logs");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Đề của tôi" })).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/exams"));
  });
});

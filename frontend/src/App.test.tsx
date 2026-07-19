import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { fetchCurrentUser } from "./api/auth";
import { teacherUser } from "./test/fixtures";

vi.mock("./api/auth", () => ({
  fetchCurrentUser: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("./pages/ExamListPage", () => ({
  ExamListPage: () => <h2>Đề của tôi</h2>,
}));

vi.mock("./pages/AdminOverviewPage", () => ({
  AdminOverviewPage: () => <h2>Quản trị hệ thống</h2>,
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
});

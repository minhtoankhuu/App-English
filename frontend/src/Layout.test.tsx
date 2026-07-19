import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";
import { adminUser, teacherUser } from "./test/fixtures";
import { getMyUsage } from "./api/usage";

vi.mock("./api/usage", () => ({ getMyUsage: vi.fn() }));

const mockedGetMyUsage = vi.mocked(getMyUsage);

function renderLayout(user = adminUser) {
  render(
    <MemoryRouter initialEntries={["/exams"]}>
      <Routes>
        <Route element={<Layout user={user} onLogout={vi.fn()} />}>
          <Route path="/exams" element={<p>Danh sách đề</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  beforeEach(() => {
    mockedGetMyUsage.mockReset();
    mockedGetMyUsage.mockResolvedValue({
      limit: 10,
      used: 3,
      remaining: 7,
      usage_date: "2026-07-19",
      reset_at: "2026-07-20T00:00:00+07:00",
      is_unlimited: false,
    });
  });

  it("hiển thị liên kết quản trị cho Admin", () => {
    renderLayout();

    expect(screen.getByRole("link", { name: "Quản trị" })).toHaveAttribute("href", "/admin");
  });

  it("không hiển thị liên kết quản trị cho giáo viên", () => {
    renderLayout(teacherUser);

    expect(screen.queryByRole("link", { name: "Quản trị" })).not.toBeInTheDocument();
  });

  it("hiển thị số lượt còn lại cho giáo viên", async () => {
    renderLayout(teacherUser);

    expect(await screen.findByText("Còn 7/10 lượt hôm nay")).toBeInTheDocument();
  });

  it("không tải hoặc hiển thị hạn mức cho Admin", () => {
    renderLayout(adminUser);

    expect(mockedGetMyUsage).not.toHaveBeenCalled();
    expect(screen.queryByText(/lượt hôm nay/)).not.toBeInTheDocument();
  });
});

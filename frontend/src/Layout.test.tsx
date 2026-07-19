import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";
import { adminUser, teacherUser } from "./test/fixtures";

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
  it("hiển thị liên kết quản trị cho Admin", () => {
    renderLayout();

    expect(screen.getByRole("link", { name: "Quản trị" })).toHaveAttribute("href", "/admin");
  });

  it("không hiển thị liên kết quản trị cho giáo viên", () => {
    renderLayout(teacherUser);

    expect(screen.queryByRole("link", { name: "Quản trị" })).not.toBeInTheDocument();
  });
});

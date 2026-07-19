import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createTeacher, deleteTeacher, listTeachers, updateTeacher } from "../api/admin";
import type { TeacherOut } from "../types/admin";
import { AdminTeachersPage } from "./AdminTeachersPage";

vi.mock("../api/admin", () => ({
  listTeachers: vi.fn(),
  createTeacher: vi.fn(),
  updateTeacher: vi.fn(),
  deleteTeacher: vi.fn(),
}));

const teacher: TeacherOut = {
  id: "teacher-1",
  email: "teacher@examcraft.dev",
  full_name: "Nguyen An",
  is_active: true,
  created_at: "2026-07-19T04:00:00Z",
};

describe("AdminTeachersPage", () => {
  beforeEach(() => {
    vi.mocked(listTeachers).mockReset();
    vi.mocked(createTeacher).mockReset();
    vi.mocked(updateTeacher).mockReset();
    vi.mocked(deleteTeacher).mockReset();
    vi.spyOn(window, "confirm").mockReset();
  });

  it("hiển thị danh sách giáo viên dạng bảng", async () => {
    vi.mocked(listTeachers).mockResolvedValue([teacher]);

    render(<AdminTeachersPage />);

    expect(await screen.findByRole("cell", { name: "Nguyen An" })).toBeInTheDocument();
    expect(screen.getByText("teacher@examcraft.dev")).toBeInTheDocument();
    expect(screen.getByText("Đang hoạt động")).toBeInTheDocument();
  });

  it("mở popup thêm tài khoản và tạo thành công", async () => {
    const user = userEvent.setup();
    vi.mocked(listTeachers).mockResolvedValue([]);
    vi.mocked(createTeacher).mockResolvedValue({ ...teacher, id: "teacher-2" });

    render(<AdminTeachersPage />);
    await screen.findByText("Chưa có giáo viên nào.");

    await user.click(screen.getByRole("button", { name: "+ Thêm tài khoản" }));
    expect(screen.getByRole("heading", { name: "Thêm tài khoản giáo viên" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Email"), "new@examcraft.dev");
    await user.type(screen.getByLabelText("Họ tên"), "Người Mới");
    await user.type(screen.getByLabelText("Mật khẩu"), "Secret123!");
    await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

    expect(createTeacher).toHaveBeenCalledWith({
      email: "new@examcraft.dev",
      full_name: "Người Mới",
      password: "Secret123!",
    });
  });

  it("mở popup chỉnh sửa và cập nhật họ tên", async () => {
    const user = userEvent.setup();
    vi.mocked(listTeachers).mockResolvedValue([teacher]);
    vi.mocked(updateTeacher).mockResolvedValue({ ...teacher, full_name: "Tên Mới" });

    render(<AdminTeachersPage />);
    await screen.findByRole("cell", { name: "Nguyen An" });

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
    const nameInput = screen.getByLabelText("Họ tên");
    expect(nameInput).toHaveValue("Nguyen An");
    await user.clear(nameInput);
    await user.type(nameInput, "Tên Mới");
    await user.click(screen.getByRole("button", { name: "Lưu" }));

    expect(updateTeacher).toHaveBeenCalledWith("teacher-1", { full_name: "Tên Mới" });
  });

  it("xóa tài khoản sau khi xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listTeachers).mockResolvedValue([teacher]);
    vi.mocked(deleteTeacher).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<AdminTeachersPage />);
    await screen.findByRole("cell", { name: "Nguyen An" });

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteTeacher).toHaveBeenCalledWith("teacher-1");
  });

  it("không xóa khi từ chối xác nhận", async () => {
    const user = userEvent.setup();
    vi.mocked(listTeachers).mockResolvedValue([teacher]);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<AdminTeachersPage />);
    await screen.findByRole("cell", { name: "Nguyen An" });

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(deleteTeacher).not.toHaveBeenCalled();
  });

  it("hiển thị lỗi 409 khi xóa giáo viên còn đề thi", async () => {
    const user = userEvent.setup();
    vi.mocked(listTeachers).mockResolvedValue([teacher]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { ApiError } = await import("../api/client");
    vi.mocked(deleteTeacher).mockRejectedValue(new ApiError(409, "Giáo viên còn 1 đề thi — khóa tài khoản thay vì xóa."));

    render(<AdminTeachersPage />);
    await screen.findByRole("cell", { name: "Nguyen An" });

    await user.click(screen.getByRole("button", { name: "Xóa" }));

    expect(await screen.findByText("Giáo viên còn 1 đề thi — khóa tài khoản thay vì xóa.")).toBeInTheDocument();
  });
});

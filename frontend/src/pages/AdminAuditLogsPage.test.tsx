import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listAuditLogs } from "../api/audit";
import type { AuditLogOut, AuditLogPage } from "../types/audit";
import { AdminAuditLogsPage } from "./AdminAuditLogsPage";

vi.mock("../api/audit", () => ({
  listAuditLogs: vi.fn(),
}));

const auditItem: AuditLogOut = {
  id: "log-1",
  created_at: "2026-07-19T04:00:00Z",
  actor_user_id: "admin-1",
  actor_email: "admin@examcraft.dev",
  action: "teacher.updated",
  target_type: "teacher",
  target_id: "teacher-1",
  target_label: "teacher@examcraft.dev",
  details: { changed_fields: ["full_name"] },
};

function page(items: AuditLogOut[], total = items.length, offset = 0): AuditLogPage {
  return { items, total, limit: 20, offset };
}

describe("AdminAuditLogsPage", () => {
  beforeEach(() => {
    vi.mocked(listAuditLogs).mockReset();
  });

  it("hiển thị trạng thái đang tải", () => {
    vi.mocked(listAuditLogs).mockReturnValue(new Promise(() => undefined));

    render(<AdminAuditLogsPage />);

    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
  });

  it("hiển thị danh sách audit và metadata an toàn", async () => {
    vi.mocked(listAuditLogs).mockResolvedValue(page([auditItem]));

    render(<AdminAuditLogsPage />);

    expect(await screen.findByText("admin@examcraft.dev")).toBeInTheDocument();
    expect(screen.getByText("teacher@examcraft.dev")).toBeInTheDocument();
    expect(screen.getByText("Cập nhật giáo viên")).toBeInTheDocument();
    expect(screen.getByText("Thay đổi: họ tên")).toBeInTheDocument();
  });

  it("hiển thị trạng thái rỗng", async () => {
    vi.mocked(listAuditLogs).mockResolvedValue(page([]));

    render(<AdminAuditLogsPage />);

    expect(await screen.findByText("Chưa có hoạt động nào.")).toBeInTheDocument();
  });

  it("hiển thị lỗi tải", async () => {
    vi.mocked(listAuditLogs).mockRejectedValue(new Error("network"));

    render(<AdminAuditLogsPage />);

    expect(await screen.findByText("Không tải được audit log")).toBeInTheDocument();
  });

  it("chuyển trang bằng offset và khóa nút ở biên", async () => {
    const user = userEvent.setup();
    vi.mocked(listAuditLogs)
      .mockResolvedValueOnce(page([auditItem], 21, 0))
      .mockResolvedValueOnce(page([{ ...auditItem, id: "log-2" }], 21, 20));

    render(<AdminAuditLogsPage />);

    const previous = await screen.findByRole("button", { name: "Trang trước" });
    const next = screen.getByRole("button", { name: "Trang sau" });
    expect(previous).toBeDisabled();
    expect(next).toBeEnabled();

    await user.click(next);

    expect(listAuditLogs).toHaveBeenLastCalledWith(20, 20);
    expect(await screen.findByText("Trang 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trang sau" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Trang trước" })).toBeEnabled();
  });
});

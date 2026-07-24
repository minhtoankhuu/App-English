import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getAIConfig, testAIConfig, updateAIConfig } from "../api/admin";
import type { AIProviderConfigOut } from "../types/admin";
import { AdminAIConfigPage } from "./AdminAIConfigPage";

vi.mock("../api/admin", () => ({
  getAIConfig: vi.fn(),
  updateAIConfig: vi.fn(),
  testAIConfig: vi.fn(),
}));

const existingConfig: AIProviderConfigOut = {
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

describe("AdminAIConfigPage", () => {
  beforeEach(() => {
    vi.mocked(getAIConfig).mockReset();
    vi.mocked(updateAIConfig).mockReset();
    vi.mocked(testAIConfig).mockReset();
    vi.mocked(getAIConfig).mockResolvedValue(null);
  });

  it("hiển thị trạng thái chưa cấu hình", async () => {
    render(<AdminAIConfigPage />);

    expect(await screen.findByText(/Chưa cấu hình/)).toBeInTheDocument();
  });

  it("hiển thị model và key đã che khi đã cấu hình", async () => {
    vi.mocked(getAIConfig).mockResolvedValue(existingConfig);

    render(<AdminAIConfigPage />);

    const summary = await screen.findByText(/Đang dùng/);
    expect(summary).toHaveTextContent("gpt-4o-mini");
    expect(screen.getByText("sk-...ab12")).toBeInTheDocument();
  });

  it("không cho lưu khi chưa có cấu hình và chưa nhập API key", async () => {
    render(<AdminAIConfigPage />);
    await screen.findByText(/Chưa cấu hình/);

    expect(screen.getByRole("button", { name: "Lưu cấu hình" })).toBeDisabled();
  });

  it("lưu cấu hình mới với API key vừa nhập", async () => {
    const user = userEvent.setup();
    vi.mocked(updateAIConfig).mockResolvedValue(existingConfig);
    render(<AdminAIConfigPage />);
    await screen.findByText(/Chưa cấu hình/);

    await user.type(screen.getByPlaceholderText("sk-..."), "sk-new-key");
    await user.click(screen.getByRole("button", { name: "Lưu cấu hình" }));

    await waitFor(() => expect(updateAIConfig).toHaveBeenCalledWith(
      expect.objectContaining({ model: "gpt-4o-mini", api_key: "sk-new-key" }),
    ));
  });

  it("để trống API key khi sửa cấu hình đã có vẫn lưu được (giữ key cũ)", async () => {
    vi.mocked(getAIConfig).mockResolvedValue(existingConfig);
    vi.mocked(updateAIConfig).mockResolvedValue(existingConfig);
    const user = userEvent.setup();
    render(<AdminAIConfigPage />);
    await screen.findByText("sk-...ab12");

    await user.click(screen.getByRole("button", { name: "Lưu cấu hình" }));

    await waitFor(() => expect(updateAIConfig).toHaveBeenCalledWith(expect.objectContaining({ api_key: null })));
  });

  it("nút kiểm tra kết nối bị khóa khi chưa nhập key", async () => {
    render(<AdminAIConfigPage />);
    await screen.findByText(/Chưa cấu hình/);

    expect(screen.getByRole("button", { name: "Kiểm tra kết nối" })).toBeDisabled();
  });

  it("gọi kiểm tra kết nối và hiển thị kết quả thành công", async () => {
    vi.mocked(testAIConfig).mockResolvedValue({ ok: true, message: "Kết nối thành công." });
    const user = userEvent.setup();
    render(<AdminAIConfigPage />);
    await screen.findByText(/Chưa cấu hình/);

    await user.type(screen.getByPlaceholderText("sk-..."), "sk-test-key");
    await user.click(screen.getByRole("button", { name: "Kiểm tra kết nối" }));

    expect(await screen.findByText("Kết nối thành công.")).toBeInTheDocument();
    expect(testAIConfig).toHaveBeenCalledWith("sk-test-key");
  });

  it("hiển thị lỗi khi kiểm tra kết nối thất bại", async () => {
    vi.mocked(testAIConfig).mockResolvedValue({ ok: false, message: "API key không hợp lệ." });
    const user = userEvent.setup();
    render(<AdminAIConfigPage />);
    await screen.findByText(/Chưa cấu hình/);

    await user.type(screen.getByPlaceholderText("sk-..."), "sk-bad-key");
    await user.click(screen.getByRole("button", { name: "Kiểm tra kết nối" }));

    expect(await screen.findByText("API key không hợp lệ.")).toBeInTheDocument();
  });
});

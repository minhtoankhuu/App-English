import { act } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as examApi from "../api/exams";
import type { ExamDetailOut } from "../types/exam";
import { ApiError } from "../api/client";
import { ExamExportPage } from "./ExamExportPage";

vi.mock("../api/exams", () => ({
  getExam: vi.fn(),
  saveExportConfig: vi.fn(),
  downloadExportUrl: (examId: string, variant: string) => `/download/${examId}/${variant}`,
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function makeExam(id: string, title: string): ExamDetailOut {
  return {
    id, title, status: "ready", source_type: "global_success", grade_id: "grade-1",
    level: { id: "level-1", code: "A2" }, unit_id: "unit-1", grammar_topic_id: null,
    cambridge_certificate_id: null, extra_prompt: null, export_mode: "plain", variant_count: 1,
    grammar_point_ids: [], blocks: [],
  };
}

function NavigationControls() {
  const navigate = useNavigate();
  return <button onClick={() => navigate("/exams/exam-2/export")}>Đổi đề</button>;
}

function renderExport() {
  return render(
    <MemoryRouter initialEntries={["/exams/exam-1/export"]}>
      <NavigationControls />
      <Routes><Route path="/exams/:examId/export" element={<ExamExportPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe("ExamExportPage route isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(examApi.saveExportConfig).mockResolvedValue(makeExam("exam-1", "Old exam"));
  });

  it("ignores an old load and keeps links on the current exam", async () => {
    const oldLoad = deferred<ExamDetailOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) =>
      id === "exam-1" ? oldLoad.promise : Promise.resolve(makeExam("exam-2", "New exam")),
    );
    const user = userEvent.setup();
    renderExport();

    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New exam")).toBeInTheDocument();
    await act(async () => oldLoad.resolve(makeExam("exam-1", "Old exam")));

    expect(screen.queryByText("Old exam")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Mã đề A" })).toHaveAttribute("href", "/download/exam-2/A");
  });

  it("does not let an old save reload the new route", async () => {
    const oldSave = deferred<ExamDetailOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) => Promise.resolve(makeExam(id, id === "exam-1" ? "Old exam" : "New exam")));
    vi.mocked(examApi.saveExportConfig).mockReturnValueOnce(oldSave.promise);
    const user = userEvent.setup();
    renderExport();
    await user.click(await screen.findByRole("button", { name: "Lưu vào Đề của tôi" }));

    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New exam")).toBeInTheDocument();
    await act(async () => oldSave.resolve(makeExam("exam-1", "Old exam")));

    await waitFor(() => expect(examApi.getExam).toHaveBeenCalledTimes(2));
    expect(screen.getByText("New exam")).toBeInTheDocument();
  });

  it("ignores an error from a save on the previous route", async () => {
    const oldSave = deferred<ExamDetailOut>();
    vi.mocked(examApi.getExam).mockImplementation((id) => Promise.resolve(makeExam(id, id === "exam-1" ? "Old exam" : "New exam")));
    vi.mocked(examApi.saveExportConfig).mockReturnValueOnce(oldSave.promise);
    const user = userEvent.setup();
    renderExport();
    await user.click(await screen.findByRole("button", { name: "Lưu vào Đề của tôi" }));
    await user.click(screen.getByRole("button", { name: "Đổi đề" }));
    expect(await screen.findByText("New exam")).toBeInTheDocument();

    await act(async () => oldSave.reject(new Error("old failure")));

    expect(screen.queryByText("Chưa lưu được cấu hình xuất")).not.toBeInTheDocument();
  });

  it("keeps the current form and shows a reload error after save", async () => {
    vi.mocked(examApi.getExam)
      .mockResolvedValueOnce(makeExam("exam-1", "Current exam"))
      .mockRejectedValueOnce(new ApiError(500, "Không tải lại được đề"));
    const user = userEvent.setup();
    renderExport();

    await user.click(await screen.findByRole("button", { name: "Lưu vào Đề của tôi" }));

    expect(await screen.findByText("Không tải lại được đề")).toBeInTheDocument();
    expect(screen.getByText("Current exam")).toBeInTheDocument();
  });
});

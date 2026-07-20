import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { GradeOut, ProficiencyLevelOut, UnitOut } from "../types/catalog";
import { ExamCreatePage } from "./ExamCreatePage";

const examApi = vi.hoisted(() => ({ createExam: vi.fn() }));
const catalogApi = vi.hoisted(() => ({
  listGrades: vi.fn(),
  listProficiencyLevels: vi.fn(),
  listGrammarTopics: vi.fn(),
  listCambridgeCertificates: vi.fn(),
  listUnitsForGrade: vi.fn(),
}));

vi.mock("../api/exams", () => examApi);
vi.mock("../api/catalog", () => catalogApi);

const grade7: GradeOut = {
  id: "grade-7",
  number: 7,
  school_stage: { id: "s1", code: "secondary", name: "THCS", order_no: 2 },
  suggested_level: { id: "level-a2", code: "A2", rank: 2 },
};
const levelA2: ProficiencyLevelOut = { id: "level-a2", code: "A2", rank: 2 };
const unit3: UnitOut = { id: "unit-3", order_no: 3, title: "Community Service" };

function renderCreate() {
  return render(
    <MemoryRouter initialEntries={["/exams/new"]}>
      <Routes>
        <Route path="/exams/new" element={<ExamCreatePage />} />
        <Route path="/exams/:examId/builder" element={<p>Trình dựng đề</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ExamCreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    catalogApi.listGrades.mockResolvedValue([grade7]);
    catalogApi.listProficiencyLevels.mockResolvedValue([levelA2]);
    catalogApi.listGrammarTopics.mockResolvedValue([]);
    catalogApi.listCambridgeCertificates.mockResolvedValue([]);
    catalogApi.listUnitsForGrade.mockResolvedValue([unit3]);
  });

  it("hiển thị bước 1 và tạo đề thành công thì chuyển sang bước 2", async () => {
    const user = userEvent.setup();
    examApi.createExam.mockResolvedValue({ id: "exam-new" });
    renderCreate();

    expect(screen.getByRole("heading", { name: "Tạo đề mới" })).toBeInTheDocument();
    expect(screen.getAllByText("Nguồn kiến thức")).toHaveLength(2); // step-label + label form
    expect(await screen.findByRole("option", { name: "Unit 3 — Community Service" })).toBeInTheDocument();

    expect(await screen.findByDisplayValue("UNIT 3 REVISION EXERCISES – GLOBAL SUCCESS 7")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "+ Tạo đề" }));

    expect(examApi.createExam).toHaveBeenCalledWith({
      title: "UNIT 3 REVISION EXERCISES – GLOBAL SUCCESS 7",
      grade_id: "grade-7",
      level_id: "level-a2",
      source_type: "global_success",
      unit_id: "unit-3",
      grammar_topic_id: undefined,
      cambridge_certificate_id: undefined,
    });
    expect(await screen.findByText("Trình dựng đề")).toBeInTheDocument();
  });

  it("khóa ô Tên đề và tự đặt theo Unit + Global Success khi chọn Ôn tập theo Unit", async () => {
    renderCreate();
    await screen.findByRole("option", { name: "Unit 3 — Community Service" });

    const titleInput = await screen.findByDisplayValue("UNIT 3 REVISION EXERCISES – GLOBAL SUCCESS 7");
    expect(titleInput).toHaveAttribute("readonly");
  });

  it("hiện thông báo sắp ra mắt và khóa nút Tạo đề với loại đề khác Ôn tập theo Unit", async () => {
    const user = userEvent.setup();
    renderCreate();
    await screen.findByRole("option", { name: "Unit 3 — Community Service" });

    await user.selectOptions(screen.getByRole("combobox", { name: "Loại đề" }), "Kiểm tra giữa kì 1");

    expect(screen.getByText(/sắp ra mắt/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+ Tạo đề" })).toBeDisabled();
  });

  it("chặn tạo đề khi chưa có Unit nào cho khối lớp đã chọn", async () => {
    catalogApi.listUnitsForGrade.mockResolvedValue([]);
    renderCreate();
    await screen.findByRole("heading", { name: "Tạo đề mới" });

    expect(screen.getByRole("button", { name: "+ Tạo đề" })).toBeDisabled();
  });

  it("hiển thị lỗi và giữ nguyên trang khi tạo đề thất bại", async () => {
    const user = userEvent.setup();
    examApi.createExam.mockRejectedValue(new ApiError(500, "Không tạo được đề"));
    renderCreate();
    await screen.findByRole("option", { name: "Unit 3 — Community Service" });

    await user.click(screen.getByRole("button", { name: "+ Tạo đề" }));

    expect(await screen.findByText("Không tạo được đề")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tạo đề mới" })).toBeInTheDocument();
  });
});

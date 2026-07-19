# Exam Builder Drag-and-Drop and A4 Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép giáo viên kéo-thả block và xem trước cấu trúc đề trên nhiều trang A4 ngay trong Builder.

**Architecture:** Backend tạo read model preview độc lập, đánh số câu liên tục và chia trang bằng đơn vị dòng logic ổn định; router chỉ kiểm tra quyền và serialize kết quả. Frontend tách helper sắp xếp, danh sách block kéo-thả và component preview A4; Builder điều phối optimistic reorder, rollback và reload preview sau mutation.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic 2, pytest; React 19, TypeScript 6, HTML Drag and Drop API, Vitest, Testing Library.

## Global Constraints

- Không thêm migration hoặc thư viện drag-and-drop.
- Preview chỉ đọc dữ liệu, không gọi quota service và không thay đổi DOCX renderer.
- Preview dùng A4 dọc, nhiều trang và quy tắc sức chứa `42` dòng.
- Header trang đầu tốn `5` dòng; trang tiếp theo `2`; footer chừa `2` dòng.
- Header block tốn `2` dòng cộng `1` khi có instruction; placeholder tốn `2` dòng.
- Câu thật tốn `2 + ceil(len(prompt_text) / 90)` dòng; passage tốn `ceil(len(passage_text) / 90)` dòng khi cần render.
- Không tách một câu giữa hai trang; block dài được tách theo ranh giới câu và phần sau có `continuation=true`.
- Kéo-thả và nút Lên/Xuống dùng cùng endpoint reorder; request lỗi phải rollback optimistic state.
- Trong lúc lưu reorder, khóa mọi thao tác reorder khác.
- Commit dùng `feat:`, `fix:` hoặc `doc:`; branch là `feat/1c-exam-builder-preview`.

---

### Task 1: Read model preview và helper đánh số

**Files:**
- Create: `backend/app/services/exam_preview.py`
- Create: `backend/tests/test_exam_preview.py`

**Interfaces:**
- Consumes: `Exam`, `ExamBlock`, `Question`, `Decimal`.
- Produces: `to_roman(value: int) -> str`, `build_preview(exam: Exam) -> dict[str, object]`.

- [ ] **Step 1: Viết test RED cho đề rỗng và placeholder**

```python
def test_empty_exam_has_one_empty_page(exam):
    preview = build_preview(exam)
    assert preview["total_questions"] == 0
    assert preview["total_points"] == Decimal("0.0")
    assert preview["page_count"] == 1
    assert preview["pages"] == [{"page_number": 1, "blocks": []}]

def test_placeholders_are_numbered_across_blocks(exam_with_blocks):
    preview = build_preview(exam_with_blocks)
    first, second = preview["pages"][0]["blocks"]
    assert (first["section_label"], first["question_start"], first["question_end"]) == ("I", 1, 2)
    assert (second["section_label"], second["question_start"], second["question_end"]) == ("II", 3, 5)
    assert [q["question_number"] for q in second["questions"]] == [3, 4, 5]
    assert all(q["is_placeholder"] for q in first["questions"] + second["questions"])
```

- [ ] **Step 2: Chạy RED đúng nguyên nhân**

Run: `cd backend; $env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest tests/test_exam_preview.py -q`
Expected: FAIL khi import `app.services.exam_preview`.

- [ ] **Step 3: Cài đặt helper thuần và read model chưa phân trang**

```python
def to_roman(value: int) -> str:
    if value <= 0:
        raise ValueError("value must be positive")
    parts: list[str] = []
    for number, symbol in ROMAN_NUMERALS:
        while value >= number:
            parts.append(symbol)
            value -= number
    return "".join(parts)

def _preview_questions(block: ExamBlock, next_number: int) -> tuple[list[dict[str, object]], int]:
    actual = sorted(block.questions, key=lambda question: question.order_no)
    count = max(block.question_count, len(actual))
    items = []
    for index in range(count):
        question = actual[index] if index < len(actual) else None
        items.append({
            "question_number": next_number,
            "prompt_text": question.prompt_text if question else None,
            "passage_text": question.passage_text if question else None,
            "is_placeholder": question is None,
        })
        next_number += 1
    return items, next_number
```

`build_preview` sắp block theo `order_no`, cộng `Decimal` từ `0.0`, tạo một page và section metadata đúng schema đặc tả.

- [ ] **Step 4: Chạy GREEN**

Run: `cd backend; python -m pytest tests/test_exam_preview.py -q`
Expected: test empty và numbering PASS.

- [ ] **Step 5: Viết test RED cho câu thật, bù placeholder và Roman > 20**

```python
def test_actual_questions_are_preserved_and_missing_questions_are_filled(block_with_one_of_three_questions):
    preview = build_preview(block_with_one_of_three_questions.exam)
    questions = preview["pages"][0]["blocks"][0]["questions"]
    assert questions[0]["prompt_text"] == "Choose the correct answer."
    assert [q["is_placeholder"] for q in questions] == [False, True, True]

def test_to_roman_supports_more_than_twenty():
    assert to_roman(24) == "XXIV"
```

- [ ] **Step 6: Chạy RED rồi bổ sung hành vi tối thiểu**

Run: `cd backend; python -m pytest tests/test_exam_preview.py -q`
Expected: test dữ liệu thật hoặc Roman lớn FAIL trước thay đổi; sau khi hoàn thiện `_preview_questions` và bảng Roman thì PASS.

### Task 2: Thuật toán phân trang ổn định

**Files:**
- Modify: `backend/app/services/exam_preview.py`
- Modify: `backend/tests/test_exam_preview.py`

**Interfaces:**
- Consumes: item câu từ `_preview_questions`.
- Produces: `_question_lines(question, previous_passage) -> int`, `_paginate(blocks) -> list[dict[str, object]]`.

- [ ] **Step 1: Viết test RED cho nhiều trang và continuation**

```python
def test_long_block_splits_between_questions(long_exam):
    preview = build_preview(long_exam)
    assert preview["page_count"] >= 2
    first_piece = preview["pages"][0]["blocks"][0]
    second_piece = preview["pages"][1]["blocks"][0]
    assert first_piece["continuation"] is False
    assert second_piece["continuation"] is True
    assert second_piece["question_start"] == first_piece["question_end"] + 1

def test_single_oversized_question_terminates(oversized_question_exam):
    preview = build_preview(oversized_question_exam)
    assert preview["page_count"] <= 2
    assert sum(len(piece["questions"]) for page in preview["pages"] for piece in page["blocks"]) == 1
```

- [ ] **Step 2: Chạy RED**

Run: `cd backend; python -m pytest tests/test_exam_preview.py -k "long_block or oversized" -q`
Expected: FAIL vì output vẫn chỉ có một page.

- [ ] **Step 3: Cài thuật toán packing theo câu**

```python
PAGE_LINES = 42
FOOTER_LINES = 2

def _question_lines(question: dict[str, object], previous_passage: str | None) -> int:
    if question["is_placeholder"]:
        return 2
    prompt = str(question["prompt_text"] or "")
    passage = question["passage_text"]
    lines = 2 + math.ceil(len(prompt) / 90)
    if passage and passage != previous_passage:
        lines += math.ceil(len(str(passage)) / 90)
    return lines
```

`_paginate` khởi tạo budget `PAGE_LINES - FOOTER_LINES - header`, tính block header, chuyển trang nếu header+câu đầu không vừa, thêm từng câu; khi mở page mới cho cùng block tạo piece mới có `continuation=true`. Nếu câu lớn hơn full budget, thêm câu vào page rỗng và tiếp tục để không lặp vô hạn.

- [ ] **Step 4: Chạy GREEN và toàn file test**

Run: `cd backend; python -m pytest tests/test_exam_preview.py -q`
Expected: mọi test service PASS, bao gồm total points Decimal và passage line accounting.

### Task 3: Schema và endpoint preview có phân quyền

**Files:**
- Create: `backend/app/schemas/exam_preview.py`
- Modify: `backend/app/routers/exams.py`
- Modify: `backend/tests/test_exam_preview.py`

**Interfaces:**
- Consumes: `build_preview(exam)` và `_get_owned_exam(db, exam_id, current_user)`.
- Produces: `GET /exams/{exam_id}/preview` với response model `ExamPreviewOut`.

- [ ] **Step 1: Viết test API RED**

```python
def _login(client, db, email):
    user = User(email=email, password_hash=hash_password("Secret123!"), full_name=email, role=UserRole.TEACHER)
    db.add(user)
    db.commit()
    assert client.post("/auth/login", json={"email": email, "password": "Secret123!"}).status_code == 200
    return user

def _create_exam_with_blocks(client, db):
    grade = db.scalar(select(Grade).where(Grade.number == 7))
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == "A2"))
    unit = db.scalar(select(Unit).where(Unit.grade_id == grade.id, Unit.order_no == 3))
    exam = client.post("/exams", json={
        "title": "Preview exam", "grade_id": str(grade.id), "level_id": str(level.id),
        "source_type": "global_success", "unit_id": str(unit.id),
    }).json()
    exercise_type = db.scalar(select(ExerciseType).where(ExerciseType.code == "multiple_choice"))
    client.post(f"/exams/{exam['id']}/blocks", json={
        "exercise_type_id": str(exercise_type.id), "title": "Grammar",
        "question_count": 3, "points": "2.0",
    })
    return exam

def test_preview_endpoint_returns_typed_payload(client, seeded_db):
    _login(client, seeded_db, "preview-owner@examcraft.dev")
    exam = _create_exam_with_blocks(client, seeded_db)
    response = client.get(f"/exams/{exam['id']}/preview")
    assert response.status_code == 200
    assert response.json()["exam_id"] == exam["id"]
    assert response.json()["page_count"] == len(response.json()["pages"])

def test_preview_requires_owner(client, seeded_db):
    _login(client, seeded_db, "preview-owner@examcraft.dev")
    exam = _create_exam_with_blocks(client, seeded_db)
    client.post("/auth/logout")
    _login(client, seeded_db, "preview-other@examcraft.dev")
    assert client.get(f"/exams/{exam['id']}/preview").status_code == 403
```

Thêm riêng assert 401 khi chưa login và 404 với UUID không tồn tại.

- [ ] **Step 2: Chạy RED**

Run: `cd backend; python -m pytest tests/test_exam_preview.py -k endpoint -q`
Expected: FAIL 404 vì route chưa có.

- [ ] **Step 3: Tạo Pydantic schemas và route**

```python
class PreviewQuestionOut(BaseModel):
    question_number: int
    prompt_text: str | None
    passage_text: str | None
    is_placeholder: bool

class ExamPreviewOut(BaseModel):
    exam_id: uuid.UUID
    title: str
    total_questions: int
    total_points: Decimal
    page_count: int
    pages: list[PreviewPageOut]

@router.get("/{exam_id}/preview", response_model=ExamPreviewOut)
def get_exam_preview(exam_id: uuid.UUID, current_user: User = Depends(require_any_role), db: Session = Depends(get_db)):
    return build_preview(_get_owned_exam(db, exam_id, current_user))
```

Đặt route tĩnh `/{exam_id}/preview` trước các route question không gây xung đột; schemas piece/page chứa đúng toàn bộ trường từ spec.

- [ ] **Step 4: Chạy backend suite**

Run: `cd backend; python -m pytest -q`
Expected: toàn bộ test PASS.

- [ ] **Step 5: Commit backend**

```bash
git add backend/app/services/exam_preview.py backend/app/schemas/exam_preview.py backend/app/routers/exams.py backend/tests/test_exam_preview.py
git commit -m "feat: thêm API xem trước đề A4"
```

### Task 4: API client và component preview A4

**Files:**
- Create: `frontend/src/types/examPreview.ts`
- Create: `frontend/src/exam-preview/ExamPreview.tsx`
- Create: `frontend/src/exam-preview/ExamPreview.test.tsx`
- Modify: `frontend/src/api/exams.ts`

**Interfaces:**
- Produces: `getExamPreview(examId: string): Promise<ExamPreviewOut>` và `ExamPreview({preview, loading, error, onRetry})`.
- Consumes: backend `ExamPreviewOut` schema Task 3.

- [ ] **Step 1: Viết test RED cho các trạng thái preview**

```tsx
it("renders loading and retry states", async () => {
  const { rerender } = render(<ExamPreview preview={null} loading error={null} onRetry={retry} />);
  expect(screen.getByText("Đang dựng bản xem trước...")).toBeInTheDocument();
  rerender(<ExamPreview preview={null} loading={false} error="Không tải được" onRetry={retry} />);
  await user.click(screen.getByRole("button", { name: "Thử lại" }));
  expect(retry).toHaveBeenCalledOnce();
});

it("renders empty and multipage previews", () => {
  const { rerender } = render(<ExamPreview preview={emptyPreview} loading={false} error={null} onRetry={retry} />);
  expect(screen.getByText("Thêm phần để xem trước đề")).toBeInTheDocument();
  rerender(<ExamPreview preview={twoPagePreview} loading={false} error={null} onRetry={retry} />);
  expect(screen.getByText("Trang 1/2")).toBeInTheDocument();
  expect(screen.getByText("Trang 2/2")).toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy RED**

Run: `cd frontend; npm test -- --run src/exam-preview/ExamPreview.test.tsx`
Expected: FAIL vì module chưa tồn tại.

- [ ] **Step 3: Tạo types, API và component tối thiểu**

```typescript
export interface ExamPreviewOut {
  exam_id: string;
  title: string;
  total_questions: number;
  total_points: string;
  page_count: number;
  pages: PreviewPage[];
}

export const getExamPreview = (examId: string): Promise<ExamPreviewOut> =>
  apiGet(`/exams/${examId}/preview`);
```

Component render toolbar tổng, danh sách `<article aria-label="Trang X/Y">` có `aspectRatio: "210 / 297"`, section header, instruction, passage không lặp liên tiếp, placeholder và footer.

- [ ] **Step 4: Chạy GREEN**

Run: `cd frontend; npm test -- --run src/exam-preview/ExamPreview.test.tsx`
Expected: test loading/error/empty/multipage/placeholder/passage PASS.

### Task 5: Helper block order và danh sách kéo-thả

**Files:**
- Create: `frontend/src/exam-builder/blockOrder.ts`
- Create: `frontend/src/exam-builder/blockOrder.test.ts`
- Create: `frontend/src/exam-builder/SortableBlockList.tsx`
- Create: `frontend/src/exam-builder/SortableBlockList.test.tsx`

**Interfaces:**
- Produces: `moveBlock<T extends {id: string}>(items, sourceId, targetId): T[]`; `SortableBlockList` gọi `onReorder(blockIds)`.
- Consumes: `BlockOut`, callbacks delete/update từ Builder.

- [ ] **Step 1: Viết test RED cho helper**

```typescript
expect(moveBlock(blocks, "c", "a").map((b) => b.id)).toEqual(["c", "a", "b"]);
expect(moveBlock(blocks, "a", "c").map((b) => b.id)).toEqual(["b", "a", "c"]);
expect(moveBlock(blocks, "b", "b")).toBe(blocks);
```

- [ ] **Step 2: Chạy RED rồi cài helper tối thiểu**

Run: `cd frontend; npm test -- --run src/exam-builder/blockOrder.test.ts`
Expected: FAIL import; sau khi tạo helper splice source rồi chèn trước target (điều chỉnh index sau remove) thì PASS.

- [ ] **Step 3: Viết test RED cho drag/drop và fallback**

```tsx
const defaultProps = {
  blocks,
  saving: false,
  onReorder,
  onDelete: vi.fn(),
  onUpdateField: vi.fn(),
};

it("reorders with drag and drop", () => {
  render(<SortableBlockList {...defaultProps} />);
  fireEvent.dragStart(screen.getByLabelText("Kéo để sắp xếp A"));
  fireEvent.dragOver(screen.getByTestId("block-c"));
  fireEvent.drop(screen.getByTestId("block-c"));
  expect(onReorder).toHaveBeenCalledWith(["b", "a", "c"]);
});

it("keeps arrow controls and disables boundaries", async () => {
  render(<SortableBlockList {...defaultProps} />);
  expect(screen.getByRole("button", {name: "Lên A"})).toBeDisabled();
  await user.click(screen.getByRole("button", {name: "Xuống A"}));
  expect(onReorder).toHaveBeenCalledWith(["b", "a", "c"]);
});
```

- [ ] **Step 4: Cài component và chạy GREEN**

`SortableBlockList` render card hiện có, tay nắm `draggable`, data-testid, drag state, nút biên disabled và tất cả điều khiển reorder disabled khi `saving=true`. `dragend` xóa source/target.

Run: `cd frontend; npm test -- --run src/exam-builder/SortableBlockList.test.tsx src/exam-builder/blockOrder.test.ts`
Expected: PASS.

### Task 6: Tích hợp optimistic reorder và preview vào Builder

**Files:**
- Modify: `frontend/src/pages/ExamBuilderPage.tsx`
- Create: `frontend/src/pages/ExamBuilderPage.test.tsx`

**Interfaces:**
- Consumes: `getExamPreview`, `ExamPreview`, `SortableBlockList`, `reorderBlocks`.
- Produces: layout hai cột, reload đồng bộ exam/preview, optimistic reorder và rollback.

- [ ] **Step 1: Viết test RED cho tải preview và optimistic reorder**

```tsx
it("loads exam and preview together", async () => {
  renderBuilder();
  expect(await screen.findByText("Trang 1/1")).toBeInTheDocument();
  expect(getExamPreview).toHaveBeenCalledWith("exam-1");
});

it("rolls back reorder and keeps preview after API failure", async () => {
  reorderBlocks.mockRejectedValueOnce(new ApiError(500, "Không lưu được thứ tự"));
  renderBuilder();
  await user.click(await screen.findByRole("button", {name: "Xuống A"}));
  expect(await screen.findByText("Không lưu được thứ tự")).toBeInTheDocument();
  expect(screen.getAllByTestId(/block-/).map((el) => el.dataset.testid)).toEqual(["block-a", "block-b"]);
  expect(getExamPreview).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Chạy RED**

Run: `cd frontend; npm test -- --run src/pages/ExamBuilderPage.test.tsx`
Expected: FAIL vì Builder chưa render preview/component mới.

- [ ] **Step 3: Tích hợp state và mutation**

```tsx
const [preview, setPreview] = useState<ExamPreviewOut | null>(null);
const [previewLoading, setPreviewLoading] = useState(true);
const [previewError, setPreviewError] = useState<string | null>(null);
const [reorderSaving, setReorderSaving] = useState(false);

async function handleReorder(blockIds: string[]) {
  if (!examId || !exam || reorderSaving) return;
  const snapshot = exam;
  setExam({...exam, blocks: blockIds.map((id, index) => ({...exam.blocks.find((b) => b.id === id)!, order_no: index + 1}))});
  setReorderSaving(true);
  try {
    setExam(await reorderBlocks(examId, blockIds));
    await loadPreview();
  } catch (error) {
    setExam(snapshot);
    setError(error instanceof ApiError ? error.message : "Không lưu được thứ tự");
  } finally {
    setReorderSaving(false);
  }
}
```

Sau mọi mutation add/delete/update/grammar thành công, gọi `reload()` và `loadPreview()`. Layout CSS grid dùng `minmax(0, 1fr) minmax(320px, 0.8fr)` và media class trong `index.css`; preview sticky chỉ desktop.

- [ ] **Step 4: Chạy frontend suite, lint và build**

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`
Expected: toàn bộ test PASS, lint không warning/error, TypeScript và Vite build thành công.

- [ ] **Step 5: Commit frontend**

```bash
git add frontend
git commit -m "feat: thêm kéo thả và xem trước đề A4"
```

### Task 7: Cập nhật tiến độ và verification cuối

**Files:**
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`
- Modify: `docs/engineering/IMPLEMENTATION_NOTES.vi.md`

**Interfaces:**
- Consumes: API và UI đã hoàn thành.
- Produces: tài liệu phản ánh kéo-thả, preview A4 và giới hạn ước tính so với DOCX.

- [ ] **Step 1: Cập nhật tài liệu**

Đánh dấu checklist kéo-thả/xem trước hoàn thành; thêm API `/preview`, quy tắc read-only/không quota và ghi chú preview dùng logical lines nên không cam kết pixel-perfect Word.

- [ ] **Step 2: Chạy verification mới toàn bộ**

Run: `cd backend; $env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest -q`
Expected: toàn bộ backend test PASS.

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`
Expected: toàn bộ frontend test PASS, lint sạch, build thành công.

- [ ] **Step 3: Commit tài liệu**

```bash
git add docs/engineering/DEVELOPMENT_PLAN.vi.md docs/engineering/IMPLEMENTATION_NOTES.vi.md
git commit -m "doc: cập nhật tiến độ trình dựng đề"
```

- [ ] **Step 4: Kiểm tra phạm vi publish**

Run: `git status --short; git log --oneline main..HEAD; git diff --check main...HEAD`
Expected: worktree sạch, chỉ có 5 commit của task (spec, plan, backend, frontend, progress), không có whitespace error.

- [ ] **Step 5: Push và tạo Draft PR**

Run: `git push -u origin feat/1c-exam-builder-preview`
Expected: branch được push thành công. Tạo Draft PR vào `main` với title `feat: thêm kéo thả và xem trước đề A4`, mô tả API read-only, optimistic rollback và kết quả verification; không merge PR.

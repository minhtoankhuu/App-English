# Daily Generation Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Giới hạn mỗi giáo viên tối đa 10 lượt gọi sinh nội dung AI mỗi ngày theo múi giờ Asia/Bangkok, trong khi Admin không bị giới hạn, đồng thời hiển thị số lượt còn lại trên giao diện.

**Architecture:** Backend lưu một bộ đếm theo `(user_id, usage_date)`, khóa dòng PostgreSQL khi giữ lượt và dùng cùng transaction với thao tác sinh câu hỏi để bảo đảm lỗi AI hoàn trả lượt. Frontend dùng một Usage Context tại `Layout` để tải `/usage/me`, hiển thị badge cho giáo viên và cho các trang sinh đề yêu cầu làm mới bộ đếm sau thao tác thành công.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Pydantic Settings, pytest; React 19, TypeScript 6, React Router, Vitest, Testing Library.

## Global Constraints

- Hạn mức mặc định là `DAILY_GENERATION_LIMIT=10` và phải là số nguyên dương.
- Ngày sử dụng và thời điểm reset được tính cố định theo `Asia/Bangkok`.
- Sinh toàn bộ đề tốn một lượt cho mỗi block; sinh lại một câu tốn đúng một lượt.
- Nếu số lượt còn lại không đủ cho toàn bộ đề, từ chối trước khi gọi provider và không sinh một phần.
- Provider hoặc validation lỗi phải rollback cả lượt đã giữ và thay đổi câu hỏi.
- Admin không giới hạn và không tạo/cập nhật dòng `daily_usage`.
- Các thao tác chỉnh sửa, duyệt và xuất đề không tốn lượt.
- Phản hồi vượt hạn mức dùng HTTP `429` với `detail` gồm `message`, `limit`, `used`, `remaining`, `reset_at`.
- Commit theo cấu trúc của dự án: `feat: ...`, `fix: ...`, `doc: ...`.

---

### Task 1: Cấu hình, model và migration bộ đếm hằng ngày

**Files:**
- Create: `backend/app/models/usage.py`
- Create: `backend/alembic/versions/d4f61c2a9b07_add_daily_usage.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/config.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_usage.py`

**Interfaces:**
- Produces: `DailyUsage(user_id: UUID, usage_date: date, used_count: int)` và `Settings.daily_generation_limit: int`.
- Consumes: `User`, `TimestampMixin`, revision Alembic `a71d10c9e4b2`.

- [ ] **Step 1: Viết test cấu hình thất bại**

```python
from pydantic import ValidationError
from app.config import Settings

def test_daily_generation_limit_defaults_to_ten():
    assert Settings(_env_file=None).daily_generation_limit == 10

def test_daily_generation_limit_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, daily_generation_limit=0)
```

- [ ] **Step 2: Chạy test RED**

Run: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest tests/test_usage.py -q`
Expected: FAIL vì chưa có `daily_generation_limit`.

- [ ] **Step 3: Thêm cấu hình và model tối thiểu**

```python
daily_generation_limit: int = Field(default=10, gt=0)

class DailyUsage(TimestampMixin, Base):
    __tablename__ = "daily_usage"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

Thêm import/export model, migration tạo bảng/index/unique constraint, `DAILY_GENERATION_LIMIT=10` vào `.env.example` và service backend trong `docker-compose.yml`.

- [ ] **Step 4: Kiểm tra migration và test GREEN**

Run: `cd backend; alembic upgrade head; alembic downgrade a71d10c9e4b2; alembic upgrade head; python -m pytest tests/test_usage.py -q`
Expected: ba lệnh Alembic thành công và test PASS.

### Task 2: Dịch vụ giữ lượt và API trạng thái

**Files:**
- Create: `backend/app/services/usage.py`
- Create: `backend/app/schemas/usage.py`
- Create: `backend/app/routers/usage.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_usage.py`

**Interfaces:**
- Produces: `UsageStatus`, `get_usage_status(db, user, now=None)`, `reserve_usage(db, user, amount, now=None)`, `GET /usage/me`.
- Consumes: `DailyUsage`, `Settings.daily_generation_limit`, `UserRole`.

- [ ] **Step 1: Viết test RED cho giáo viên, Admin, reset ngày và vượt quota**

```python
def test_teacher_usage_starts_at_zero_and_reserves_amount(seeded_db, teacher):
    status = get_usage_status(seeded_db, teacher, now=BANGKOK_NOON)
    assert (status.used, status.remaining) == (0, 10)
    assert reserve_usage(seeded_db, teacher, 3, now=BANGKOK_NOON).remaining == 7

def test_reserve_rejects_whole_amount_without_increment(seeded_db, teacher):
    reserve_usage(seeded_db, teacher, 8, now=BANGKOK_NOON)
    with pytest.raises(UsageLimitExceeded) as error:
        reserve_usage(seeded_db, teacher, 3, now=BANGKOK_NOON)
    assert error.value.status.remaining == 2

def test_admin_is_unlimited_without_daily_row(seeded_db, admin):
    assert reserve_usage(seeded_db, admin, 99, now=BANGKOK_NOON).is_unlimited
    assert seeded_db.scalar(select(func.count(DailyUsage.id))) == 0
```

- [ ] **Step 2: Chạy test RED**

Run: `cd backend; python -m pytest tests/test_usage.py -q`
Expected: FAIL do module dịch vụ/API chưa tồn tại.

- [ ] **Step 3: Cài đặt khóa dòng và schema ổn định**

```python
@dataclass(frozen=True)
class UsageStatus:
    limit: int
    used: int
    remaining: int
    usage_date: date
    reset_at: datetime
    is_unlimited: bool

def reserve_usage(db: Session, user: User, amount: int, now: datetime | None = None) -> UsageStatus:
    if user.role == UserRole.ADMIN:
        return _admin_status(now)
    db.execute(pg_insert(DailyUsage).values(...).on_conflict_do_nothing(
        index_elements=[DailyUsage.user_id, DailyUsage.usage_date]
    ))
    row = db.scalar(select(DailyUsage).where(...).with_for_update())
    if row.used_count + amount > settings.daily_generation_limit:
        raise UsageLimitExceeded(_to_status(row, now))
    row.used_count += amount
    db.flush()
    return _to_status(row, now)
```

Router chuyển `UsageLimitExceeded` thành HTTP 429 đúng object `detail`; `/usage/me` trả đủ sáu trường cho cả hai role.

- [ ] **Step 4: Chạy test GREEN và kiểm tra API xác thực**

Run: `cd backend; python -m pytest tests/test_usage.py -q`
Expected: PASS, gồm `/usage/me` trả 401 khi chưa đăng nhập và schema đúng khi đăng nhập.

### Task 3: Áp quota nguyên tử vào hai luồng sinh AI

**Files:**
- Modify: `backend/app/routers/exams.py`
- Test: `backend/tests/test_exams.py`
- Test: `backend/tests/test_usage.py`

**Interfaces:**
- Consumes: `reserve_usage(db, current_user, amount)` và `UsageLimitExceeded.status`.
- Produces: generate giữ `len(exam.blocks)` lượt; regenerate giữ `1`; lỗi rollback transaction.

- [ ] **Step 1: Viết test RED tại router boundary**

```python
def test_generate_reserves_one_unit_per_block(client, seeded_db, logged_in_teacher, exam_with_two_blocks):
    response = client.post(f"/exams/{exam_with_two_blocks.id}/generate")
    assert response.status_code == 200
    assert client.get("/usage/me").json()["used"] == 2

def test_generate_rejects_before_provider_when_remaining_is_insufficient(...):
    reserve_usage(seeded_db, teacher, 9)
    provider.generate.reset_mock()
    response = client.post(f"/exams/{exam_with_two_blocks.id}/generate")
    assert response.status_code == 429
    provider.generate.assert_not_called()
    assert client.get("/usage/me").json()["used"] == 9

def test_provider_failure_rolls_back_reserved_usage(...):
    provider.generate.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError):
        client.post(f"/exams/{exam.id}/generate")
    seeded_db.rollback()
    assert get_usage_status(seeded_db, teacher).used == 0
```

- [ ] **Step 2: Chạy test RED**

Run: `cd backend; python -m pytest tests/test_exams.py tests/test_usage.py -q`
Expected: FAIL vì endpoint chưa giữ lượt.

- [ ] **Step 3: Giữ lượt sau validation và rollback khi lỗi**

```python
try:
    reserve_usage(db, current_user, len(exam.blocks))
    for block in exam.blocks:
        generate_block_questions(db, exam, block)
    db.commit()
except UsageLimitExceeded as exc:
    db.rollback()
    raise HTTPException(status_code=429, detail=exc.status.to_error_detail()) from exc
except Exception:
    db.rollback()
    raise
```

Áp cùng cấu trúc cho regenerate với amount `1`, nhưng chỉ sau kiểm tra 404, locked và approved để các lỗi validation không chạm quota.

- [ ] **Step 4: Chạy backend suite GREEN**

Run: `cd backend; python -m pytest -q`
Expected: toàn bộ test PASS.

- [ ] **Step 5: Commit backend**

```bash
git add backend docker-compose.yml
git commit -m "feat: thêm hạn mức sinh đề hằng ngày"
```

### Task 4: API client và Usage Context trên frontend

**Files:**
- Create: `frontend/src/types/usage.ts`
- Create: `frontend/src/api/usage.ts`
- Create: `frontend/src/usage/UsageContext.tsx`
- Create: `frontend/src/usage/UsageContext.test.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/Layout.tsx`
- Modify: `frontend/src/Layout.test.tsx`

**Interfaces:**
- Produces: `UsageStatus`, `getMyUsage()`, `UsageProvider`, `useUsage(): { status, loading, refresh }`.
- Consumes: authenticated `UserOut`; error detail object `{ message: string, ... }`.

- [ ] **Step 1: Viết test RED cho error object, badge và Admin**

```tsx
it("uses detail.message for structured 429 errors", async () => {
  mockFetchJson(429, { detail: { message: "Đã hết lượt", remaining: 0 } });
  await expect(apiGet("/x")).rejects.toMatchObject({ status: 429, message: "Đã hết lượt" });
});

it("shows remaining usage for teachers", async () => {
  mockGetMyUsage({ limit: 10, used: 3, remaining: 7, is_unlimited: false, ...dates });
  renderLayout(teacherUser);
  expect(await screen.findByText("Còn 7/10 lượt hôm nay")).toBeInTheDocument();
});

it("does not request or render quota for admin", () => {
  renderLayout(adminUser);
  expect(getMyUsage).not.toHaveBeenCalled();
  expect(screen.queryByText(/lượt hôm nay/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy test RED**

Run: `cd frontend; npm test -- --run src/Layout.test.tsx src/usage/UsageContext.test.tsx`
Expected: FAIL vì API/context chưa tồn tại và client bỏ qua `detail.message`.

- [ ] **Step 3: Cài đặt client, context và badge**

```tsx
const UsageContext = createContext<UsageContextValue | null>(null);
export function UsageProvider({ user, children }: PropsWithChildren<{ user: UserOut }>) {
  const [status, setStatus] = useState<UsageStatus | null>(null);
  const refresh = useCallback(async () => {
    if (user.role === "admin") return;
    setStatus(await getMyUsage());
  }, [user.role]);
  useEffect(() => { void refresh(); }, [refresh]);
  return <UsageContext.Provider value={{ status, loading, refresh }}>{children}</UsageContext.Provider>;
}
```

Trong client, nếu `detail` là object và `detail.message` là string thì dùng message đó. Bọc header và `<Outlet />` trong provider; chỉ render badge khi teacher và status đã tải thành công, lỗi tải quota không chặn điều hướng.

- [ ] **Step 4: Chạy test GREEN**

Run: `cd frontend; npm test -- --run src/Layout.test.tsx src/usage/UsageContext.test.tsx`
Expected: PASS.

### Task 5: Đồng bộ badge sau generate và regenerate

**Files:**
- Modify: `frontend/src/pages/ExamBuilderPage.tsx`
- Modify: `frontend/src/pages/ExamReviewPage.tsx`
- Create: `frontend/src/pages/ExamGenerationUsage.test.tsx`

**Interfaces:**
- Consumes: `useUsage().refresh()`.
- Produces: refresh quota đúng một lần sau generate/regenerate thành công, không refresh khi API lỗi.

- [ ] **Step 1: Viết test RED cho hai handler**

```tsx
it("refreshes usage after successful full generation", async () => {
  renderBuilderWithMocks();
  await user.click(await screen.findByRole("button", { name: /sinh đề/i }));
  await waitFor(() => expect(refreshUsage).toHaveBeenCalledTimes(1));
});

it("refreshes usage after successful regeneration but not after a failed call", async () => {
  renderReviewWithMocks();
  await user.click(await screen.findByRole("button", { name: /sinh lại/i }));
  await waitFor(() => expect(refreshUsage).toHaveBeenCalledTimes(1));
  regenerateQuestion.mockRejectedValueOnce(new ApiError(429, "Đã hết lượt"));
  await user.click(screen.getByRole("button", { name: /sinh lại/i }));
  expect(refreshUsage).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Chạy test RED**

Run: `cd frontend; npm test -- --run src/pages/ExamGenerationUsage.test.tsx`
Expected: FAIL vì handlers chưa gọi `refresh`.

- [ ] **Step 3: Gọi refresh sau API thành công**

```tsx
const { refresh } = useUsage();
await generateExam(examId);
await refresh();
navigate(`/exams/${examId}/review`);
```

Với regenerate: gọi `await refresh()` ngay sau `await regenerateQuestion(...)`, trước `reload()`. Không đặt refresh trong `finally` để request lỗi giữ nguyên badge.

- [ ] **Step 4: Chạy frontend suite, lint và build**

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`
Expected: tất cả PASS, lint không lỗi, TypeScript/Vite build thành công.

- [ ] **Step 5: Commit frontend**

```bash
git add frontend
git commit -m "feat: hiển thị hạn mức sinh đề"
```

### Task 6: Cập nhật tiến độ và kiểm chứng toàn bộ

**Files:**
- Modify: `docs/PROGRESS.md`

**Interfaces:**
- Consumes: kết quả migration, backend suite và frontend suite.
- Produces: tài liệu tiến độ ghi rõ quota 10 lượt/ngày, Admin unlimited và các lệnh xác minh.

- [ ] **Step 1: Cập nhật tài liệu**

Thêm mục đã hoàn thành mô tả: bộ đếm theo ngày Asia/Bangkok; full generation tính theo block; regenerate tính một lượt; 429 nguyên tử; badge giáo viên; Admin không giới hạn.

- [ ] **Step 2: Chạy verification cuối**

Run: `cd backend; alembic upgrade head; python -m pytest -q`
Expected: migration ở revision `d4f61c2a9b07`, toàn bộ backend tests PASS.

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`
Expected: toàn bộ frontend tests PASS, lint và build thành công.

- [ ] **Step 3: Commit tài liệu**

```bash
git add docs/PROGRESS.md
git commit -m "doc: cập nhật tiến độ hạn mức sử dụng"
```

- [ ] **Step 4: Kiểm tra phạm vi commit trước khi publish**

Run: `git status --short; git log --oneline main..HEAD`
Expected: worktree sạch và chỉ có các commit đặc tả, plan, backend, frontend, tiến độ của task hạn mức.

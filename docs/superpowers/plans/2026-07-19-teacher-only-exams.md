# Teacher-Only Exams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Loại bỏ hoàn toàn workflow đề thi khỏi Admin và chỉ cho Giáo viên truy cập `/exams` ở cả backend lẫn frontend.

**Architecture:** Backend khóa router đề thi bằng dependency `require_teacher`. Frontend tính `homePath` từ vai trò, dùng guard route để không mount trang đề cho Admin, đồng thời dựng menu/logo riêng theo vai trò.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React 19, React Router, Vitest, Testing Library, TypeScript.

## Global Constraints

- Không xóa hoặc chuyển quyền đề cũ của Admin.
- Không sửa schema hoặc tạo migration.
- Catalog và `/usage/me` giữ API hiện tại; Admin không gọi quota từ frontend.
- Commit theo cấu trúc `fix: ...` và `doc: ...`.
- Viết test thất bại trước khi sửa implementation.

---

### Task 1: Khóa API đề thi cho Giáo viên

**Files:**
- Modify: `backend/app/deps.py`
- Modify: `backend/app/routers/exams.py`
- Modify: `backend/tests/test_exams.py`

**Interfaces:**
- Produces: `require_teacher = require_role(UserRole.TEACHER)`.
- Consumes: `UserRole`, `require_role`, FastAPI dependency injection hiện có.

- [ ] **Step 1: Viết test backend thất bại cho Admin**

Thêm helper tạo Admin riêng trong transaction test (không phụ thuộc credential `.env`) và test tham số hóa các request đại diện:

```python
def _login_as_admin(client, db):
    user = User(
        email="exam-admin@examcraft.dev",
        password_hash=hash_password("Secret123!"),
        full_name="Exam Admin",
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    response = client.post(
        "/auth/login",
        json={"email": "exam-admin@examcraft.dev", "password": "Secret123!"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("get", "/exams", None),
        ("post", "/exams", {}),
        ("get", f"/exams/{uuid.uuid4()}", None),
    ],
)
def test_admin_cannot_access_exam_workflow(client, db, method, path, json):
    _login_as_admin(client, db)

    response = getattr(client, method)(path, json=json) if json is not None else getattr(client, method)(path)

    assert response.status_code == 403
    assert response.json()["detail"] == "Không đủ quyền truy cập"
```

Thêm test chưa đăng nhập `GET /exams` trả `401` để giữ phân biệt authentication/authorization.

- [ ] **Step 2: Chạy test để xác nhận RED**

Run:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test"
.\backend\.venv\Scripts\python -m pytest backend/tests/test_exams.py -k "admin_cannot_access or unauthenticated_cannot_access" -q
```

Expected: các case Admin thất bại vì API hiện cho Admin đi tiếp; case chưa đăng nhập đạt.

- [ ] **Step 3: Thêm dependency và đổi router**

Trong `backend/app/deps.py`:

```python
require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER)
require_any_role = require_role(UserRole.ADMIN, UserRole.TEACHER)
```

Trong `backend/app/routers/exams.py`, import `require_teacher`, đặt dependency cấp router:

```python
router = APIRouter(prefix="/exams", tags=["exams"], dependencies=[Depends(require_teacher)])
```

Và thay mọi dependency tham số `current_user: User = Depends(require_any_role)` trong file bằng `Depends(require_teacher)` để hợp đồng endpoint nhất quán.

- [ ] **Step 4: Chạy test mục tiêu và toàn bộ backend**

Run:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test"
.\backend\.venv\Scripts\python -m pytest backend/tests/test_exams.py -q
.\backend\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: test đề thi và toàn bộ backend pass.

- [ ] **Step 5: Commit backend**

```bash
git add backend/app/deps.py backend/app/routers/exams.py backend/tests/test_exams.py
git commit -m "fix: giới hạn API đề thi cho giáo viên"
```

### Task 2: Chặn route đề thi của Admin

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `user.role`, `Navigate`, các page component hiện có.
- Produces: redirect theo vai trò và không mount exam pages cho Admin.

- [ ] **Step 1: Mở rộng mock page và viết test RED**

Mock đủ `ExamBuilderPage`, `ExamReviewPage`, `ExamExportPage` bằng heading riêng. Thêm test tham số hóa `['/', '/exams', '/exams/exam-1/builder', '/exams/exam-1/review', '/exams/exam-1/export', '/khong-ton-tai']` cho Admin:

```tsx
it.each(adminPaths)("chuyển Admin từ %s về dashboard", async (path) => {
  vi.mocked(fetchCurrentUser).mockResolvedValue(adminUser);
  window.history.replaceState({}, "", path);
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Quản trị hệ thống" })).toBeInTheDocument();
  await waitFor(() => expect(window.location.pathname).toBe("/admin"));
  expect(screen.queryByRole("heading", { name: "Đề của tôi" })).not.toBeInTheDocument();
});
```

Giữ và mở rộng test Giáo viên `/` về `/exams` và route Admin về `/exams`.

- [ ] **Step 2: Chạy test để xác nhận RED**

Run: `npm test -- --run src/App.test.tsx`

Expected: các route đề của Admin mount trang đề hoặc không về `/admin`.

- [ ] **Step 3: Tạo route guard theo vai trò**

Trong `App.tsx`, import `ReactNode` bằng `import type { ReactNode } from "react";` rồi tính:

```tsx
const isAdmin = user.role === "admin";
const homePath = isAdmin ? "/admin" : "/exams";
const teacherOnly = (element: ReactNode) => (isAdmin ? <Navigate to="/admin" replace /> : element);
```

Dùng `homePath` cho `/` và `*`; bọc toàn bộ route `/exams*` bằng `teacherOnly(...)`. Giữ guard Admin hiện có nhưng redirect Giáo viên về `/exams`.

- [ ] **Step 4: Chạy App tests**

Run: `npm test -- --run src/App.test.tsx`

Expected: pass; Admin không mount page đề ở mọi route được kiểm tra.

- [ ] **Step 5: Commit route guard**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "fix: chuyển Admin khỏi route đề thi"
```

### Task 3: Tách header theo vai trò

**Files:**
- Modify: `frontend/src/Layout.tsx`
- Modify: `frontend/src/Layout.test.tsx`

**Interfaces:**
- Consumes: `user.role`, `UsageProvider`, React Router `Link`.
- Produces: `homePath` và `navLinks` chỉ chứa chức năng thuộc vai trò hiện tại.

- [ ] **Step 1: Viết test RED cho header Admin**

Mở rộng tests:

```tsx
it("chỉ hiển thị điều hướng quản trị cho Admin", () => {
  renderLayout(adminUser);
  expect(screen.getByRole("link", { name: "ExamCraft AI" })).toHaveAttribute("href", "/admin");
  expect(screen.getByRole("link", { name: "Quản trị" })).toHaveAttribute("href", "/admin");
  expect(screen.queryByRole("link", { name: "Đề của tôi" })).not.toBeInTheDocument();
});
```

Với Giáo viên, xác nhận logo và `Đề của tôi` cùng trỏ `/exams`, không có `Quản trị`.

- [ ] **Step 2: Chạy test để xác nhận RED**

Run: `npm test -- --run src/Layout.test.tsx`

Expected: Admin vẫn có `Đề của tôi` và logo trỏ `/exams`.

- [ ] **Step 3: Dựng menu theo vai trò**

Trong `LayoutContent`:

```tsx
const isAdmin = user.role === "admin";
const homePath = isAdmin ? "/admin" : "/exams";
const navLinks = isAdmin
  ? [{ to: "/admin", label: "Quản trị" }]
  : [{ to: "/exams", label: "Đề của tôi" }];
```

Dùng `homePath` cho logo. Giữ quota chỉ hiển thị với Giáo viên.

- [ ] **Step 4: Chạy Layout tests và toàn bộ frontend**

Run:

```bash
npm test -- --run src/Layout.test.tsx
npm test -- --run
npm run lint
npm run build
```

Expected: toàn bộ test, lint và build pass.

- [ ] **Step 5: Commit header**

```bash
git add frontend/src/Layout.tsx frontend/src/Layout.test.tsx
git commit -m "fix: tách điều hướng Admin khỏi đề thi"
```

### Task 4: Tài liệu tiến độ, verification và publish

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`

**Interfaces:**
- Consumes: hành vi phân quyền hoàn chỉnh từ Tasks 1–3.
- Produces: mô tả vai trò nhất quán và Draft PR vào `main`.

- [ ] **Step 1: Cập nhật tài liệu**

Trong README, nêu rõ Admin chỉ có workflow quản trị và Giáo viên mới có workflow đề thi. Trong development plan, cập nhật mục Admin/role navigation để phản ánh phân tách hai chiều ở cả frontend/backend.

- [ ] **Step 2: Chạy verification cuối**

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test"
.\backend\.venv\Scripts\python -m pytest backend/tests -q
Push-Location frontend
npm test -- --run
npm run lint
npm run build
Pop-Location
git diff --check main...HEAD
git diff --name-only main...HEAD
```

Expected: backend/frontend pass; diff chỉ gồm spec, plan, backend/frontend role guard tests và hai tài liệu tiến độ.

- [ ] **Step 3: Commit tài liệu**

```bash
git add README.md docs/engineering/DEVELOPMENT_PLAN.vi.md
git commit -m "doc: cập nhật phân quyền Admin và Giáo viên"
```

- [ ] **Step 4: Push và tạo Draft PR**

```bash
git push -u origin fix/teacher-only-exams
```

Tạo Draft PR vào `main` với tiêu đề `fix: giới hạn workflow đề thi cho giáo viên`, mô tả root cause, backend/frontend guards và kết quả test. Không merge PR.

# Admin Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện dashboard quản trị có phân quyền, thống kê giáo viên hoạt động, trạng thái lỗi rõ ràng và kiểm thử frontend tự động.

**Architecture:** React Router tiếp tục gate quyền tại `App.tsx`; `Layout.tsx` dựng menu theo vai trò; `AdminOverviewPage.tsx` chỉ dùng API `listTeachers()` hiện có và quản lý trạng thái thống kê cục bộ. Vitest, Testing Library và jsdom kiểm thử hành vi qua DOM, không kiểm thử chi tiết cài đặt.

**Tech Stack:** React 19, TypeScript strict, React Router 7, Vite 8, Vitest, Testing Library, jsdom, oxlint.

## Global Constraints

- Không thêm API backend hoặc route placeholder cho phân hệ chưa triển khai.
- Chỉ thẻ “Tài khoản & phân quyền” được điều hướng.
- Giáo viên truy cập `/admin` phải được chuyển về `/exams`.
- Commit dùng tiền tố `feat:`, `fix:` hoặc `doc:`; branch dùng tiền tố `feat/` hoặc `fix/`.
- Không stage thay đổi ngoài phạm vi dashboard và tài liệu trạng thái dự án.

---

### Task 1: Thiết lập kiểm thử frontend

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tsconfig.app.json`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/fixtures.ts`

**Interfaces:**
- Produces: môi trường `npm test -- --run` với DOM matchers và hai fixture `adminUser`, `teacherUser` kiểu `UserOut`.

- [ ] **Step 1: Cài dependencies kiểm thử**

Run: `npm install --save-dev vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event`

Expected: `package.json` và lockfile chứa các dependency mới.

- [ ] **Step 2: Thêm script và cấu hình test**

Thêm script `"test": "vitest"`; thêm `test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", clearMocks: true }` vào `vite.config.ts`; thêm `"vitest/globals"` và `"@testing-library/jest-dom"` vào `compilerOptions.types`.

Tạo `frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

Tạo `frontend/src/test/fixtures.ts`:

```ts
import type { UserOut } from "../types/auth";

export const adminUser: UserOut = {
  id: "admin-1",
  email: "admin@example.com",
  full_name: "Admin",
  role: "admin",
  is_active: true,
};

export const teacherUser: UserOut = { ...adminUser, id: "teacher-1", role: "teacher" };
```

- [ ] **Step 3: Xác minh test runner hoạt động**

Run: `npm test -- --run --passWithNoTests`

Expected: exit 0 và Vitest báo không có test.

---

### Task 2: Kiểm thử và hoàn thiện điều hướng theo vai trò

**Files:**
- Create: `frontend/src/Layout.test.tsx`
- Create: `frontend/src/App.test.tsx`
- Modify: `frontend/src/Layout.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `adminUser`, `teacherUser` từ Task 1.
- Produces: route `/admin` chỉ dành cho Admin và menu “Quản trị” chỉ hiện với Admin.

- [ ] **Step 1: Viết test hồi quy cho menu và route đã có trong worktree**

Trong `Layout.test.tsx`, render `Layout` bằng `MemoryRouter` và xác nhận Admin thấy link `Quản trị` trỏ `/admin`, giáo viên không thấy link này.

Trong `App.test.tsx`, mock `fetchCurrentUser()` trả về `teacherUser`, đặt `window.history` tại `/admin`, render `App`, rồi chờ URL/nội dung màn đề xác nhận redirect về `/exams`.

- [ ] **Step 2: Chạy test để đặc tả hành vi hiện có**

Run: `npm test -- --run src/Layout.test.tsx src/App.test.tsx`

Expected: các test PASS với thay đổi dashboard do người dùng đã viết sẵn trong worktree. Đây là test hồi quy cho code có trước phiên triển khai, không phải một chu kỳ RED mới.

- [ ] **Step 3: Rà soát implementation hiện có**

Xác nhận `Layout.tsx` dùng `{ to: "/admin", label: "Quản trị" }`.

Xác nhận `App.tsx` tính `const isAdmin = user.role === "admin"` và có route:

```tsx
<Route path="/admin" element={isAdmin ? <AdminOverviewPage /> : <Navigate to="/exams" replace />} />
```

và dùng `isAdmin` cho route `/admin/teachers`.

- [ ] **Step 4: Chạy test để xác nhận GREEN**

Run: `npm test -- --run src/Layout.test.tsx src/App.test.tsx`

Expected: tất cả test PASS.

---

### Task 3: Kiểm thử và hoàn thiện dashboard

**Files:**
- Create: `frontend/src/pages/AdminOverviewPage.test.tsx`
- Modify: `frontend/src/pages/AdminOverviewPage.tsx`

**Interfaces:**
- Consumes: `listTeachers(): Promise<TeacherOut[]>` từ `frontend/src/api/admin.ts`.
- Produces: `AdminOverviewPage` với sáu thẻ và chip thống kê có ba trạng thái `loading | success | error`.

- [ ] **Step 1: Viết test dashboard trước**

Mock `listTeachers` và kiểm tra riêng:

```ts
expect(screen.getByText("Đang tải...")).toBeInTheDocument();
expect(await screen.findByText("2 giáo viên hoạt động")).toBeInTheDocument();
expect(await screen.findByText("Không tải được dữ liệu")).toBeInTheDocument();
expect(screen.getByRole("link", { name: /Tài khoản & phân quyền/ })).toHaveAttribute("href", "/admin/teachers");
```

Đồng thời xác nhận các thẻ chưa triển khai không có role `link`.

- [ ] **Step 2: Chạy test để xác nhận RED**

Run: `npm test -- --run src/pages/AdminOverviewPage.test.tsx`

Expected: case API lỗi FAIL vì code hiện tại quay lại chuỗi “Đang tải...”.

- [ ] **Step 3: Cài đặt trạng thái tường minh**

Đổi state sang discriminated union:

```ts
type TeacherStat =
  | { status: "loading" }
  | { status: "success"; activeCount: number }
  | { status: "error" };
```

Map chip: loading → `Đang tải...`, success → `${activeCount} giáo viên hoạt động`, error → `Không tải được dữ liệu`.

- [ ] **Step 4: Chạy test để xác nhận GREEN**

Run: `npm test -- --run src/pages/AdminOverviewPage.test.tsx`

Expected: tất cả test PASS.

- [ ] **Step 5: Xác minh toàn bộ frontend**

Run: `npm test -- --run && npm run lint && npm run build`

Expected: ba lệnh exit 0, không có test failure, lint error hoặc TypeScript/build error.

- [ ] **Step 6: Commit tính năng**

Run: `git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.app.json frontend/src/test frontend/src/Layout.tsx frontend/src/Layout.test.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pages/AdminOverviewPage.tsx frontend/src/pages/AdminOverviewPage.test.tsx && git commit -m "feat: hoàn thiện dashboard quản trị"`

Expected: commit chỉ chứa frontend dashboard và test infrastructure.

---

### Task 4: Cập nhật trạng thái dự án

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`

**Interfaces:**
- Produces: tài liệu khởi đầu phản ánh đúng 1A, 1B và phần đã hoàn thành của 1C.

- [ ] **Step 1: Cập nhật README**

Thay mô tả “giai đoạn ý tưởng + prototype” bằng trạng thái: lõi tạo đề trên MockAIProvider đã hoạt động, xuất DOCX đã nghiệm thu và Admin đã có quản lý tài khoản cùng dashboard tổng quan. Bổ sung lệnh `docker compose up --build` và URL frontend/backend.

- [ ] **Step 2: Cập nhật development plan**

Ghi dashboard tổng quan Admin đã hoàn thành nhưng các màn chỉnh sửa kho kiến thức, template, hình ảnh và cấu hình AI vẫn chờ 1D.

- [ ] **Step 3: Kiểm tra tài liệu và commit**

Run: `git diff --check && rg -n "ý tưởng \+ prototype|dashboard tổng quan" README.md docs/engineering/DEVELOPMENT_PLAN.vi.md`

Expected: `git diff --check` exit 0; README không còn mô tả lỗi thời; development plan có trạng thái dashboard.

Run: `git add README.md docs/engineering/DEVELOPMENT_PLAN.vi.md && git commit -m "doc: cập nhật trạng thái phát triển dự án"`

Expected: commit chỉ chứa hai tệp tài liệu.

---

### Task 5: Xác minh, push và tạo pull request

**Files:**
- Verify only; không sửa production files.

**Interfaces:**
- Produces: branch remote và draft PR vào default branch.

- [ ] **Step 1: Xác minh cuối**

Run: `npm test -- --run && npm run lint && npm run build` trong `frontend`.

Run: `git diff --check && git status -sb && git log --oneline origin/main..HEAD` tại repository root.

Expected: frontend checks exit 0; working tree sạch; log chỉ gồm các commit thuộc branch 1C.

- [ ] **Step 2: Push branch**

Run: `git push -u origin feat/1c-admin-teacher-accounts`

Expected: remote branch cập nhật thành công.

- [ ] **Step 3: Tạo draft PR**

Dùng GitHub connector nếu khả dụng; fallback là GitHub CLI. PR title: `feat: hoàn thiện quản trị tài khoản giáo viên và dashboard`. PR body nêu thay đổi, lý do, ảnh hưởng và các lệnh xác minh.

Expected: nhận URL draft PR trỏ vào default branch của repository.

# Admin Audit Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ghi và hiển thị lịch sử chỉ-đọc cho các thao tác Admin quản lý tài khoản giáo viên mà không lưu dữ liệu xác thực nhạy cảm.

**Architecture:** Model `AuditLog` append-only lưu snapshot actor/target và metadata JSON an toàn. Router tài khoản ghi audit trong cùng transaction với thay đổi nghiệp vụ; router audit riêng cung cấp API phân trang chỉ dành cho Admin. Frontend thêm API client, route và trang bảng audit có phân trang.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL JSONB, Pydantic 2, pytest, React 19, TypeScript strict, React Router 7, Vitest, Testing Library.

## Global Constraints

- Chỉ audit thao tác quản trị tài khoản giáo viên trong task này.
- Không lưu mật khẩu, password hash, session, token, request body hoặc giá trị họ tên cũ/mới.
- Audit và thay đổi nghiệp vụ phải commit/rollback trong cùng transaction.
- Không cung cấp API cập nhật hoặc xóa audit log.
- API danh sách sắp xếp `created_at DESC, id DESC`; `limit` từ 1 đến 100, mặc định 20; `offset` không âm.
- Commit dùng `feat:`, `fix:` hoặc `doc:`; branch là `feat/1c-audit-log`.

---

### Task 1: Model và migration audit log

**Files:**
- Create: `backend/app/models/audit.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/a71d10c9e4b2_add_audit_logs.py`
- Create: `backend/tests/test_audit.py`

**Interfaces:**
- Produces: `AuditLog` với các thuộc tính `id`, `created_at`, `actor_user_id`, `actor_email`, `action`, `target_type`, `target_id`, `target_label`, `details`.

- [ ] **Step 1: Viết test model trước**

Tạo `backend/tests/test_audit.py`, khởi tạo trực tiếp một `AuditLog`, commit và query lại; assert UUID actor/target, action và `details == {"changed_fields": ["full_name"]}`.

- [ ] **Step 2: Chạy test để xác nhận RED**

Run: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest tests/test_audit.py -q`

Expected: FAIL khi import `app.models.audit` vì model chưa tồn tại.

- [ ] **Step 3: Tạo model tối thiểu**

`AuditLog` kế thừa `Base`, dùng UUID PostgreSQL, `DateTime(timezone=True)` với `server_default=func.now()`, `String(100)` cho action/target type, `String(255)` cho snapshot label và `JSONB` với `default=dict`.

- [ ] **Step 4: Tạo migration**

Migration revision `a71d10c9e4b2`, down revision `f1af42b1bbf5`; tạo bảng và index ghép `created_at`, `id` phục vụ sort. `downgrade()` drop index rồi drop table.

- [ ] **Step 5: Chạy test để xác nhận GREEN**

Run: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest tests/test_audit.py -q`

Expected: PASS.

---

### Task 2: Ghi audit cùng transaction quản lý giáo viên

**Files:**
- Create: `backend/app/services/audit.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: model `AuditLog` từ Task 1, `User` actor và target.
- Produces: `record_audit_log(db: Session, *, actor: User, action: str, target: User, details: dict[str, object] | None = None) -> AuditLog`.

- [ ] **Step 1: Viết test RED cho tạo giáo viên**

Sau POST thành công, query `AuditLog` và assert một record `teacher.created`, actor là Admin đăng nhập, target là giáo viên vừa tạo, `details == {}`.

- [ ] **Step 2: Chạy test RED**

Run: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest tests/test_admin.py -k audit -q`

Expected: FAIL vì chưa có audit record.

- [ ] **Step 3: Cài helper và tích hợp create**

Helper chỉ tạo `AuditLog` và `db.add(log)`, không commit. `create_teacher` nhận `actor: User = Depends(require_admin)`, gọi `db.flush()` để có target id, record `teacher.created`, rồi `db.commit()`.

- [ ] **Step 4: Chạy test create GREEN**

Run lại test `-k audit`; expected PASS cho case create.

- [ ] **Step 5: Viết test RED cho update nhiều trường**

PATCH cùng lúc `full_name`, `is_active=false`, `password`; assert đúng ba action `teacher.updated`, `teacher.deactivated`, `teacher.password_reset`; details của update chỉ là `{"changed_fields": ["full_name"]}` và JSON serialize không chứa password/hash.

- [ ] **Step 6: Cài update audit tối thiểu**

Chụp `was_active` trước thay đổi. Sau khi áp dụng payload, thêm record theo các điều kiện:

```python
if "full_name" in data:
    record_audit_log(..., action="teacher.updated", details={"changed_fields": ["full_name"]})
if "is_active" in data and data["is_active"] != was_active:
    record_audit_log(..., action="teacher.activated" if data["is_active"] else "teacher.deactivated")
if password:
    record_audit_log(..., action="teacher.password_reset")
```

- [ ] **Step 7: Test lỗi không tạo audit**

Mở rộng test email trùng: đếm audit trước/sau request 409 và assert không tăng. Chạy toàn bộ `tests/test_admin.py` và `tests/test_audit.py`.

- [ ] **Step 8: Commit backend ghi log**

Run: `git add backend/app/models backend/app/services/audit.py backend/app/routers/admin.py backend/alembic/versions/a71d10c9e4b2_add_audit_logs.py backend/tests/test_admin.py backend/tests/test_audit.py && git commit -m "feat: thêm audit log cho quản lý giáo viên"`

---

### Task 3: API danh sách audit phân trang

**Files:**
- Create: `backend/app/schemas/audit.py`
- Create: `backend/app/routers/audit.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_audit.py`

**Interfaces:**
- Produces: `GET /admin/audit-logs?limit=20&offset=0` trả `AuditLogPage` gồm `items`, `total`, `limit`, `offset`.

- [ ] **Step 1: Viết test RED API**

Test chưa đăng nhập → 401, teacher → 403; Admin tạo nhiều giáo viên rồi GET với `limit=1&offset=1`, assert `total`, một item và thứ tự mới nhất trước. Test `limit=0`, `limit=101`, `offset=-1` trả 422.

- [ ] **Step 2: Chạy RED**

Run test API cụ thể; expected 404 vì router chưa tồn tại.

- [ ] **Step 3: Tạo schema và router**

`AuditLogOut` dùng `ConfigDict(from_attributes=True)`; `AuditLogPage` chứa `list[AuditLogOut]`. Router dùng `Query(20, ge=1, le=100)` và `Query(0, ge=0)`, count bằng `select(func.count()).select_from(AuditLog)` và list bằng order/offset/limit.

- [ ] **Step 4: Đăng ký router và chạy GREEN**

Import `audit` trong `main.py`, gọi `app.include_router(audit.router)`. Chạy `tests/test_audit.py`; expected PASS.

- [ ] **Step 5: Chạy toàn backend**

Run: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest -q`

Expected: tất cả test PASS.

- [ ] **Step 6: Commit API**

Run: `git add backend/app/schemas/audit.py backend/app/routers/audit.py backend/app/main.py backend/tests/test_audit.py && git commit -m "feat: thêm API danh sách audit log"`

---

### Task 4: Frontend API, route và dashboard

**Files:**
- Create: `frontend/src/types/audit.ts`
- Create: `frontend/src/api/audit.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/pages/AdminOverviewPage.tsx`
- Modify: `frontend/src/pages/AdminOverviewPage.test.tsx`

**Interfaces:**
- Produces: `listAuditLogs(limit: number, offset: number): Promise<AuditLogPage>` và link `/admin/audit-logs` chỉ dành cho Admin.

- [ ] **Step 1: Viết test RED dashboard và route**

Dashboard test assert có link `Audit log` tới `/admin/audit-logs`, tổng số link chức năng là 2 và copy là “2 khối”. App test đặt teacher tại `/admin/audit-logs` và assert redirect `/exams`.

- [ ] **Step 2: Chạy RED**

Run: `npm test -- --run src/App.test.tsx src/pages/AdminOverviewPage.test.tsx`

Expected: FAIL vì link/route chưa có.

- [ ] **Step 3: Tạo types/API và route**

Types phản ánh schema backend; API gọi `apiGet(`/admin/audit-logs?limit=${limit}&offset=${offset}`)`. Thêm route gate `isAdmin`. Mock trang audit trong App test để route import ổn định.

- [ ] **Step 4: Cập nhật dashboard**

Thêm card `Audit log`, `to: "/admin/audit-logs"`, `implemented: true`, chip `Lịch sử thao tác quản trị`; đổi copy thành “2 khối bên dưới đã có chức năng thật.”

- [ ] **Step 5: Chạy GREEN**

Run lại hai test; expected PASS.

---

### Task 5: Trang audit log và phân trang

**Files:**
- Create: `frontend/src/pages/AdminAuditLogsPage.tsx`
- Create: `frontend/src/pages/AdminAuditLogsPage.test.tsx`

**Interfaces:**
- Consumes: `listAuditLogs(20, offset)` từ Task 4.
- Produces: bảng audit và nút `Trang trước`, `Trang sau`.

- [ ] **Step 1: Viết test RED**

Mock API cho bốn case: Promise pending hiển thị `Đang tải...`; page rỗng hiển thị `Chưa có hoạt động nào`; rejected hiển thị `Không tải được audit log`; page có item hiển thị actor, target và nhãn action. Dùng user-event click `Trang sau`, assert API được gọi offset 20; assert disable trước ở offset 0 và sau khi `offset + items.length >= total`.

- [ ] **Step 2: Chạy RED**

Run: `npm test -- --run src/pages/AdminAuditLogsPage.test.tsx`

Expected: FAIL import vì page chưa tồn tại.

- [ ] **Step 3: Cài page tối thiểu**

State gồm `offset`, `page`, `loading`, `error`. `useEffect` gọi API khi offset đổi. Map action tiếng Việt; format thời gian bằng `toLocaleString("vi-VN")`; render `changed_fields` thành “Thay đổi: họ tên”, còn details rỗng hiển thị “—”.

- [ ] **Step 4: Chạy GREEN và toàn frontend**

Run: `npm test -- --run && npm run lint && npm run build`

Expected: tất cả exit 0.

- [ ] **Step 5: Commit frontend**

Run: `git add frontend/src/types/audit.ts frontend/src/api/audit.ts frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pages/AdminOverviewPage.tsx frontend/src/pages/AdminOverviewPage.test.tsx frontend/src/pages/AdminAuditLogsPage.tsx frontend/src/pages/AdminAuditLogsPage.test.tsx && git commit -m "feat: thêm màn hình audit log quản trị"`

---

### Task 6: Tài liệu, xác minh và publish

**Files:**
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`
- Modify: `docs/engineering/IMPLEMENTATION_NOTES.vi.md`

**Interfaces:**
- Produces: tài liệu trạng thái và draft PR riêng.

- [ ] **Step 1: Cập nhật tài liệu**

Tách checklist “Audit log, hạn mức”: đánh dấu audit log hoàn thành và giữ hạn mức chưa làm. Bổ sung tham chiếu nhanh model/action/API audit vào Implementation Notes.

- [ ] **Step 2: Commit tài liệu**

Run: `git diff --check && git add docs/engineering/DEVELOPMENT_PLAN.vi.md docs/engineering/IMPLEMENTATION_NOTES.vi.md && git commit -m "doc: cập nhật tiến độ audit log"`

- [ ] **Step 3: Xác minh cuối**

Backend: `$env:TEST_DATABASE_URL='postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test'; python -m pytest -q`.

Frontend: `npm test -- --run`, `npm run lint`, `npm run build`.

Git: `git diff --check`, `git status -sb`, `git log --oneline origin/main..HEAD`.

Expected: mọi command exit 0 và working tree sạch.

- [ ] **Step 4: Push và tạo draft PR**

Run: `git push -u origin feat/1c-audit-log`.

Tạo draft PR vào `main`, title `feat: thêm audit log quản trị`, body mô tả phạm vi, bảo mật transaction và kết quả test. Không merge hoặc xóa branch.

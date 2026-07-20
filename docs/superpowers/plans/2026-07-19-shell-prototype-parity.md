# Shell Prototype Parity Implementation Plan

**Goal:** Đồng bộ khung giao diện (sidebar tối, nav theo vai trò, user card, màn đăng nhập) với `prototype/index.html` + `styles.css`, giữ nguyên các trang bên trong và toàn bộ logic route/auth hiện có.

**Architecture:** Port token màu + class CSS của phần khung (không đụng phần class chỉ dùng cho trang trong) vào `frontend/src/index.css`; icon dựng lại bằng component React nhỏ thay vì sprite; viết lại `Layout.tsx`/`LoginForm.tsx` dùng class thay vì inline style, không đổi `App.tsx`.

**Tech Stack:** React 19, React Router, Vitest, Testing Library, TypeScript, oxlint.

## Global Constraints

- Không đổi route guard/redirect logic trong `App.tsx`.
- Không port trang trong (list/builder/review/export/admin dashboard) — chỉ khung.
- Vẫn 1 form login chung, không tách route login theo vai trò.
- Commit `doc: ...` rồi `feat: ...`, branch `feat/1c-shell-prototype-parity`.

---

### Task 0: Đặc tả và kế hoạch

- [x] Viết spec + plan.
- [x] Commit: `doc: đặc tả đồng bộ khung giao diện theo prototype`

### Task 1: CSS khung + icon

**Files:**
- Modify: `frontend/src/index.css`
- Add: `frontend/src/icons/Icon.tsx`

- [x] **Step 1:** Thêm token màu còn thiếu vào `:root` (surface-soft, border-strong, primary-soft, success*, shadow-*, radius) từ `prototype/styles.css`.
- [x] **Step 2:** Thêm `.app-shell`, `.sidebar`, `.brand*`, `.main-nav`, `.nav-item(.active)`, `.user-card`, `.avatar`, `.user-meta`, `.icon`, `.workspace`, `.button(.primary/.secondary/.compact/.large)`, reset `label/select/input/textarea`, responsive breakpoint co sidebar (giữ nguyên nội dung từ prototype, không đổi giá trị).
- [x] **Step 3:** Bỏ `#root { padding: 24px }`; sửa `.center-screen` tự có `padding: 24px; min-height: 100vh`.
- [x] **Step 4:** Tạo `Icon.tsx` với `DocIcon`, `LayersIcon`, `UsersIcon`, `BankIcon` (giữ nguyên toạ độ path/circle từ prototype).
- [x] **Step 5:** Commit: `feat: thêm token và class CSS khung giao diện theo prototype`

### Task 2: Viết lại Layout và LoginForm

**Files:**
- Modify: `frontend/src/Layout.tsx`
- Modify: `frontend/src/LoginForm.tsx`
- Modify: `frontend/src/Layout.test.tsx`
- Modify: `frontend/src/App.test.tsx` (nếu cần chỉnh selector)

- [x] **Step 1:** Chạy test hiện có để có baseline GREEN trước khi sửa: `npm test -- --run src/Layout.test.tsx src/App.test.tsx`.
- [x] **Step 2:** Viết lại `Layout.tsx`: `.app-shell` > `.sidebar` (brand, `.main-nav` theo bảng route Giáo viên/Admin, usage badge, user-card, nút đăng xuất) + `.main-content > .workspace > <Outlet />`. Giữ nguyên `UsageProvider` bọc ngoài.
- [x] **Step 3:** Viết lại `LoginForm.tsx` dùng `.button.primary.large` và class chung thay vì object style, không đổi logic state/gọi API.
- [x] **Step 4:** Chạy lại test, sửa assertion nếu cần (không đổi ý nghĩa test, chỉ theo cấu trúc DOM mới nếu có).
- [x] **Step 5:** Chạy `npm test -- --run`, `npm run lint`, `npm run build`.
- [ ] **Step 6:** Kiểm thử thủ công qua trình duyệt: đăng nhập Giáo viên và Admin, xác nhận sidebar/nav/avatar đúng vai trò, responsive ở màn hẹp. **Chưa làm** — môi trường agent không có công cụ trình duyệt/screenshot; cần chủ dự án tự kiểm tra bằng `docker compose up` hoặc `npm run dev` trước khi merge.
- [x] **Step 7:** Commit: `feat: đồng bộ sidebar và màn đăng nhập theo prototype`

### Task 3: Cập nhật tài liệu tiến độ

**Files:**
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`

- [x] **Step 1:** Ghi chú đã đồng bộ khung giao diện theo prototype (sidebar/login), còn lại port trang trong (builder/review/export/admin dashboard) để task sau.
- [x] **Step 2:** Commit: `doc: cập nhật tiến độ đồng bộ khung giao diện`

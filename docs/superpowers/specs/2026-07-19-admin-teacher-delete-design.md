# Thiết kế xóa cứng tài khoản giáo viên + bảng quản lý

## Mục tiêu

Trang "Quản lý giáo viên" hiện là danh sách dạng thẻ, thêm tài khoản qua form luôn hiển thị trên trang, và không có xóa (chỉ khóa/mở lại, theo quyết định gốc PRD 12 — ưu tiên xóa mềm cho dữ liệu có lịch sử). Chủ dự án yêu cầu: đổi sang bảng, thêm nút "Xóa" là xóa cứng thật sự, và nút "Thêm" mở popup thay vì form luôn hiện.

Đã xác nhận với chủ dự án: **xóa cứng thật**, không phải đổi tên nút khóa. Vì `Exam.teacher_id` là FK `NOT NULL` tới `users.id` không có `ON DELETE CASCADE`, xóa thẳng sẽ vỡ ràng buộc nếu giáo viên đã có đề. Quyết định: **chặn xóa nếu giáo viên còn đề thi** (trả `409` kèm số lượng đề, gợi ý khóa tài khoản thay vì xóa) — nhất quán với nguyên tắc "không mất dữ liệu có lịch sử" đã áp dụng cho audit log và tài liệu kho kiến thức.

`AuditLog.actor_user_id`/`target_id` không phải FK (chỉ lưu UUID + email/label snapshot tại thời điểm ghi) — xóa `User` không ảnh hưởng audit log cũ, không cần xử lý gì thêm ở đó.

## Backend

- `DELETE /admin/teachers/{teacher_id}` (router `admin.py`, cùng `require_admin`):
  - 404 nếu không tìm thấy giáo viên (dùng lại `_get_teacher`).
  - Đếm `Exam` có `teacher_id` này; nếu > 0 → `409` với `detail` nêu rõ số đề, ví dụ "Giáo viên còn 3 đề thi — khóa tài khoản thay vì xóa."
  - Nếu = 0: ghi audit log `action="teacher.deleted"` **trước** khi xóa (vì sau khi xóa không còn `target` object để truyền vào `record_audit_log`, nhưng hàm chỉ đọc `target.id`/`target.email` nên gọi trước `db.delete()` là đủ), rồi `db.delete(teacher)`, `db.commit()`.
  - Response `204 No Content`.

## Frontend

- `frontend/src/api/admin.ts`: thêm `deleteTeacher(id): Promise<void>` gọi `DELETE`.
- `frontend/src/components/Modal.tsx` (mới): component dựng trên `<dialog>` gốc (giống cách prototype dùng `<dialog class="block-editor">`), nhận `open`/`onClose`/`title`/`children`. Dùng lại cho cả 2 luồng: thêm tài khoản, đặt lại mật khẩu.
- `frontend/src/pages/AdminTeachersPage.tsx`: viết lại
  - Bảng (`<table className="data-table">`) thay cho danh sách thẻ: cột Họ tên, Email, Trạng thái (status pill), và cột hành động (Khóa/Mở lại, Đặt lại mật khẩu, Xóa).
  - Nút "+ Thêm tài khoản" ở đầu trang mở `Modal` chứa form tạo (email/họ tên/mật khẩu) — logic tạo giữ nguyên, chỉ đổi nơi hiển thị.
  - "Đặt lại mật khẩu" cũng chuyển vào `Modal` riêng (nhất quán về tương tác, tránh mở rộng hàng trong bảng gây khó style).
  - "Xóa": `window.confirm()` xác nhận trước khi gọi API (thao tác không thể hoàn tác, chưa cần dựng thêm 1 dialog riêng cho việc này — xác nhận trình duyệt là đủ cho thao tác admin nội bộ). Lỗi 409 hiển thị nguyên `detail` từ API (đã có số đề + gợi ý) qua state `error` sẵn có.
- CSS (`index.css`): thêm `.data-table`, `.status-pill(.active/.locked)`, `.app-modal*`, `.icon-button` — theo đúng bảng màu/spacing đã dùng cho sidebar (nhất quán, không tạo token mới).

## Không thuộc phạm vi

- Không đổi hành vi khóa/mở lại tài khoản hiện có.
- Không thêm xác nhận xóa dạng dialog tùy chỉnh (dùng `window.confirm` gốc trình duyệt).
- Không cho xóa khi còn đề — không có tùy chọn "xóa kèm xóa đề" ở lần này.
- Không đổi trang Audit log hay Tổng quan.

## Test

- Backend (`test_admin.py`): xóa thành công khi không có đề (204, DB không còn row, có audit log `teacher.deleted`); 409 khi còn đề (kèm assert message chứa số đề); 404 khi id không tồn tại; 403 khi gọi bằng tài khoản Giáo viên.
- Frontend (`AdminTeachersPage.test.tsx`, mới): render bảng đúng dữ liệu mock; mở modal thêm tài khoản và submit gọi đúng API; bấm Xóa sau khi xác nhận `confirm` gọi đúng API và reload danh sách; không gọi API khi `confirm` trả `false`.

## Tiêu chí hoàn thành

- `pytest backend/tests -q`, `npm test -- --run`, `npm run lint`, `npm run build` đều pass.
- Xóa giáo viên không có đề thành công qua UI; xóa giáo viên có đề bị chặn với thông báo rõ ràng.

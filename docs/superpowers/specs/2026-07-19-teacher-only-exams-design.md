# Thiết kế giới hạn đề thi cho Giáo viên

## Mục tiêu

Tách hoàn toàn workflow đề thi khỏi vai trò Admin. Chỉ Giáo viên được xem, tạo, chỉnh sửa, sinh, duyệt và xuất đề; Admin chỉ sử dụng các màn quản trị.

## Backend

- Thêm dependency `require_teacher = require_role(UserRole.TEACHER)` dùng chung.
- Toàn bộ router `/exams/*` chuyển từ `require_any_role` sang `require_teacher`.
- Admin gọi bất kỳ endpoint đề thi nào nhận HTTP `403` với thông báo phân quyền hiện có.
- Người chưa đăng nhập vẫn nhận `401`; tài khoản Giáo viên giữ nguyên hành vi ownership `403/404` hiện tại.
- API catalog tiếp tục cho cả Admin và Giáo viên để không chặn các màn quản trị kho kiến thức trong tương lai.
- `/usage/me` giữ dependency hiện tại để tránh thay đổi API ngoài phạm vi; frontend Admin không gọi endpoint này và service vẫn thể hiện Admin không có quota. Task không bổ sung luồng quota mới cho Admin.

## Frontend

- Route mặc định theo vai trò: Admin vào `/admin`, Giáo viên vào `/exams`.
- Admin mở `/exams` hoặc mọi route con `/exams/:examId/builder|review|export` sẽ được chuyển về `/admin` trước khi mount page đề thi, do đó không phát sinh request API đề.
- Giáo viên mở `/admin`, `/admin/teachers` hoặc `/admin/audit-logs` tiếp tục được chuyển về `/exams`.
- Route không tồn tại chuyển về trang mặc định theo vai trò.
- Header Admin chỉ có liên kết `Quản trị`; logo dẫn `/admin`.
- Header Giáo viên chỉ có liên kết `Đề của tôi`; logo dẫn `/exams`.
- `UsageProvider` tiếp tục không tải quota cho Admin.

## Dữ liệu

Không xóa hoặc chuyển quyền các đề từng được Admin tạo. Sau thay đổi, các bản ghi này vẫn tồn tại nhưng không thể truy cập qua API đề thi bằng tài khoản Admin.

## Kiểm thử

### Backend

- Đăng nhập Admin và xác nhận `GET /exams`, `POST /exams` cùng một endpoint con đại diện đều trả `403`.
- Xác nhận Giáo viên vẫn tạo và truy cập đề bình thường qua các test hiện có.
- Xác nhận người chưa đăng nhập vẫn nhận `401`.

### Frontend

- Admin đăng nhập ở `/`, `/exams` và route con của đề đều kết thúc tại `/admin` và không mount component đề.
- Header Admin không có `Đề của tôi`; logo và liên kết quản trị trỏ `/admin`.
- Giáo viên giữ nguyên route mặc định `/exams`, menu đề và chặn route Admin.
- Usage API không được gọi cho Admin.

## Không thuộc phạm vi

- Không tạo trang Admin xem đề read-only.
- Không xóa đề cũ của Admin.
- Không sửa catalog, audit log, quản lý giáo viên, quota hoặc schema database.
- Không tạo migration.

## Tiêu chí hoàn thành

- Phân quyền được khóa ở cả frontend và backend.
- Không còn đường điều hướng Admin nào tới workflow đề thi.
- Toàn bộ backend tests, frontend tests, lint và build đều đạt.

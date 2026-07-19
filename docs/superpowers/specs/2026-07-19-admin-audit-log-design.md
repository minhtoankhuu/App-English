# Đặc tả audit log quản trị

## Mục tiêu

Ghi lại các thao tác quản trị tài khoản giáo viên theo dạng lịch sử chỉ-đọc để Admin có thể truy vết ai đã thực hiện thay đổi, vào thời điểm nào và thay đổi loại thông tin nào mà không làm lộ dữ liệu xác thực.

## Phạm vi

Task này chỉ audit các thao tác trên API `/admin/teachers`:

- Tạo tài khoản giáo viên: `teacher.created`.
- Đổi họ tên: `teacher.updated`.
- Khóa tài khoản: `teacher.deactivated`.
- Mở lại tài khoản: `teacher.activated`.
- Đặt lại mật khẩu: `teacher.password_reset`.

Một request cập nhật nhiều thuộc tính tạo một audit record cho mỗi ý nghĩa nghiệp vụ xảy ra. Ví dụ đổi tên, khóa và đặt lại mật khẩu trong cùng request tạo ba record. Request thất bại hoặc transaction bị rollback không được tạo record.

Không audit vòng đời đề thi, đăng nhập/đăng xuất, request đọc dữ liệu, chi phí AI hoặc hạn mức trong task này.

## Mô hình dữ liệu

Bảng `audit_logs` là append-only ở tầng ứng dụng và gồm:

- `id`: UUID khóa chính.
- `created_at`: thời điểm database tạo record.
- `actor_user_id`: UUID Admin thực hiện thao tác.
- `actor_email`: snapshot email Admin để lịch sử vẫn đọc được nếu thông tin tài khoản thay đổi.
- `action`: mã hành động ổn định.
- `target_type`: giá trị `teacher` trong phạm vi task này.
- `target_id`: UUID tài khoản giáo viên bị tác động.
- `target_label`: snapshot email giáo viên.
- `details`: JSON object chứa metadata an toàn.

`actor_user_id` và `target_id` không dùng foreign key có hành vi cascade, tránh lịch sử bị xóa theo tài khoản. Không có endpoint cập nhật hoặc xóa audit log.

## Quy tắc dữ liệu nhạy cảm

Audit log không được chứa mật khẩu thô, password hash, session cookie, toàn bộ request body hoặc token. Với `teacher.password_reset`, `details` là object rỗng. Với đổi tên, `details.changed_fields` chỉ chứa `["full_name"]`; không lưu giá trị cũ hoặc mới. Với kích hoạt/khóa, action đã biểu đạt trạng thái nên `details` là object rỗng.

## Ghi log và transaction

Router Admin nhận `actor: User = Depends(require_admin)` thay cho việc chỉ dùng dependency ở cấp router. Hàm dịch vụ `record_audit_log(db, actor, action, target, details)` chỉ `db.add()` và không tự commit.

Tạo/cập nhật giáo viên và các audit record tương ứng được flush rồi commit trong cùng một transaction. Nếu commit thất bại, dữ liệu nghiệp vụ và audit cùng rollback. Trường hợp email trùng trả 409 và không để lại audit record.

## API đọc audit

Endpoint `GET /admin/audit-logs` chỉ dành cho Admin, trả object:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

- `limit`: mặc định 20, nhỏ nhất 1, lớn nhất 100.
- `offset`: mặc định 0, nhỏ nhất 0.
- Sắp xếp `created_at DESC, id DESC` để kết quả ổn định.
- Giáo viên nhận 403; chưa đăng nhập nhận 401.

## Frontend

- Bổ sung thẻ “Audit log” hoạt động trên dashboard `/admin` và cập nhật câu mô tả số khối đã triển khai.
- Thêm route `/admin/audit-logs`, gate bằng cùng điều kiện `isAdmin` như các route Admin khác.
- Trang audit hiển thị bảng: thời gian, người thực hiện, hành động, tài khoản đích và nội dung thay đổi.
- Nhãn hành động được dịch sang tiếng Việt; action chưa biết hiển thị nguyên mã để tương thích dữ liệu tương lai.
- Có trạng thái loading, danh sách rỗng và lỗi.
- Phân trang bằng nút “Trang trước” và “Trang sau”; nút được disable theo `offset` và `total`.
- Không thêm filter, tìm kiếm, export hoặc trang chi tiết trong task này.

## Kiểm thử và nghiệm thu

Backend test-first:

- Migration tạo đúng bảng và model được nhận diện.
- Tạo giáo viên sinh `teacher.created` với đúng actor/target.
- Đổi tên, khóa/mở và đặt lại mật khẩu sinh đúng action.
- Request nhiều thay đổi sinh đủ record.
- Email trùng hoặc request lỗi không sinh audit.
- Chuỗi serialize của audit không chứa mật khẩu hoặc hash.
- API chỉ Admin truy cập, trả đúng tổng số, thứ tự và phân trang.

Frontend test-first:

- Dashboard có link Audit log và đúng số khối chức năng thật.
- Giáo viên không truy cập được `/admin/audit-logs`.
- Trang hiển thị loading, dữ liệu, rỗng, lỗi và trạng thái nút phân trang.

Trước commit/push phải chạy backend pytest, frontend Vitest, lint, production build và `git diff --check`.

## Chiến lược Git

- Branch: `feat/1c-audit-log`.
- Commit tài liệu: `doc: đặc tả audit log quản trị` và `doc: lập kế hoạch audit log quản trị`.
- Commit backend: `feat: thêm audit log cho quản lý giáo viên`.
- Commit frontend: `feat: thêm màn hình audit log quản trị`.
- Commit trạng thái kế hoạch nếu cần: `doc: cập nhật tiến độ audit log`.
- Push branch và tạo draft PR riêng vào `main`; không đưa task hạn mức vào PR này.

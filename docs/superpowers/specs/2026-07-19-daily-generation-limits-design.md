# Đặc tả hạn mức sinh đề hằng ngày

## Mục tiêu

Giới hạn mỗi giáo viên tối đa 10 lượt gọi sinh nội dung AI trong một ngày theo múi giờ `Asia/Bangkok`, chặn an toàn trước khi gọi provider khi không đủ lượt và cho giáo viên biết số lượt còn lại. Cơ chế phải hoạt động với `MockAIProvider` hiện tại và giữ được ranh giới phù hợp để nối token/chi phí thật ở Giai đoạn 1D.

## Phạm vi và cách tính lượt

- Giáo viên có 10 lượt mỗi ngày dương lịch theo `Asia/Bangkok`.
- Sinh toàn đề qua `POST /exams/{id}/generate` tiêu thụ một lượt cho mỗi block thực sự được yêu cầu sinh.
- Sinh lại một câu qua `POST /exams/{id}/questions/{question_id}/regenerate` tiêu thụ một lượt.
- Một request sinh toàn đề là nguyên tử về quota: nếu đề có 4 block nhưng chỉ còn 3 lượt, hệ thống trả 429 trước khi sinh block đầu tiên.
- Tạo/sửa đề, CRUD/reorder block, chọn grammar, duyệt/khóa câu, hoàn tất kiểm duyệt, cấu hình xuất và tải DOCX không tiêu thụ lượt.
- Admin được miễn hạn mức; các request sinh của Admin không tạo hoặc tăng bộ đếm.

Task này không theo dõi token, tiền thật, thời gian provider, quota theo model, cấp thêm lượt thủ công hoặc cấu hình riêng cho từng giáo viên.

## Cấu hình và múi giờ

- Biến cấu hình `DAILY_GENERATION_LIMIT`, mặc định `10`, phải là số nguyên dương.
- Múi giờ quota cố định `Asia/Bangkok` trong phiên bản này.
- `usage_date` là ngày địa phương tại thời điểm giữ lượt.
- `reset_at` là đầu ngày kế tiếp tại Bangkok, serialize ISO 8601 có offset `+07:00`.

## Mô hình dữ liệu

Bảng `daily_usage` gồm:

- `id`: UUID khóa chính.
- `user_id`: UUID giáo viên.
- `usage_date`: `DATE` theo Bangkok.
- `used_count`: số nguyên không âm.
- `created_at`, `updated_at`.
- Unique constraint `(user_id, usage_date)`.

Không cần lưu một record cho mỗi lượt ở task này. Audit log quản trị tài khoản không được dùng làm nguồn quota.

## Giữ và hoàn lượt

Service quota cung cấp:

- `get_usage_status(db, user, now=None) -> UsageStatus`.
- `reserve_usage(db, user, amount, now=None) -> UsageReservation`.

`amount` phải lớn hơn 0. Với giáo viên, service bảo đảm row tồn tại bằng PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`, sau đó khóa row bằng `SELECT ... FOR UPDATE`, kiểm tra `used_count + amount <= limit`, tăng bộ đếm rồi flush. Hai request đầu ngày vì vậy hội tụ vào cùng một row và serialize tại row lock.

Router giữ quota trước khi gọi provider. Nếu toàn bộ thao tác sinh thành công, quota và câu hỏi được commit. Nếu provider hoặc validation phát sinh exception, transaction rollback cả câu hỏi và lượt giữ. Code generation không được commit độc lập ngoài transaction.

Admin nhận reservation bypass và không chạm database quota.

## Hành vi khi hết lượt

Không đủ lượt trả HTTP 429 với body:

```json
{
  "detail": {
    "message": "Bạn đã hết lượt sinh hôm nay",
    "limit": 10,
    "used": 10,
    "remaining": 0,
    "reset_at": "2026-07-20T00:00:00+07:00"
  }
}
```

Nếu còn lượt nhưng không đủ cho request nhiều block, `used` và `remaining` phản ánh trạng thái trước request; không trừ một phần.

## API trạng thái

`GET /usage/me` yêu cầu đăng nhập và trả:

```json
{
  "limit": 10,
  "used": 3,
  "remaining": 7,
  "usage_date": "2026-07-19",
  "reset_at": "2026-07-20T00:00:00+07:00",
  "is_unlimited": false
}
```

Với Admin: `used=0`, `remaining=10`, `is_unlimited=true`; các con số phục vụ schema ổn định nhưng UI không hiển thị badge cho Admin.

## Tích hợp backend

- Router generate/regenerate nhận actor từ `require_any_role` hiện có.
- Sinh toàn đề xác định số block trước khi reserve; đề không có block tiếp tục dùng validation nghiệp vụ hiện tại và không tiêu thụ lượt.
- Regenerate vẫn kiểm tra quyền sở hữu, trạng thái locked/approved và dữ liệu câu trước khi reserve để request 404/409 không mất lượt.
- Service generation không tự quản quota; quota nằm tại boundary router để provider interface không phụ thuộc user/session.
- CORS và auth hiện có không thay đổi.

## Frontend

- Thêm API `getMyUsage()` và type `UsageStatus`.
- `Layout` tải usage cho giáo viên và hiển thị badge `Còn X/10 lượt hôm nay`; Admin không gọi endpoint từ Layout.
- Layout cung cấp cơ chế refresh usage cho các trang con thông qua React context nhỏ, tránh truyền callback qua mọi route.
- `ExamBuilderPage` refresh quota sau generate thành công.
- `ExamReviewPage` refresh quota sau regenerate thành công.
- Khi API trả 429 có detail object, `ApiError` giữ payload quota có kiểu an toàn; trang hiển thị message và thời gian reset. Các lỗi string hiện tại vẫn hoạt động.
- Khi remaining bằng 0, nút sinh/sinh lại được disable sau khi usage load; backend tiếp tục bảo vệ khi tab cũ hoặc hai request đồng thời.
- Lỗi tải badge không chặn sử dụng trang; hiển thị `Không tải được hạn mức` và backend quyết định request sinh.

## Kiểm thử

Backend test-first:

- Cấu hình mặc định 10 và reject giá trị không dương.
- Ngày/reset theo Bangkok tại ranh giới UTC.
- Status ban đầu, reserve và unique `(user_id, usage_date)`.
- Sinh N block tăng N; regenerate tăng 1.
- Không đủ lượt trả đúng 429 và không tạo câu/trừ một phần.
- Request 404/409 không tiêu thụ lượt.
- Exception provider rollback quota và câu hỏi.
- Request cạnh tranh không vượt 10.
- Admin bypass và `/usage/me` đúng phân quyền/schema.

Frontend test-first:

- Layout chỉ tải/hiển thị quota cho giáo viên, có loading/error/unlimited behavior đúng.
- ApiError parse được detail object 429 mà không phá lỗi string.
- Builder/review refresh sau thành công và disable khi remaining 0.
- Thông báo hết lượt và thời gian reset hiển thị rõ.

Trước push phải chạy migration upgrade/downgrade/upgrade trên database test, toàn bộ pytest, Vitest, lint, production build và `git diff --check`.

## Chiến lược Git

- Branch: `feat/1c-usage-limits`.
- `doc: đặc tả hạn mức sinh đề`.
- `doc: lập kế hoạch hạn mức sinh đề`.
- `feat: thêm hạn mức sinh đề hằng ngày` cho backend.
- `feat: hiển thị hạn mức sinh đề` cho frontend.
- `doc: cập nhật tiến độ hạn mức sử dụng`.
- Push branch và tạo draft PR riêng vào `main` sau khi xác minh; không merge hoặc xóa branch.

# Đặc tả dashboard quản trị

## Mục tiêu

Hoàn thiện trang tổng quan dành riêng cho Admin để người quản trị nhìn thấy các phân hệ của hệ thống, truy cập chức năng quản lý tài khoản giáo viên đã triển khai và nhận biết rõ các phân hệ chưa sẵn sàng.

## Phạm vi

- Thêm route `/admin` trong frontend.
- Chỉ người dùng có vai trò `admin` được xem route; giáo viên được chuyển về `/exams`.
- Đổi mục điều hướng dành cho Admin từ liên kết trực tiếp “Quản lý tài khoản” thành “Quản trị”, trỏ tới `/admin`.
- Hiển thị sáu thẻ phân hệ: kho kiến thức và RAG, danh mục học thuật, dạng bài và template, thư viện hình ảnh, cấu hình AI, tài khoản và phân quyền.
- Chỉ thẻ “Tài khoản & phân quyền” là liên kết hoạt động và dẫn tới `/admin/teachers`.
- Tải danh sách giáo viên qua API hiện có để tính số giáo viên đang hoạt động.
- Hiển thị riêng ba trạng thái của thống kê giáo viên: đang tải, tải thành công và không tải được dữ liệu.
- Cập nhật README để mô tả đúng trạng thái triển khai hiện tại.

Không bổ sung API thống kê mới, route placeholder cho các phân hệ chưa triển khai hoặc chức năng thuộc RAG/LLM trong task này.

## Kiến trúc và thành phần

`App.tsx` chịu trách nhiệm khai báo route và gate vai trò. `Layout.tsx` chỉ xây dựng điều hướng theo vai trò. `AdminOverviewPage.tsx` chịu trách nhiệm trình bày dashboard và gọi `listTeachers()` từ lớp API hiện có; trang không truy cập trực tiếp HTTP client.

Dữ liệu các thẻ được khai báo trong một danh sách có kiểu rõ ràng. Thẻ có `to` được render bằng `Link`; thẻ chưa triển khai là phần tử tĩnh, giảm độ nổi bật và không có hành vi click.

## Luồng dữ liệu và lỗi

Khi trang mount, trạng thái thống kê bắt đầu ở `loading`. Lời gọi `listTeachers()` thành công sẽ lọc `is_active === true` và hiển thị tổng số. Nếu lời gọi thất bại, trang vẫn hiển thị bình thường và chip tài khoản chuyển thành “Không tải được dữ liệu”; lỗi thống kê không chặn điều hướng đến màn quản lý tài khoản.

## Kiểm thử và nghiệm thu

- Kiểm thử frontend xác nhận Admin nhìn thấy liên kết “Quản trị”, còn giáo viên không thấy.
- Kiểm thử route xác nhận giáo viên không thể xem `/admin` và bị chuyển về `/exams`.
- Kiểm thử dashboard xác nhận trạng thái tải, số giáo viên hoạt động sau khi API thành công và thông báo lỗi khi API thất bại.
- Chạy toàn bộ frontend tests, `npm run lint` và `npm run build` trước khi commit tính năng.
- Kiểm tra `git diff` để chỉ đưa các tệp thuộc dashboard và tài liệu liên quan vào commit.

## Chiến lược Git

Tiếp tục trên branch `feat/1c-admin-teacher-accounts` vì dashboard là phần hoàn thiện trải nghiệm quản trị của hạng mục 1C đang có. Các commit dùng Conventional Commits theo quy ước dự án:

- `doc: đặc tả dashboard quản trị`
- `feat: hoàn thiện dashboard quản trị`
- `doc: cập nhật trạng thái phát triển dự án`

Sau khi xác minh, push branch lên `origin` và tạo draft pull request vào branch mặc định của repository.

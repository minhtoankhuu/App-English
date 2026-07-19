# Thiết kế cập nhật README hướng dẫn chạy

## Mục tiêu

Giúp người mới clone repository có thể chạy và kiểm tra ExamCraft AI bằng Docker Compose mà không phải suy đoán cấu hình, tài khoản đăng nhập hoặc lệnh vận hành.

## Phạm vi

- Giữ Docker Compose là cách chạy chuẩn duy nhất trong README.
- Nêu yêu cầu Git và Docker Desktop.
- Hướng dẫn clone repository, tạo `.env` từ `.env.example`, build và khởi động dịch vụ.
- Nêu URL frontend, backend, health check và tài khoản Admin lấy từ `.env`.
- Giải thích migration và seed tự chạy khi backend khởi động.
- Thêm lệnh xem trạng thái/log, dừng dịch vụ và reset database có cảnh báo mất dữ liệu.
- Bổ sung lệnh chạy test backend và frontend.
- Thêm xử lý ngắn cho lỗi Docker chưa chạy, trùng cổng và frontend không gọi được backend.
- Sửa nhãn phiên bản đặc tả sản phẩm từ v1.3 thành v1.6.

## An toàn thông tin

README chỉ dùng giá trị mẫu trong `.env.example`. Email và mật khẩu Admin local thật không được ghi vào tài liệu hoặc commit.

## Tiêu chí hoàn thành

- Các lệnh và đường dẫn khớp với `docker-compose.yml`, Dockerfile và package scripts hiện tại.
- Markdown không có liên kết nội bộ hỏng hoặc thông tin đăng nhập thật.
- Thay đổi chỉ gồm tài liệu.

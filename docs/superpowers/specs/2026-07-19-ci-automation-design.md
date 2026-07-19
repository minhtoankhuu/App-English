# Thiết kế tự động hoá golden test (CI)

## Mục tiêu

Hoàn thành mục còn lại của Giai đoạn 1C: "Golden test tự động hoá (hiện đang là test thủ công trong pytest)". Hiện repo **chưa có CI nào** (`.github/workflows/` không tồn tại) — toàn bộ `pytest backend/tests` (bao gồm golden flow Unit 3) và `npm test`/`lint`/`build` ở frontend đều phải chạy tay. Task này thêm GitHub Actions để tự động chạy các bước đó trên mỗi push/PR vào `main`.

Phạm vi chỉ là **tự động hoá việc chạy test đã có**, không viết thêm test mới, không đổi golden flow.

## Thiết kế

Một workflow `.github/workflows/ci.yml`, 2 job chạy song song:

### Job `backend`
- Runner `ubuntu-latest`, service container `postgres` dùng image `pgvector/pgvector:pg16` (khớp `docker-compose.yml`), user/password/db `examcraft`/`examcraft`/`examcraft`, port map `5432:5432`, healthcheck `pg_isready`.
- Cài Python 3.12 (khớp `backend/Dockerfile`), `pip install -r requirements-dev.txt`.
- Tạo database `examcraft_test` bằng `psql` (README đã ghi bước này là thủ công — CI phải tự làm thay vì cần Actions cache sẵn).
- Chạy `pytest -q` với `TEST_DATABASE_URL` trỏ vào `examcraft_test` trên `localhost:5432` (service container map ra host runner).

### Job `frontend`
- Runner `ubuntu-latest`, Node 22 (khớp `frontend/Dockerfile`), cache npm theo `package-lock.json`.
- `npm ci`, rồi tuần tự `npm run lint`, `npm test -- --run`, `npm run build`.

Hai job độc lập, không phụ thuộc nhau — fail sớm ở job nào thì job kia vẫn chạy xong để thấy đủ lỗi trong 1 lần push.

## Trigger

`push` và `pull_request` nhắm `main` — đủ để thấy PR có test đỏ trước khi merge (repo hiện dùng luồng PR thủ công, chủ dự án tự bấm merge sau khi review).

## Không thuộc phạm vi

- Không thêm test mới, không đổi golden flow hay bất kỳ file test hiện có.
- Không cấu hình branch protection rule bắt buộc CI pass mới merge được (đó là cài đặt GitHub repo settings, ngoài phạm vi thay đổi code — chủ dự án tự bật nếu muốn sau khi thấy CI chạy ổn).
- Không đóng gói VPS (phần còn lại của cùng gạch đầu dòng 1C, để task riêng).
- Không thêm lint/type-check backend (repo hiện không có cấu hình ruff/mypy).

## Tiêu chí hoàn thành

- Workflow chạy xanh trên nhánh hiện tại (kiểm tra qua `gh run` hoặc tab Actions sau khi push).
- Cả 2 job pass với đúng bộ test hiện có (81 backend, toàn bộ frontend).

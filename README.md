# ExamCraft AI — Nền tảng AI tạo đề tiếng Anh

Ứng dụng web cho giáo viên tạo bài tập/đề tiếng Anh, kiểm duyệt từng câu và xuất DOCX A4. Lõi tạo đề hiện chạy trên `MockAIProvider`; luồng tạo đề, duyệt câu, mã đề A/B/C/D và xuất DOCX đã được nghiệm thu. Admin đã có dashboard tổng quan và chức năng quản lý tài khoản giáo viên. Kho kiến thức RAG và LLM thật được dành cho giai đoạn tiếp theo.

## Yêu cầu

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) đang chạy
- Để chạy kiểm thử ngoài Docker: Python 3.12 và Node.js 22 trở lên

## Chạy ứng dụng lần đầu

### Windows PowerShell

```powershell
git clone https://github.com/minhtoankhuu/App-English.git
cd App-English
Copy-Item .env.example .env
docker compose up --build
```

### macOS/Linux

```bash
git clone https://github.com/minhtoankhuu/App-English.git
cd App-English
cp .env.example .env
docker compose up --build
```

Lần build đầu có thể mất vài phút. Khi backend khởi động, ứng dụng tự chạy Alembic migration và seed các danh mục học thuật cùng tài khoản Admin; không cần chạy migration bằng tay.

Sau khi các container sẵn sàng:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>

### Đăng nhập Admin

Thông tin đăng nhập được cấu hình trong file `.env`:

```dotenv
SEED_ADMIN_EMAIL=admin@examcraft.dev
SEED_ADMIN_PASSWORD=ChangeMe123!
```

Đây là giá trị mẫu dành cho môi trường local. Hãy thay đổi email, mật khẩu và `SESSION_SECRET` trước khi triển khai môi trường thật. Không commit file `.env`.

> Tài khoản Admin chỉ được seed khi database chưa có Admin. Nếu đổi các biến seed sau lần chạy đầu, dữ liệu Admin hiện có không tự đổi theo.

## Vận hành bằng Docker Compose

Xem trạng thái các dịch vụ:

```bash
docker compose ps
```

Theo dõi log backend:

```bash
docker compose logs -f backend
```

Dừng và xóa container, giữ nguyên dữ liệu database:

```bash
docker compose down
```

Để khởi động lại:

```bash
docker compose up
```

> **Cảnh báo:** Lệnh sau xóa volume PostgreSQL local và toàn bộ tài khoản, đề thi, audit log cùng dữ liệu đã tạo. Chỉ dùng khi thật sự muốn khởi tạo lại từ đầu.

```bash
docker compose down -v
docker compose up --build
```

## Chạy kiểm thử

### Backend

Khi PostgreSQL container đang chạy, tạo database test riêng (chỉ cần chạy lệnh đầu một lần). Nếu `createdb` báo database đã tồn tại, có thể bỏ qua.

Windows PowerShell:

```powershell
docker compose exec db createdb -U examcraft examcraft_test
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test"
.\.venv\Scripts\python -m pytest -q
```

macOS/Linux:

```bash
docker compose exec db createdb -U examcraft examcraft_test
cd backend
python3.12 -m venv .venv
./.venv/bin/python -m pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test ./.venv/bin/python -m pytest -q
```

Các giá trị kết nối trên khớp `.env.example`; nếu đã đổi credential hoặc port PostgreSQL, hãy thay chúng trong URL. Production backend image không chứa thư mục `tests`, vì vậy pytest được chạy từ source trên máy host.

> Bộ test tạo và xóa bảng trong `examcraft_test`. Không trỏ `TEST_DATABASE_URL` vào database ứng dụng hoặc database production.

### Frontend

```bash
cd frontend
npm ci
npm test -- --run
npm run lint
npm run build
```

## Xử lý lỗi thường gặp

### Không kết nối được Docker

Mở Docker Desktop, chờ Docker Engine sẵn sàng rồi chạy lại `docker compose up --build`.

### Cổng đã được sử dụng

Ứng dụng dùng các cổng `5173` (frontend), `8000` (backend) và `5432` (PostgreSQL). Hãy dừng tiến trình/container đang dùng cổng tương ứng hoặc đổi port mapping trong `docker-compose.yml`.

### Backend báo thiếu Alembic revision

Backend image có thể được build từ source cũ trong khi database đã ở migration mới hơn. Rebuild image từ source hiện tại:

```bash
docker compose up --build
```

### Frontend không gọi được backend

Kiểm tra `VITE_API_BASE_URL` trong `.env`; với môi trường local mặc định, giá trị là `http://localhost:8000`. Vite đưa biến này vào bundle lúc build, vì vậy cần chạy lại:

```bash
docker compose up --build frontend
```

## Bắt đầu từ đâu

| Muốn... | Xem |
|---|---|
| Đọc đặc tả sản phẩm đầy đủ (v1.6) | [docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md](docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md) |
| Hiện trạng, prototype và nhật ký quyết định | Mục 23 của đặc tả trên |
| Bắt tay vào code: seed data, thông số DOCX, hành vi UI | [docs/engineering/IMPLEMENTATION_NOTES.vi.md](docs/engineering/IMPLEMENTATION_NOTES.vi.md) |
| Hướng đi và lộ trình phát triển đã chốt | [docs/engineering/DEVELOPMENT_PLAN.vi.md](docs/engineering/DEVELOPMENT_PLAN.vi.md) |
| Xem prototype giao diện | Mở `prototype/index.html` bằng trình duyệt (không cần server) |

## Build tài liệu DOCX

Đặc tả DOCX được sinh tự động từ file Markdown — không sửa tay file `.docx`:

```bash
pip install python-docx   # lần đầu
python tools/build_project_idea_docx.py
```

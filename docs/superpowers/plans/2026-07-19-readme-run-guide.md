# README Run Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cập nhật README để người mới clone repository có thể cấu hình, chạy, kiểm tra và xử lý lỗi cơ bản của ExamCraft AI bằng Docker Compose.

**Architecture:** `README.md` là điểm vào duy nhất cho luồng chạy chuẩn. Nội dung lấy giá trị mẫu từ `.env.example`, lệnh từ `docker-compose.yml` và package scripts; không sao chép thông tin đăng nhập local thật.

**Tech Stack:** Markdown, Docker Compose, FastAPI/pytest, React/Vitest/oxlint/TypeScript.

## Global Constraints

- Chỉ thay đổi tài liệu; không thay đổi mã nguồn, dependency hoặc cấu hình runtime.
- Docker Compose là cách chạy ứng dụng chuẩn duy nhất trong README.
- Không ghi email hoặc mật khẩu Admin local thật vào Git.
- Lệnh reset database phải cảnh báo xóa toàn bộ dữ liệu local.
- Commit theo cấu trúc `doc: ...`.

---

### Task 1: Viết lại hướng dẫn chạy trong README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `.env.example`, `docker-compose.yml`, `backend/requirements-dev.txt`, `frontend/package.json`.
- Produces: hướng dẫn chạy và kiểm tra dành cho developer.

- [ ] **Step 1: Cập nhật phần giới thiệu và phiên bản tài liệu**

Giữ mô tả trạng thái sản phẩm hiện tại và đổi nhãn liên kết PRD từ `v1.3` thành `v1.6`.

- [ ] **Step 2: Thêm yêu cầu và luồng khởi động lần đầu**

README phải hướng dẫn chính xác:

```powershell
git clone https://github.com/minhtoankhuu/App-English.git
cd App-English
Copy-Item .env.example .env
docker compose up --build
```

Kèm biến thể macOS/Linux:

```bash
cp .env.example .env
docker compose up --build
```

Nêu rõ backend tự chạy Alembic migration và seed dữ liệu khi khởi động.

- [ ] **Step 3: Ghi URL và cách đăng nhập Admin an toàn**

Liệt kê frontend `http://localhost:5173`, backend `http://localhost:8000`, health check `http://localhost:8000/health`. Tài khoản Admin được đọc từ `SEED_ADMIN_EMAIL` và `SEED_ADMIN_PASSWORD` trong `.env`; không ghi thông tin local thật.

- [ ] **Step 4: Thêm lệnh vận hành**

```bash
docker compose ps
docker compose logs -f backend
docker compose down
docker compose down -v
```

Đặt cảnh báo ngay trước `docker compose down -v`: lệnh xóa database local và toàn bộ dữ liệu đã tạo.

- [ ] **Step 5: Bổ sung kiểm tra backend và frontend**

Backend dùng PostgreSQL test database trong Docker nhưng chạy pytest từ source trên máy host, vì production image loại thư mục `tests` qua `.dockerignore`.

```powershell
docker compose exec db createdb -U examcraft examcraft_test
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test"
.\.venv\Scripts\python -m pytest -q
```

Thêm biến thể macOS/Linux dùng `python3.12`, `./.venv/bin/python` và biến môi trường inline. Ghi rõ lỗi database đã tồn tại có thể bỏ qua; nếu đổi credential PostgreSQL so với `.env.example` thì phải thay giá trị trong URL. Cảnh báo không trỏ test vào database ứng dụng vì fixture sẽ xóa schema sau phiên test.

Frontend chạy từ máy host:

```bash
cd frontend
npm ci
npm test -- --run
npm run lint
npm run build
```

- [ ] **Step 6: Thêm xử lý lỗi thường gặp**

Nêu ba tình huống và hành động cụ thể:

- Docker daemon chưa chạy: mở Docker Desktop rồi chạy lại.
- Cổng `5173`, `8000` hoặc `5432` bị chiếm: dừng tiến trình/container đang dùng cổng hoặc đổi mapping trong `docker-compose.yml`.
- Backend image cũ thiếu migration: chạy `docker compose up --build` để rebuild.
- Frontend không gọi được API: kiểm tra `VITE_API_BASE_URL` trong `.env`, sau đó rebuild frontend vì Vite bake biến này vào bundle.

- [ ] **Step 7: Kiểm tra và commit README**

Run:

```bash
git diff --check
git diff -- README.md
git check-ignore -v .env
```

Expected: `git diff --check` exit 0; diff chỉ có nội dung đã duyệt; `.env` được `.gitignore` loại trừ.

Commit:

```bash
git add README.md
git commit -m "doc: cập nhật hướng dẫn chạy ứng dụng"
```

### Task 2: Xác minh phạm vi và xuất bản

**Files:**
- Verify: `README.md`
- Verify: `docs/superpowers/specs/2026-07-19-readme-run-guide-design.md`
- Verify: `docs/superpowers/plans/2026-07-19-readme-run-guide.md`

**Interfaces:**
- Consumes: commit tài liệu từ Task 1.
- Produces: nhánh tài liệu đã push và Draft PR vào `main`.

- [ ] **Step 1: Xác minh trạng thái Git và phạm vi**

Run:

```bash
git status -sb
git diff --check main...HEAD
git diff --name-only main...HEAD
git log --oneline main..HEAD
```

Expected: chỉ có ba file Markdown thuộc spec, plan và README; không có `.env`, mã nguồn hoặc tài liệu Knowledge Base mới.

- [ ] **Step 2: Push và tạo Draft PR**

```bash
git push -u origin fix/readme-run-guide
```

Tạo Draft PR vào `main` với tiêu đề `doc: cập nhật hướng dẫn chạy ứng dụng`, mô tả nội dung thay đổi và các kiểm tra Markdown/phạm vi đã chạy. Không merge PR.

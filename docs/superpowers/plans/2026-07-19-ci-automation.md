# CI Automation Implementation Plan

**Goal:** Thêm GitHub Actions để tự động chạy golden test + toàn bộ pytest backend và lint/test/build frontend trên mỗi push/PR vào `main` — hoàn thành phần "tự động hoá" còn lại của Giai đoạn 1C.

**Architecture:** 1 workflow file `.github/workflows/ci.yml`, 2 job độc lập (`backend`, `frontend`), backend dùng service container Postgres pgvector khớp `docker-compose.yml`.

**Tech Stack:** GitHub Actions, Python 3.12, pytest, Node 22, npm.

## Global Constraints

- Không viết test mới, không đổi test/golden flow hiện có.
- Không cấu hình branch protection (ngoài phạm vi code).
- Branch `chore/1c-ci-automation`, commit `doc: ...` rồi `chore: ...`.

---

### Task 0: Đặc tả và kế hoạch

- [x] Viết spec + plan.
- [ ] Commit: `doc: đặc tả tự động hoá CI`

### Task 1: Viết workflow CI

**Files:**
- Add: `.github/workflows/ci.yml`

- [ ] **Step 1:** Job `backend`: service `postgres` (`pgvector/pgvector:pg16`, user/pass/db `examcraft`, port 5432, healthcheck `pg_isready`); setup Python 3.12; `pip install -r backend/requirements-dev.txt`; tạo database `examcraft_test` bằng `psql`; chạy `pytest -q` với `TEST_DATABASE_URL` trỏ `examcraft_test`.
- [ ] **Step 2:** Job `frontend`: setup Node 22 (cache npm theo `frontend/package-lock.json`); `npm ci`; `npm run lint`; `npm test -- --run`; `npm run build`.
- [ ] **Step 3:** Trigger `push`/`pull_request` nhắm `main`.
- [ ] **Step 4:** Push nhánh, xác nhận cả 2 job chạy xanh trên GitHub Actions (81 test backend, toàn bộ test/lint/build frontend).
- [ ] **Step 5:** Commit: `chore: thêm CI chạy pytest và frontend check`

### Task 2: Cập nhật tài liệu tiến độ

**Files:**
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`

- [ ] **Step 1:** Tách gạch đầu dòng "Golden test tự động hoá..." ở 1C: tick phần tự động hoá CI, giữ chưa tick phần đóng gói VPS/UAT giáo viên (còn lại, để task riêng).
- [ ] **Step 2:** Commit: `doc: cập nhật tiến độ CI tự động hoá`

# KẾ HOẠCH PHÁT TRIỂN — HƯỚNG ĐI ĐÃ CHỐT

**Cập nhật:** 19/07/2026. Phạm vi ưu tiên: **cấp 2 (THCS) trước**, các cấp khác bật dần bằng dữ liệu.
Tài liệu liên quan: [PRD](../product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md) · [Implementation Notes](IMPLEMENTATION_NOTES.vi.md) · prototype tham chiếu tại `prototype/`.

## 1. Nguyên tắc chỉ đạo

1. **Quyết định chủ dự án (19/07/2026):** tích hợp LLM/API key làm **sau cùng**, khi UI + BE + FE hoàn tất. Để điều này an toàn, mọi lời gọi AI đi qua interface `AIProvider` ngay từ đầu; trong suốt giai đoạn phát triển dùng `MockAIProvider` trả fixture lấy từ đề Global Success 7 – Unit 3 thật. Đánh đổi được chấp nhận: rủi ro chất lượng sinh phát hiện muộn hơn; bù lại pipeline được thiết kế để thay provider không phải sửa lõi.
2. **Hạ tầng tối thiểu** (PRD 22.1): 1 database, 1 tiến trình, job là bảng trong DB, không microservice/queue riêng.
3. **Giáo viên duyệt 100%** trước khi xuất; mọi cảnh báo là mềm, không chặn.
4. Prototype là **đặc tả hành vi UI** — code thật phải tái hiện đúng, không sáng tạo lại.
5. Mọi quyết định mới → ghi vào docs (nhật ký PRD mục 23.3) rồi mới code.

## 2. Stack đã chốt

| Tầng | Lựa chọn | Lý do chính |
|---|---|---|
| Backend | Python 3.12 + FastAPI | `python-docx` là thư viện DOCX tốt nhất (định dạng giáo viên đã kiểm chứng bằng nó); hệ sinh thái RAG mạnh nhất ở Python |
| Database | PostgreSQL 16 + pgvector | Một DB cho cả dữ liệu, full-text và vector search — đúng nguyên tắc 22.1 |
| ORM / migration | SQLAlchemy + Alembic | Chuẩn phổ biến, dễ tìm tài liệu |
| Frontend | React + Vite + **TypeScript (strict)** | Dữ liệu có cấu trúc sâu → type tĩnh bắt lỗi sớm; port từ prototype |
| Schema dữ liệu AI | Pydantic (backend) + Zod (frontend) | JSON schema dạng bài là hợp đồng cốt lõi; hai đầu validate cùng một đặc tả |
| DOCX renderer | python-docx | Thông số đã chốt ở Implementation Notes mục 2 |
| AI | Interface `AIProvider`; MVP dùng API (Claude/GPT), embedding qua API | PRD mục 10; local LLM là adapter thêm sau |
| Auth | Session cookie + bcrypt, phân quyền tại backend | Đủ cho 1 Admin + 3 giáo viên |
| Đóng gói | Docker Compose (app + postgres) | Chạy local và VPS cùng một cấu hình |

Cấu trúc repo đề xuất: `backend/` (FastAPI), `frontend/` (Vite React TS), giữ `prototype/` và `docs/` như hiện tại.

### 2.1 Quy ước Git

Theo chuẩn Conventional Commits, dùng chung tiền tố cho cả branch và commit:

| Tiền tố | Khi dùng |
|---|---|
| `feat` | Tính năng mới |
| `fix` | Sửa lỗi |
| `chore` | Việc lặt vặt không ảnh hưởng logic (cấu hình, dependency, tool build...) |
| `doc` | Chỉ thay đổi tài liệu |
| `refactor` | Tái cấu trúc code, không đổi hành vi |
| `test` | Thêm/sửa test |
| `style` | Format/style code, không đổi logic |
| `perf` | Cải thiện hiệu năng |

- **Branch:** `<tiền tố>/<mô-tả-ngắn-gạch-ngang>` — ví dụ `feat/1a-skeleton`, `fix/docx-margin`, `chore/update-deps`.
- **Commit message:** `<tiền tố>: <mô tả ngắn gọn>` — ví dụ `feat: thêm màn hình duyệt câu hỏi`. Không kèm trailer `Co-Authored-By`; lịch sử commit chỉ đứng tên chủ dự án (minhtoankhuu).

### 2.2 Chạy thử skeleton 1A + lõi tạo đề 1B

```bash
cp .env.example .env        # chỉnh nếu cần, mặc định đã dùng được ngay
docker compose up --build
```

- Backend: http://localhost:8000 (docs tự sinh tại `/docs`), frontend: http://localhost:5173, Postgres: `localhost:5432`.
- Container `backend` tự chạy `alembic upgrade head` rồi seed dữ liệu danh mục trước khi khởi động API — idempotent, chạy lại không tạo trùng.
- Tài khoản Admin mặc định: `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` trong `.env` (mặc định `admin@examcraft.dev` / `ChangeMe123!`) — **đổi ngay ở môi trường thật**.
- Chạy test backend (cần một Postgres khác cho `TEST_DATABASE_URL`, ví dụ tạo thêm database `examcraft_test` trong cùng container `db`):
  ```bash
  cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
  TEST_DATABASE_URL=postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft_test python -m pytest tests/ -v
  ```
- Frontend build/lint: `cd frontend && npm run build && npm run lint`.

## 3. Lộ trình (đã điều chỉnh: LLM tích hợp sau cùng)

### Giai đoạn 1A — Nền móng (tuần 1–3)

- [x] Skeleton backend (FastAPI + SQLAlchemy + Alembic) và frontend (Vite + React + TypeScript strict), Docker Compose (Postgres/pgvector + backend + frontend), chạy được bằng `docker compose up` — nhánh `feat/1a-skeleton`.
- [x] Auth session cookie + bcrypt, phân quyền Admin/Giáo viên (`require_admin`/`require_any_role`).
- [x] Danh mục học thuật + **seed toàn bộ dữ liệu đã duyệt**: 5 trình độ CEFR, 5 chứng chỉ Cambridge quy đổi, 3 cấp học, 12 khối lớp + gợi ý trình độ, 78 Unit Global Success (lớp 6–12), 12 thì + 20 cấu trúc câu (32 `GrammarPoint`), 10 dạng bài, quy tắc độ dài câu/bài đọc. Idempotent, đã kiểm chứng qua pytest (16 test) và chạy thật trong container.
- [ ] Nhập tài liệu PDF/DOCX/text → trích xuất → chunk + metadata → full-text search.
- [ ] **Fixture bank:** số hóa đề Global Success 7 – Unit 3 thành JSON đúng schema — vừa là dữ liệu cho `MockAIProvider`, vừa là golden test sau này.
- **Nghiệm thu còn lại:** Admin nhập và xuất bản tài liệu Unit 3; tra cứu trả đúng đoạn theo filter lớp/Unit.

### Giai đoạn 1B — Lõi tạo đề trên MockAIProvider (tuần 4–7)

- [x] Model + migration: `Exam`, `ExamBlock`, `ExamGrammarSelection`, `Question`, `ExamVariant` (nhánh `feat/1b-exam-core`).
- [x] `AIProvider` interface + `MockAIProvider`: fixture bank viết tay cho cả 10 dạng bài (không chỉ 5), ưu tiên bộ câu "vàng" khớp golden test Global Success 7 – Unit 3 khi ngữ cảnh khớp, template chung cho các trường hợp khác.
- [x] Validation Engine: schema (qua Pydantic), đếm từ câu hỏi 12–14 (trắc nghiệm/word form) và bài đọc theo bảng khối lớp, cảnh báo vượt trình độ, trùng lặp — **dùng fuzzy text-match (difflib) thay cho cosine embedding** vì RAG chưa code (embedding để dành Giai đoạn 1D). Từ điển phát âm CMU và marker-heuristic theo thì **chưa làm** — cần khi tích hợp LLM thật.
- [x] API đầy đủ: tạo/sửa đề, CRUD + reorder block, chọn thì/cấu trúc (`grammar-selection`), sinh câu (`/generate`), duyệt/khóa qua **PATCH tường minh** `is_approved`/`is_locked` (không dùng toggle — xem ghi chú thiết kế bên dưới), sinh lại từng câu, hoàn tất kiểm duyệt (đưa câu vào ngân hàng), cấu hình xuất + tạo mã đề A/B/C/D (kéo từ 1C lên vì không cần AI), tải DOCX.
- [x] DOCX renderer bằng `python-docx` theo đúng bảng thông số Implementation Notes mục 2 (Times New Roman, lề Narrow, tab 4 cột, đáp án tô đỏ...).
- [x] Test pytest: 25 test (auth, catalog, exam flow đầy đủ kể cả golden path Unit 3, regenerate/lock/approve, mã đề, export DOCX kiểm tra bằng python-docx).
- [x] Frontend: `ExamListPage` (Đề của tôi + tạo đề), `ExamBuilderPage` (block CRUD, sắp xếp bằng nút lên/xuống, chọn thì/cấu trúc), `ExamReviewPage` (duyệt/khóa/sinh lại), `ExamExportPage` (cấu hình xuất + tải). Nối API thật, không còn mock ở tầng UI. **Không port pixel-perfect giao diện prototype** — ưu tiên đủ chức năng, style tối giản; kéo-thả và xem trước A4 động hoàn thiện ở 1C.
- [x] **Nghiệm thu đạt được:** tạo trọn đề Unit 3 (4 block, 6 câu) từ đầu đến file DOCX qua Docker Compose thật — kiểm chứng bằng curl + mở lại bằng `python-docx`, không phải chỉ chạy `pytest`.

**Quyết định thiết kế phát sinh khi code (không có trong bản kế hoạch gốc):**
- Endpoint duyệt/khóa đổi từ toggle (`POST .../approve`) sang PATCH tường minh (`PATCH /questions/{id}` với body `{is_approved, is_locked}`) sau khi phát hiện qua kiểm thử rằng toggle không an toàn với mất gói tin/double-click (client retry sẽ âm thầm đảo trạng thái ngược).
- `update_exam` (PATCH đề) phải kiểm tra nhất quán nguồn kiến thức bất cứ khi nào một trong 4 trường liên quan (`source_type`/`unit_id`/`grammar_topic_id`/`cambridge_certificate_id`) xuất hiện trong payload, không chỉ khi `source_type` có mặt — bug tìm thấy qua test, đã có test hồi quy.

### Giai đoạn 1C — Hoàn thiện không-AI (tuần 8–9)

- [x] Mã đề A/B/C/D — đã làm trong 1B (xem trên).
- [x] Admin quản lý tài khoản giáo viên (nhánh `feat/1c-admin-teacher-accounts`): API `/admin/teachers` (tạo, khóa/mở lại, đặt lại mật khẩu — không xóa cứng), trang frontend riêng, dashboard tổng quan `/admin`, điều hướng phân theo vai trò (Admin thấy mục "Quản trị", Giáo viên không thấy), gate cả server (403) lẫn client (redirect). 8 test pytest kiểm phân quyền + CRUD; frontend có test tự động cho menu, route và trạng thái dashboard.
- [x] Audit log quản trị tài khoản giáo viên (nhánh `feat/1c-audit-log`): append-only, cùng transaction với thao tác tạo/cập nhật, không lưu mật khẩu/hash/session; API phân trang và trang Admin riêng.
- [x] Hạn mức sinh đề: mỗi giáo viên 10 lượt gọi AI/ngày theo `Asia/Bangkok`; sinh toàn đề tính theo số block, sinh lại tính 1 lượt, chặn nguyên tử bằng HTTP 429 khi không đủ; Admin không giới hạn. Frontend hiển thị số lượt còn lại và làm mới sau thao tác sinh thành công.
- [ ] Màn hình chỉnh sửa Admin còn lại theo prototype: dashboard tổng quan đã có và hiển thị rõ trạng thái; kho kiến thức, dạng bài & template, thư viện hình ảnh, cấu hình AI vẫn chưa có chức năng chỉnh sửa vì các khối này gắn với RAG và chờ cùng Giai đoạn 1D.
- [x] Kéo-thả thật cho sắp xếp block, giữ nút Lên/Xuống làm phương án hỗ trợ; xem trước A4 nhiều trang động ở frontend. Preview lấy từ API read-only `GET /exams/{id}/preview`, không dùng quota sinh đề; thứ tự thay đổi được cập nhật lạc quan và rollback khi API reorder lỗi.
- [ ] Golden test tự động hoá (hiện đang là test thủ công trong pytest); đóng gói VPS; giáo viên dùng thử toàn luồng trên mock.

### Giai đoạn 1D — Tích hợp LLM thật (tuần 10–11, khi có API key)

- Adapter provider thật (Claude/GPT) cắm vào `AIProvider`; embedding + hybrid search + reranker interface.
- **Spike chất lượng chuyển về đây:** sinh thử 3 dạng khó nhất (phát âm, trọng âm, đọc hiểu) với prompt ràng buộc chuẩn đã chốt; tiêu chí ≥70% câu chấp nhận không sửa. Dạng nào rớt → giữ chạy bằng ngân hàng câu hỏi/mock, lùi sinh tự động của dạng đó.
- Theo dõi token/chi phí; UAT thật với giáo viên.

Ước lượng trên giả định 1 người code với AI hỗ trợ, làm gần như toàn thời gian; nếu bán thời gian thì nhân đôi.

## 4. Rủi ro chính và đối sách

| Rủi ro | Đối sách |
|---|---|
| Chất lượng AI phát hiện muộn (do hoãn LLM về 1D) | Interface `AIProvider` cách ly hoàn toàn; fixture bank chuẩn hóa từ đề thật nên pipeline không đổi khi cắm LLM; spike 1D vẫn giữ tiêu chí ≥70%, dạng rớt chạy tạm bằng ngân hàng câu hỏi |
| AI sinh dạng ngữ âm kém | Validation bằng từ điển phát âm CMU; sẵn sàng lùi dạng này khỏi sinh tự động |
| Trích xuất PDF giáo trình lỗi | Chỉ nhận PDF có text (PRD đã loại OCR); cho phép dán text thủ công làm đường vòng |
| DOCX lệch định dạng giữa máy | Thông số đã kiểm chứng bằng python-docx; golden test render + PRD đã tuyên bố không cam kết số trang |
| Phạm vi phình (thêm cấp 1/3, Cambridge content) | Khóa phạm vi cấp 2; cấp khác chỉ là thêm seed data, không thêm tính năng |

## 5. Đang chờ xác nhận từ giáo viên

1. Danh mục Unit lớp 1–5 (khi mở rộng Primary).
2. Nguồn nội dung mục Cambridge (tài liệu riêng hay tái dùng Global Success).
3. Số từ/câu cho Tiểu học (6–10?) và THPT (14–18?).
4. Bảng số từ bài đọc (hiện là đề xuất của hệ thống).

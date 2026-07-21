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
- [x] Auth session cookie + bcrypt, phân quyền Admin/Giáo viên: `require_admin` khóa API quản trị, `require_teacher` khóa toàn bộ `/exams/*`, còn `require_any_role` chỉ dùng cho tài nguyên chung như catalog/usage.
- [x] Danh mục học thuật + **seed toàn bộ dữ liệu đã duyệt**: 5 trình độ CEFR, 5 chứng chỉ Cambridge quy đổi, 3 cấp học, 12 khối lớp + gợi ý trình độ, 78 Unit Global Success (lớp 6–12), 12 thì + 20 cấu trúc câu (32 `GrammarPoint`), 10 dạng bài, quy tắc độ dài câu/bài đọc. Idempotent, đã kiểm chứng qua pytest (16 test) và chạy thật trong container.
- [x] Nhập tài liệu Global Success lớp 6-8 (36 file `.docx`, nhánh `feat/1a-knowledge-base-global-success`): parser tách section theo từ khoá (VOCABULARY/WORD FORM/PREPOSITIONS AND PHRASES/GRAMMAR), best-effort trích trường có cấu trúc (word/ipa/pos/meaning cho từ vựng — tỉ lệ khớp ~98% trên 2814 mục), đọc cả bảng ngữ pháp lồng trong section GRAMMAR. Bảng `knowledge_documents`/`knowledge_chunks` (`search_vector` tsvector sinh tự động + GIN index). Script `python -m app.import_knowledge` idempotent theo checksum SHA-256 (idempotent + tự thay chunk khi file đổi nội dung). API `GET /knowledge/search` (filter unit/khối lớp/loại chunk, full-text qua `plainto_tsquery` + `ts_rank`) dùng chung `require_any_role` như catalog. Đã chạy thật qua Docker Compose: 36/36 file, 8150 chunk, chạy lại không tạo trùng. **Còn lại:** Cambridge, Tense, và `Global Success/G9` (cấu trúc tài liệu khác, không tách theo Unit) — để task riêng sau.
- [x] **Fixture bank:** `GOLDEN_UNIT3_QUESTIONS` nay đủ 10/10 dạng bài (nhánh `feat/1a-golden-unit3-fixtures`, tiếp theo 4 dạng đã có từ 1B). 6 dạng bổ sung (stress, matching, gap_fill, cloze_test, sign_reading, word_form) soạn dựa trên dữ liệu thật trong `knowledge_chunks` của Unit 3 (word/ipa/pos/meaning đã qua parser + kiểm chứng), không bịa từ ngoài Unit. `MockAIProvider._pool()` ưu tiên golden khi `grade_number==7 and unit_order_no==3`, có test hồi quy xác nhận golden/generic không lẫn nhau.
- **Nghiệm thu còn lại:** Admin nhập và xuất bản tài liệu Unit 3 (chưa có UI — dời sang 1D theo mục 1C bên dưới); tra cứu trả đúng đoạn theo filter lớp/Unit (đã đạt qua API, xem trên).

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
- [x] Admin quản lý tài khoản giáo viên (nhánh `feat/1c-admin-teacher-accounts`): API `/admin/teachers` (tạo, khóa/mở lại, đặt lại mật khẩu), trang frontend riêng, dashboard tổng quan `/admin`. Phân tách hai chiều ở cả server và client: Admin chỉ thấy workflow quản trị và bị chặn khỏi `/exams/*`; Giáo viên chỉ thấy workflow đề thi và bị chặn khỏi `/admin/*`. Bổ sung sau (cùng nhánh `feat/1c-shell-prototype-parity`): `DELETE /admin/teachers/{id}` xóa cứng — chặn `409` nếu giáo viên còn đề thi (không vi phạm FK, không mất dữ liệu); trang chuyển sang dạng bảng, nút "Thêm tài khoản" và "Đặt lại mật khẩu" mở qua popup (`<dialog>`).
- [x] Audit log quản trị tài khoản giáo viên (nhánh `feat/1c-audit-log`): append-only, cùng transaction với thao tác tạo/cập nhật, không lưu mật khẩu/hash/session; API phân trang và trang Admin riêng.
- [x] Hạn mức sinh đề: mỗi giáo viên 10 lượt gọi AI/ngày theo `Asia/Bangkok`; sinh toàn đề tính theo số block, sinh lại tính 1 lượt, chặn nguyên tử bằng HTTP 429 khi không đủ. Admin không dùng workflow sinh đề. Frontend hiển thị số lượt còn lại cho Giáo viên và làm mới sau thao tác sinh thành công.
- [x] Trang Admin quản lý kho kiến thức (nhánh `feat/1c-admin-knowledge-base`, xem `docs/superpowers/specs/2026-07-20-admin-knowledge-base-design.md`): API `admin_knowledge.py` (`/admin/knowledge-documents`) liệt kê/xuất bản-ẩn/xóa; upload `.docx` qua UI tái dùng đúng `parse_lesson_docx` + logic idempotent theo checksum SHA-256 như script CLI `app.import_knowledge` (không cần chạy tay nữa). Trang `AdminKnowledgePage` (bảng + popup nhập tài liệu chọn Khối lớp/Unit, bộ lọc theo khối lớp/loại nguồn, sắp xếp theo cột, xem nội dung từng đoạn), card "Kho kiến thức & RAG" ở dashboard Admin nay có chức năng thật.
- [x] Hỗ trợ nhập tài liệu ngữ pháp Kiến thức chung (cùng nhánh trên, xem `docs/superpowers/specs/2026-07-20-grammar-reference-knowledge-design.md`): tài liệu ngữ pháp tổng hợp (vd trọn 1 thì) khác cấu trúc bài học Global Success — tiêu đề in đậm chứ không viết hoa toàn bộ, nên cần parser riêng `grammar_parser.parse_grammar_reference_docx` (nhận diện tiêu đề bằng định dạng in đậm, luôn giữ bảng — parser cũ từng làm mất bảng vì không nhận diện được mục). `KnowledgeDocument.unit_id` chuyển nullable, thêm `grammar_point_id` — đúng một trong hai được set. Popup nhập tài liệu có chọn "Loại nguồn": Global Success (theo Unit) / Kiến thức chung (theo GrammarPoint qua Chuyên đề → Cấu trúc/Thì). Đã verify thật qua Docker: upload tài liệu ngữ pháp mẫu giữ đúng bảng, tách đúng mục theo tiêu đề in đậm.
- [x] Sửa hiển thị bảng trong popup "Xem" của Kho kiến thức: bảng có ô gộp nhiều dòng (ví dụ bảng "Irregular adjective" — 1 ô chứa cả 5 từ good/bad/far/many-much/little) trước đây bị dồn thành 1 chuỗi nối dấu "|", nhìn giống mất dữ liệu dù chữ vẫn còn đủ. Parser giờ lưu thêm `structured.table` (đúng cấu trúc hàng/cột thật của bảng Word, hàm `table_to_grid` trong `docx_utils.py`), popup "Xem" render lại đúng dạng bảng thay vì gộp chữ. Đã verify thật: xóa và upload lại `GS6 - UNIT 12 - LESSON.docx` qua API, bảng "Irregular adjective" trả đúng lưới 2 hàng x 3 cột (Positive/Comparative/Superlative tách cột rõ ràng).
- [x] Sửa tiếp `raw_text` (không chỉ hiển thị) cho cùng dạng bảng trên — đây mới là phần thật sự đưa vào LLM sau này (RAG), không phải `structured.table` chỉ dùng để hiển thị. Thêm `_row_to_lines()` trong `docx_utils.py`: khi mọi ô trong hàng có cùng số dòng con thì ghép theo đúng vị trí ("good → better → the best") thay vì gộp cả cột như cũ. Thêm cờ `--force` cho `app.import_knowledge` để parse lại toàn bộ file đã import dù checksum không đổi (import vốn idempotent theo checksum nên không tự refresh khi chỉ parser code đổi) — đã chạy `--force` refresh thật cả 36 file Global Success G6-G8 hiện có trong DB dev, không chỉ 1 file test. Giới hạn đã biết và được chủ dự án xác nhận chấp nhận (20/07/2026): với bảng mà 1 ô là câu quy tắc bị ngắt dòng giữa chừng (không phải danh sách song song thật), ghép theo vị trí dòng có thể cắt câu quy tắc thành 2 nửa gắn nhầm — không mất chữ, chỉ xáo trật tự trong số ít bảng dạng này; không có cách rẻ tiền phân biệt chắc chắn 2 trường hợp mà không hiểu ngữ nghĩa.
- [x] **Bug nghiêm trọng hơn phát hiện khi soát lại `GS7 - UNIT 12`** (khung "Xem" toàn bộ mục từ vựng hiện "Khác" thay vì "Từ vựng"): `knowledge_parser._is_header` trước đây chỉ nhận diện tiêu đề bằng viết HOA toàn bộ ("VOCABULARY", "WORD FORM"...), nhưng rà cả 36 file thì có 7 file dùng tiêu đề in đậm dạng thường/Title Case ("New words", "Vocabulary", "Word form", "Grammar and Structures"...) — với các file này, *toàn bộ* nội dung phía sau tiêu đề đầu tiên rơi vào `DocumentChunkType.OTHER`, không được parse cấu trúc, mất luôn phân loại. Đã kiểm tra: không có mục từ vựng thật nào trong kho G6-G8 in đậm toàn dòng, nên dùng "in đậm toàn đoạn" (`is_bold_paragraph`, chuyển vào `docx_utils.py` dùng chung với `grammar_parser.py`) làm tín hiệu tiêu đề bổ sung là an toàn, không nhầm nội dung thành tiêu đề. Thêm từ khóa "NEW WORD" vào `_SECTION_KEYWORDS`. Thêm test soát toàn kho: mỗi file phải có ≥5 chunk từ vựng (bắt được đúng loại lỗi này — test tổng cũ chỉ so tổng > 2000 nên không lộ ra dù vài file bằng 0). Đã `--force` refresh lại 36 file lần nữa sau fix này (7905 chunk, thay 8150 lúc trước — giảm vì tiêu đề giờ không còn bị đếm nhầm thành nội dung). Verify thật: `GS7 - UNIT 12` giờ có 125 vocabulary + 64 word_form + 28 phrase + 10 grammar, không còn "Khác".
- [x] Sửa tiếp: một số Unit đánh số thủ công cho danh sách WORD FORM (dạng từ) — vd "7. responsible (adj): có trách nhiệm", "10. harm (v/n): gây hại" — số này chỉ là marker liệt kê, không phải nội dung, và `WORD_FORM` không có structured parser riêng nên số bị lưu nguyên vào `raw_text`, hiện dính ở đầu chữ trong khung "Xem" (báo cáo trực tiếp qua ảnh chụp màn hình `GS7 - UNIT 12`, dù bug thật ra nằm ở nhiều Unit khác, không riêng file này). Thêm `_LEADING_ENUM_RE` (dùng `re.MULTILINE` để bắt cả số nằm sau dấu xuống dòng mềm giữa 1 đoạn gộp nhiều mục) bóc số khỏi mọi loại nội dung trước khi lưu. Rà lại toàn kho: từ 154 chunk còn dính số xuống còn 0 (4 trường hợp còn lại là số thứ tự quy tắc ngữ pháp thật bên trong bảng — khác code path, không đụng tới vì số ở đó mang nghĩa "quy tắc 1/2/3", không phải marker rác). Đã `--force` refresh lại 36 file, verify DB dev không còn chunk nào dính số ở đầu.
- [x] Màn hình chỉnh sửa Admin "Cấu hình AI" — xem Giai đoạn 1D bên dưới. **Còn lại:** "Dạng bài & template" vẫn chưa có màn chỉnh sửa (gắn với prompt LLM thật, không phải chỉ hạ tầng provider — xem mục prompt templates trong 1D). **Đã bỏ:** thư viện hình ảnh do Admin quản lý tập trung (quyết định 20/07/2026, PRD mục 23.3 #18) — dạng "Đọc biển báo/thông báo" mặc định mô tả bằng văn bản; nếu sau này cần ảnh thật thì để giáo viên tự tải ảnh gắn vào từng câu/block lúc tạo đề (chỉ ghi nhận hướng đi, chưa triển khai).
- [x] Kéo-thả thật cho sắp xếp block, giữ nút Lên/Xuống làm phương án hỗ trợ; xem trước A4 nhiều trang động ở frontend. Preview lấy từ API read-only `GET /exams/{id}/preview`, không dùng quota sinh đề; thứ tự thay đổi được cập nhật lạc quan và rollback khi API reorder lỗi.
- [x] Golden test tự động hoá: `.github/workflows/ci.yml` chạy song song 2 job (`backend`: Postgres pgvector service + toàn bộ pytest; `frontend`: lint + test + build) trên mỗi push/PR vào `main`, đã xác nhận chạy xanh thật trên GitHub Actions. **Còn lại:** đóng gói VPS; giáo viên dùng thử toàn luồng trên mock.
- [x] Đồng bộ khung giao diện (sidebar, nav theo vai trò, màn đăng nhập chia đôi màn hình) theo `prototype/` (nhánh `feat/1c-shell-prototype-parity`): port token màu + class CSS phần khung, icon dựng lại bằng component React, vẫn 1 form đăng nhập chung (không tách theo vai trò — đã xác nhận với chủ dự án).
- [x] Đồng bộ giao diện luồng đề thi (cùng nhánh trên): `ExamListPage`, `ExamBuilderPage` (+ `SortableBlockList`, `ExamPreview`), `ExamReviewPage`, `ExamExportPage` đều dùng đúng class/token đã port (`.builder-grid`, `.block-list`/`.exam-block` với badge màu theo 10 dạng bài, `.paper`/`.preview-panel`, `.q-card`, `.export-card`...), thêm `StepsIndicator` dùng chung hiển thị tiến trình 4 bước, và lưới chọn nhanh "Dạng bài tập" (tick = thêm block 5 câu/1 điểm mặc định, bỏ tick = xóa). **Quyết định:** giữ nguyên routing nhiều trang (không gộp thành 1 trang như prototype) để không phá cơ chế chống race-condition đã làm ở `fix/exam-page-route-races`; chỉ đổi giao diện. **Còn lại:** trang quản trị Admin cho dạng bài & template và cấu hình AI (dời sang 1D theo mục ngay trên); kho kiến thức đã xong (xem mục ngay trên); thư viện hình ảnh do Admin quản lý tập trung đã bỏ khỏi kế hoạch.
- [x] Tách bước 1 "Tạo đề" khỏi "Đề của tôi" thành route riêng `/exams/new` (`ExamCreatePage`, nav sidebar riêng) — khớp đúng cấu trúc 4 bước của prototype thay vì gộp form tạo đề vào đầu trang danh sách. `ExamListPage` (`/exams`) giờ chỉ còn bảng liệt kê toàn bộ đề đã tạo, kèm tải DOCX trực tiếp từng mã đề khi đề đã "Sẵn sàng xuất".
- [x] Phần con (sub-part) trong block (nhánh `feat/1c-block-subparts`, xem `docs/superpowers/specs/2026-07-20-block-sub-parts-design.md`): xuất phát từ mẫu đề thật GS9 Unit 2 do chủ dự án gửi, cho thấy một mục La Mã thường chia nhiều phần đánh số 1./2./3. (ví dụ so sánh kép/so sánh hơn kém nhất/cụm động từ trong cùng "IV. TRANSFORMATION PATTERNS"). Model mới `ExamBlockPart` (title/instruction/question_count/prompt_override riêng, dùng chung exercise_type/points/difficulty của block cha) + FK `part_id` nullable trên `Question` — block không có phần con hoạt động y hệt trước (tương thích ngược). API CRUD + reorder phần con tự đồng bộ `question_count` của block. `generate_block_questions`/`regenerate_question`/`shuffle_variant` xử lý riêng theo từng phần (không trộn câu giữa các phần khi xáo trộn mã đề). DOCX renderer in tiêu đề phụ 1./2./3. trước câu hỏi đầu mỗi phần; preview A4 trả `part_number`/`part_title`/`part_instruction` theo câu và không tách tiêu đề phần khỏi câu đầu khi ngắt trang. Popup chỉnh sửa block (`ExamBuilderPage`) có khu vực "Phần con" để thêm/sửa/xóa, ô "Số câu" cấp block tự khóa khi có phần con. 97 test backend + 78 test frontend, lint/build sạch, verify qua Docker Compose.

### Giai đoạn 1D — Tích hợp LLM thật (tuần 10–11, khi có API key)

- [x] Adapter provider thật OpenAI + RAG đầy đủ (nhánh `feat/1d-openai-rag-integration`, xem `docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md`): chủ dự án chọn OpenAI (đã có API key) và quyết định làm trọn RAG thật (embedding + hybrid search) ngay từ đầu thay vì nối LLM trước với ngữ cảnh đơn giản.
  - **Hạ tầng RAG:** cột `embedding vector(1536)` (`text-embedding-3-small`) thẳng trên `knowledge_chunks` (không tách bảng `ChunkEmbedding` riêng — nhất quán với cách `search_vector` đã làm), index HNSW; cột `embedding` tương tự trên `questions` cho Validation Engine. Migration viết tay `CREATE EXTENSION IF NOT EXISTS vector` + 2 bảng mới, né gotcha autogenerate quen thuộc trên `knowledge_chunks`.
  - **Hybrid search** (`app/services/rag_search.py`): kết hợp full-text (đã có) + vector cosine, hợp nhất bằng **Reciprocal Rank Fusion (RRF)** — quyết định chốt với chủ dự án: không thêm bước LLM rerank riêng (OpenAI không có endpoint rerank như Cohere; corpus mỗi Unit/GrammarPoint chỉ vài chục-200 chunk nên RRF đủ tốt, rẻ và nhanh hơn). Trả rỗng khi đề nguồn Cambridge (kho kiến thức chưa phủ) — `OpenAIProvider` xử lý tường minh bằng cảnh báo, không lỗi ngầm.
  - **`app/embed_knowledge.py`** (CLI mới, không tự động chạy — tốn tiền OpenAI thật dù nhỏ): embed chunk chưa có embedding hoặc đổi model, idempotent/resumable theo batch.
  - **`OpenAIProvider`** (`app/services/openai_provider.py`): implement đúng `AIProvider` sẵn có, dùng Chat Completions + Structured Outputs (JSON schema), retry tối đa 2 lần rồi raise `AIGenerationError` (không âm thầm rơi về Mock), ghi `GenerationLog` mỗi lần gọi (provider/model/token/chi phí/chunk nguồn — **không lưu** nguyên văn prompt/response, tránh lưu lâu dài nội dung sách bản quyền, quyết định chủ dự án). Hướng dẫn theo dạng bài gộp 1 dict `app/services/prompts.py` (không tách file/dạng bài).
  - **Cấu hình Admin** (`AIProviderConfig`, đúng 1 dòng active): API key mã hóa bằng Fernet (`app/services/crypto.py`, key mới `AI_CONFIG_ENCRYPTION_KEY`), luôn mask khi trả API (`sk-...ab12`), để trống khi sửa = giữ nguyên key cũ. Router `admin_ai_config.py` (mirror `admin_knowledge.py`) + endpoint `POST /test` xác nhận key hợp lệ trước khi lưu. Tổng quát hóa `record_audit_log` (trước chỉ nhận `target: User`) để dùng chung cho audit log cấu hình AI.
  - **Provider factory** (`get_active_provider(db)`): thay singleton `MockAIProvider()` cứng trong `generation.py` — chưa cấu hình AI thì tự động dùng Mock (an toàn), không lỗi cứng.
  - **Validation Engine:** thêm cosine-similarity check (ngưỡng 0.90 mặc định, Admin chỉnh qua `AIProviderConfig.duplicate_similarity_threshold`) **kết hợp** (không thay) fuzzy-match sẵn có — đúng PRD 11. Embed theo batch 1 lần/block (không phải N lần/N câu) để tránh N round-trip OpenAI thêm vào đường sinh câu.
  - **Frontend:** `AdminAIConfigPage.tsx` mới (chọn model từ whitelist cố định, không free-text; slider temperature/ngưỡng trùng lặp; nút "Kiểm tra kết nối"), thêm nav "Cấu hình AI", card "Cấu hình AI (OpenAI)" ở dashboard Admin hiện trạng thái thật (model đang dùng / "Chưa cấu hình") thay vì placeholder "Sắp triển khai".
  - 168 test backend (thêm ~50 test mới, toàn bộ mock OpenAI SDK — không gọi API thật trong CI) + 114 test frontend, lint/build sạch.
- [x] **Verify thật qua Docker phát hiện bug**: sinh đề thật đầu tiên trả về 200 OK nhưng 0 câu hỏi ở mọi block. `GenerationLog` cho thấy OpenAI gọi thành công nhưng `source_chunk_ids` rỗng — `_retrieve()` nhét literal `exercise_type_code` (vd "multiple_choice") vào query full-text, từ này không xuất hiện trong nội dung sách nên `plainto_tsquery` (AND toàn bộ từ) trật khớp hoàn toàn; kết hợp việc `embed_knowledge.py` chưa chạy nên nhánh vector cũng rỗng — OpenAI đúng theo prompt là từ chối bịa câu khi không có nguồn. Sửa: bỏ `exercise_type_code` khỏi query (dùng `prompt_override`/`unit_title`); `hybrid_search` thêm fallback lấy chunk theo `order_no` trong phạm vi khi cả FTS lẫn vector đều rỗng, đảm bảo luôn có ngữ cảnh khi Unit/GrammarPoint có kiến thức thật. Đã chạy `embed_knowledge.py` thật (7905 chunk, ~$0.0038 USD) và verify sinh đề thật ra câu hỏi đúng.
- [x] **Bỏ giới hạn 10 lượt/ngày** (quyết định chủ dự án 21/07/2026, sau khi thấy sinh đề = tiền thật): `reserve_usage`/`get_usage_status` không còn raise `UsageLimitExceeded`, mọi vai trò `is_unlimited=True`; vẫn cộng dồn `used_count` để theo dõi chi phí. Badge sidebar đổi thành "Không giới hạn lượt sinh đề".
- [x] **Bug chất lượng phát hiện qua ảnh chụp đề thật của chủ dự án**: câu PRONUNCIATION so sánh phát âm giữa các cụm từ không liên quan (vd "gardening" vs "computer games") — vô nghĩa vì không có điểm chung để so, và phần cần gạch chân không hiện ra ở đâu (hệ thống trước giờ, kể cả Mock, chưa từng có cơ chế đánh dấu/render gạch chân). Sửa: viết lại `EXERCISE_INSTRUCTIONS["pronunciation"/"stress"]` nêu rõ cơ chế thật (4 từ đơn cùng cụm chữ cái/cùng số âm tiết, chỉ khác phần so sánh) kèm ví dụ mẫu; quy ước đánh dấu `<u>...</u>` trong `option.text`. `docx_renderer.py` thêm `_add_runs_with_underline()` áp `run.font.underline` khi xuất DOCX; frontend (`ExamReviewPage`) thêm `UnderlineText` parse cùng marker khi duyệt đề. `PROMPT_VERSION` → v2.
- [x] **Nút "Duyệt toàn bộ" + "Xem A4" ở "Đề của tôi"** (theo yêu cầu chủ dự án sau khi dùng thử — duyệt từng câu ở trang riêng tốn thời gian với đề đã ổn): endpoint `POST /exams/{id}/approve-all` (duyệt hết + hoàn tất kiểm duyệt trong 1 lần gọi, tách `_finalize_review()` dùng chung với `complete-review`, không vi phạm nguyên tắc duyệt 100% vì vẫn là hành động chủ động của giáo viên). Nút "Xem A4" mở modal tái dùng `ExamPreview` (component đã có sẵn trong `ExamBuilderPage`) ngay tại trang danh sách.
- [x] **Câu dẫn lặp lại mỗi câu + gạch chân chưa nổi bật** (phản hồi qua ảnh chụp đề tham khảo của chủ dự án): đề tham khảo chỉ ghi câu dẫn 1 lần rồi liệt kê câu 1-5 chỉ với lựa chọn — đề hệ thống xuất lặp lại y hệt câu dẫn ở mọi câu cùng dạng (LLM trả `prompt_text` riêng từng câu, tự nhiên giống hệt với dạng phát âm/trọng âm). `docx_renderer.py` theo dõi câu dẫn của câu ngay trước trong cùng block/phần, trùng thì bỏ qua (reset khi sang block/phần mới). Nhân tiện vá bug có sẵn: `block.instruction` được tính vào phân trang preview và hiện đúng trên web nhưng chưa từng in ra file DOCX. Phần `<u>...</u>` giờ luôn in đậm (trước chỉ đậm khi là đáp án đúng); frontend bọc thêm `<strong>` cho nhất quán.
- [x] **Bổ sung 3 kiểu bài Pronunciation** (theo ảnh chụp đề tham khảo của chủ dự án): hướng dẫn cũ chỉ mô tả kiểu "so sánh âm chung" (vd clean/bread/teach/team), thiếu 2 kiểu rất phổ biến trong đề thật — đuôi -s/-es (/s/ /z/ /ɪz/) và đuôi -ed (/t/ /d/ /ɪd/). Viết lại `EXERCISE_INSTRUCTIONS["pronunciation"]` liệt kê đủ 3 kiểu kèm ví dụ mẫu, LLM tự chọn kiểu phù hợp từ vựng có sẵn trong nguồn. `PROMPT_VERSION` → v3.
- **Spike chất lượng chuyển về đây:** sinh thử 3 dạng khó nhất (phát âm, trọng âm, đọc hiểu) với prompt ràng buộc chuẩn đã chốt; tiêu chí ≥70% câu chấp nhận không sửa. Dạng nào rớt → giữ chạy bằng ngân hàng câu hỏi/mock, lùi sinh tự động của dạng đó. **Còn lại:** UAT thật với giáo viên trước khi đánh giá được tiêu chí này.
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

# Knowledge Base Global Success Ingestion Implementation Plan

**Goal:** Nhập 36 file bài học Global Success (G6-G8) từ `Knowledge_Base/` vào DB, chunk theo section có metadata, và cung cấp API full-text search theo Unit/khối lớp — hoàn thành phần còn thiếu của Giai đoạn 1A.

**Architecture:** Parser thuần (`app/services/knowledge_parser.py`) đọc `.docx` theo thứ tự body (paragraph + table xen kẽ) và phân loại section bằng từ khoá tiêu đề, sinh danh sách chunk. Script import (`app/import_knowledge.py`) idempotent theo checksum, ánh xạ file → `Unit` đã seed sẵn. API `/knowledge/search` dùng Postgres full-text (`tsvector` generated column + GIN index).

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, python-docx, PostgreSQL 16 (tsvector), pytest.

## Global Constraints

- Chỉ G6-G8 (36 file), không đụng Cambridge/Tense/G9.
- Không làm embedding/vector search, không auto-link `GrammarPoint`.
- Không làm UI Admin (đã dời sang 1D).
- Commit theo `feat: ...` và `doc: ...`, branch `feat/1a-knowledge-base-global-success`.
- Parser không được raise exception vì cấu trúc lệch — tối đa rơi vào `chunk_type=other`.

---

### Task 0: Đặc tả và kế hoạch

- [x] Viết `docs/superpowers/specs/2026-07-19-knowledge-base-global-success-design.md`
- [x] Viết plan này
- [ ] Commit: `doc: đặc tả nhập tài liệu Global Success`

### Task 1: Model + migration

**Files:**
- Add: `backend/app/models/knowledge.py`
- Modify: `backend/app/models/__init__.py`
- Add: `backend/alembic/versions/<rev>_add_knowledge_base.py`

**Interfaces:**
- Produces: `KnowledgeDocument`, `KnowledgeChunk`, `DocumentChunkType` (enum: vocabulary/word_form/phrase/grammar/other).
- Consumes: `Unit` (FK), `TimestampMixin`, `Base`.

- [ ] **Step 1:** Viết `KnowledgeDocument` (unit_id FK, file_name, checksum, is_published, timestamps, unique unit_id+file_name) và `KnowledgeChunk` (document_id FK cascade, order_no, chunk_type enum, section_title, raw_text, structured JSONB nullable, search_vector TSVECTOR Computed).
- [ ] **Step 2:** Đăng ký export trong `app/models/__init__.py`.
- [ ] **Step 3:** Viết migration nối `down_revision = "d4f61c2a9b07"`: `create_table` cho 2 bảng (search_vector dùng `sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed("to_tsvector('simple', raw_text)", persisted=True))`), `create_index` GIN trên `search_vector`, FK cascade cho `document_id`.
- [ ] **Step 4:** Chạy `alembic upgrade head` trên DB dev, xác nhận không lỗi.
- [ ] **Step 5:** Commit: `feat: thêm bảng knowledge document và chunk`

### Task 2: Parser docx theo section

**Files:**
- Add: `backend/app/services/knowledge_parser.py`
- Add: `backend/tests/test_knowledge_parser.py`

**Interfaces:**
- Produces: `parse_lesson_docx(path: Path) -> list[ParsedChunk]` (dataclass: order_no, chunk_type, section_title, raw_text, structured).
- Consumes: `python-docx` (`Document`, `document.element.body` traversal).

- [ ] **Step 1:** Viết test trước dùng file thật `Knowledge_Base/Global Success/G7/GS7 - UNIT 3 - LESSON.docx` (golden reference đã dùng ở 1B): assert có đủ 4 loại chunk_type xuất hiện, ít nhất 1 chunk vocabulary có `structured["word"] == "volunteer"`, ít nhất 1 chunk grammar có raw_text chứa "Simple Past Tense" (từ table).
- [ ] **Step 2:** Chạy test — RED (module chưa tồn tại).
- [ ] **Step 3:** Cài đặt `parse_lesson_docx`: duyệt `body` theo thứ tự, phân loại header bằng từ khoá (VOCABULARY/WORD FORM/PREPOSITION|PHRASE/GRAMMAR), áp quy tắc regex theo từng loại section như đặc tả, xử lý table trong section grammar bằng nối cell text.
- [ ] **Step 4:** Chạy lại test — GREEN. Chạy thêm trên 3-4 file khác (G6 Unit 2 có tiêu đề section khác chuẩn, G8 bất kỳ) trong cùng test để bắt lệch cấu trúc không raise lỗi.
- [ ] **Step 5:** Commit: `feat: thêm parser docx bài học Global Success`

### Task 3: Import script idempotent

**Files:**
- Add: `backend/app/import_knowledge.py`
- Add: `backend/tests/test_import_knowledge.py`

**Interfaces:**
- Produces: `import_global_success(db: Session, base_path: Path) -> ImportStats`.
- Consumes: `parse_lesson_docx`, `Unit`, `Grade`, `KnowledgeDocument`, `KnowledgeChunk`.

- [ ] **Step 1:** Viết test RED: import 1 file thật vào `seeded_db`, assert tạo đúng 1 `KnowledgeDocument` + N chunk; import lại lần 2 assert số dòng không đổi (idempotent); sửa nội dung file tạm (copy sang thư mục temp, đổi 1 dòng) rồi import lại assert chunk cũ bị thay bằng chunk mới.
- [ ] **Step 2:** Cài đặt: quét thư mục theo `G{6,7,8}/GS{grade} - UNIT {n} - LESSON.docx`, parse grade/unit từ tên, tính sha256, so khớp `KnowledgeDocument` hiện có theo `unit_id+file_name`, tạo mới hoặc xoá-chèn-lại chunk theo checksum.
- [ ] **Step 3:** Thêm `if __name__ == "__main__"` chạy qua `python -m app.import_knowledge`, log số file/chunk đã xử lý.
- [ ] **Step 4:** Chạy test — GREEN.
- [ ] **Step 5:** Commit: `feat: thêm script import tài liệu Global Success`

### Task 4: API tra cứu full-text

**Files:**
- Add: `backend/app/routers/knowledge.py`
- Add: `backend/app/schemas/knowledge.py`
- Modify: `backend/app/main.py`
- Add: `backend/tests/test_knowledge_search.py`

**Interfaces:**
- Produces: `GET /knowledge/search` (query: unit_id, grade_id, chunk_type, q, limit).
- Consumes: `require_any_role`, `KnowledgeChunk`, `plainto_tsquery`, `ts_rank`.

- [ ] **Step 1:** Viết test RED: seed + import 1-2 file thật, gọi API filter theo `unit_id` (trả đúng số chunk), theo `q=volunteer` (trả chunk vocabulary chứa từ, sắp theo rank), test 401 khi chưa đăng nhập, test Admin và Giáo viên đều 200.
- [ ] **Step 2:** Viết schema `KnowledgeChunkOut` (id, chunk_type, section_title, raw_text, structured, document: {unit_id, file_name}).
- [ ] **Step 3:** Cài đặt router: build query filter `unit_id`/`grade_id` (join Unit)/`chunk_type`, nhánh có `q` dùng `func.plainto_tsquery("simple", q)` match `search_vector`, order theo `ts_rank`; nhánh không `q` order theo `order_no`. Giới hạn `limit` (default 20, max 100). Chỉ lấy `document.is_published = true`.
- [ ] **Step 4:** Đăng ký router trong `main.py`.
- [ ] **Step 5:** Chạy test — GREEN, chạy toàn bộ `pytest backend/tests -q`.
- [ ] **Step 6:** Commit: `feat: thêm API tra cứu full-text kho kiến thức`

### Task 5: Chạy import thật + verification cuối

**Files:** không sửa code, chỉ verification.

- [ ] **Step 1:** Trong container backend (hoặc venv local với DB dev), chạy `python -m app.import_knowledge`, xác nhận nhập đủ 36 file, không lỗi.
- [ ] **Step 2:** Chạy lại lần 2, xác nhận không tạo trùng (log số chunk không đổi).
- [ ] **Step 3:** Gọi thử `GET /knowledge/search?unit_id=<unit3-lop7>` và `?q=volunteer` qua curl, xác nhận kết quả đúng golden reference.
- [ ] **Step 4:** Chạy toàn bộ `pytest backend/tests -q` và kiểm tra lint backend (nếu có cấu hình ruff/mypy).
- [ ] **Step 5:** Cập nhật `docs/engineering/DEVELOPMENT_PLAN.vi.md` mục 1A: tick "Nhập tài liệu PDF/DOCX/text..." (thu hẹp phạm vi đã làm: Global Success G6-G8; Cambridge/Tense/G9 còn lại).
- [ ] **Step 6:** Commit: `doc: cập nhật tiến độ nhập tài liệu Global Success`

# Thiết kế nhập tài liệu Global Success vào Knowledge Base

## Mục tiêu

Hiện thực hoá phần còn thiếu của Giai đoạn 1A (DEVELOPMENT_PLAN mục 3): nhập tài liệu → trích xuất → chunk + metadata → full-text search, **giới hạn phạm vi lần này ở bộ Global Success lớp 6-8** (36 file `.docx` bài học theo Unit trong `Knowledge_Base/Global Success/G6|G7|G8`). Không đụng tới Cambridge, Tense, hay G9 (xem phần "Không thuộc phạm vi").

Đây là bước chuẩn bị dữ liệu cho RAG (PRD mục 9); chưa làm vector/embedding — việc đó thuộc Giai đoạn 1D. Lần này chỉ cần **keyword/full-text search** kết hợp **metadata filter** theo Unit/khối lớp, đúng như 9.1-9.2 mô tả cho phần "vẫn dùng được khi kho nhỏ".

## Khảo sát dữ liệu nguồn

Mỗi file `GS{grade} - UNIT {n} - LESSON.docx` (G6, G7, G8 — mỗi khối 12 file, khớp 1-1 với `Unit.order_no` đã seed) có cấu trúc lặp lại nhưng **không đồng nhất tuyệt đối giữa các Unit**:

- Tiêu đề Unit (dòng đầu, chứa "UNIT").
- Một hoặc nhiều đoạn **VOCABULARY** (có Unit chỉ có 1 khối, có Unit tách thành `GETTING STARTED - VOCABULARY`, `A CLOSER LOOK 1 – VOCABULARY`...) — mỗi dòng dạng `word /IPA/ (pos): nghĩa`, nhưng một số dòng thiếu IPA hoặc dấu `:` (không khớp regex).
- **WORD FORM** — mỗi đoạn (paragraph) có thể chứa nhiều dòng con phân tách bằng newline nội bộ, gom các biến thể của cùng một từ gốc.
- **PREPOSITIONS AND PHRASES** — mỗi đoạn là một cụm từ `phrase: nghĩa`.
- **GRAMMAR** / **GRAMMAR AND STRUCTURES** / **GRAMMAR & STRUCTURES** — có đoạn dạng danh sách (`pattern: nghĩa`) và có thể có **bảng** (table) chứa mẫu câu/ví dụ (ví dụ bảng "Simple Past Tense" trong GS7 Unit 3) — phải đọc `document.element.body` theo đúng thứ tự xen kẽ paragraph/table, không dùng riêng `doc.paragraphs`/`doc.tables` (thứ tự sẽ sai).

Vì tiêu đề section không đồng nhất 100%, phân loại section dùng **so khớp từ khoá** (chứa "VOCABULARY" → vocabulary; bằng "WORD FORM" → word_form; chứa "PREPOSITION" hoặc "PHRASE" → phrase; chứa "GRAMMAR" → grammar), không so khớp chuỗi tuyệt đối.

## Mô hình dữ liệu

Bảng mới (migration nối tiếp `d4f61c2a9b07`):

```
knowledge_documents
  id UUID PK
  unit_id UUID FK units.id NOT NULL
  file_name VARCHAR(255) NOT NULL
  checksum VARCHAR(64) NOT NULL   -- sha256 nội dung file, dùng để re-import không tạo trùng
  is_published BOOLEAN NOT NULL DEFAULT true
  created_at / updated_at
  UNIQUE(unit_id, file_name)

knowledge_chunks
  id UUID PK
  document_id UUID FK knowledge_documents.id NOT NULL (ondelete CASCADE)
  order_no INTEGER NOT NULL          -- thứ tự xuất hiện trong tài liệu
  chunk_type ENUM(vocabulary, word_form, phrase, grammar, other) NOT NULL
  section_title VARCHAR(255) NOT NULL  -- tiêu đề section gốc, vd "A CLOSER LOOK 1 – VOCABULARY"
  raw_text TEXT NOT NULL             -- luôn có, dùng làm nguồn full-text search kể cả khi parse structured thất bại
  structured JSONB NULL              -- best-effort: {"word","ipa","pos","meaning"} | {"pattern","meaning","example"} | {"phrase","meaning"} | null
  search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', raw_text)) STORED
  GIN INDEX ON search_vector
```

Không tạo bảng liên kết `GrammarPoint` ở lần này — chunk `grammar` chỉ lưu text thô + structured tối thiểu; việc auto-link với 32 `GrammarPoint` đã seed để dành cho một task riêng vì tên mẫu câu trong sách không khớp 1-1 với tên `GrammarPoint` (rủi ro map sai).

`is_published` mặc định `true` (dữ liệu coi như đã duyệt vì lấy từ sách giáo khoa chính thức, không qua UI duyệt ở vòng này — nhất quán với cách seed catalog hiện tại: seed thẳng, không qua workflow duyệt thủ công).

## Parser (`app/services/knowledge_parser.py`)

Hàm thuần (không đụng DB), input là đường dẫn `.docx`, output `list[ParsedChunk]` (dataclass: `order_no, chunk_type, section_title, raw_text, structured`).

Thuật toán:
1. Duyệt `document.element.body` theo thứ tự, phân loại từng phần tử là `paragraph` hay `table`.
2. Dòng đầu tiên không rỗng → bỏ qua (tiêu đề Unit, đã có `Unit.title` trong DB).
3. Mỗi paragraph in hoa toàn bộ, ngắn (<60 ký tự) → coi là header mới, cập nhật `current_section_title` + `current_type` theo quy tắc từ khoá ở trên; không tạo chunk cho chính header.
4. Trong section `vocabulary`: mỗi paragraph phi-header → 1 chunk. Thử regex `^(?P<word>.+?)\s*/(?P<ipa>[^/]+)/\s*\((?P<pos>[^)]+)\)\s*:\s*(?P<meaning>.+)$`; khớp thì set `structured`, không khớp thì `structured=None` (raw_text vẫn lưu nguyên).
5. Trong section `word_form`: mỗi paragraph có thể chứa nhiều dòng (`\n`) — mỗi paragraph là 1 chunk (giữ nguyên cụm biến thể từ cùng gốc), `structured=None` (không tách nhỏ hơn — cấu trúc câu trong 1 dòng không đều để regex tin cậy).
6. Trong section `phrase`: mỗi paragraph → 1 chunk, thử regex `^(?P<phrase>.+?):\s*(?P<meaning>.+)$`.
7. Trong section `grammar`: mỗi paragraph → 1 chunk dạng list (thử regex phrase ở trên cho `pattern`/`meaning`); mỗi **table** gặp trong section này → 1 chunk có `raw_text` là nối các cell theo dòng (`" | ".join(cell texts)`, các dòng nối bằng `\n`), `chunk_type=grammar`, `structured=None`.
8. Paragraph rỗng bị bỏ qua hoàn toàn (không tạo chunk).
9. Section không khớp từ khoá nào (ví dụ dòng tiêu đề phụ như "GETTING STARTED" đứng riêng không kèm "VOCABULARY") → `chunk_type=other`, vẫn giữ toàn bộ paragraph con dưới nó làm chunk raw_text để không mất dữ liệu, không raise lỗi.

Parser không được phép raise exception vì một Unit có cấu trúc lệch — lỗi tối đa là chunk rơi vào `other`, không chặn import các file khác (đúng nguyên tắc "một block lỗi không làm mất phần đã hoàn thành" ở PRD mục 16, áp dụng tương tự cho import).

## Import script (`app/import_knowledge.py`)

Idempotent theo mẫu `seed.py`:
- Quét `Knowledge_Base/Global Success/G6`, `G7`, `G8` (đường dẫn lấy từ config, mặc định tương đối gốc repo).
- Với mỗi file: tính `sha256`; tìm `Unit` theo `grade.number` (parse từ tên thư mục `G6`→6) + `order_no` (parse số Unit từ tên file bằng regex `UNIT (\d+)`).
- Nếu `KnowledgeDocument` đã tồn tại (unique `unit_id+file_name`) và `checksum` không đổi → bỏ qua (không parse lại, không tạo trùng chunk).
- Nếu đã tồn tại nhưng `checksum` khác (file được cập nhật) → xoá toàn bộ chunk cũ của document đó rồi parse + insert lại (cascade delete-orphan lo phần xoá qua ORM).
- Nếu chưa tồn tại → tạo `KnowledgeDocument` + toàn bộ `KnowledgeChunk` từ parser.
- Không parse G9 (khác cấu trúc — xem "Không thuộc phạm vi"), không parse Cambridge/Tense.
- Chạy độc lập qua `python -m app.import_knowledge` (giống cách `seed.py` chạy), **không** gộp vào `run_seed()` vì đây là nhập tài liệu lớn, không phải danh mục tĩnh — tránh làm chậm/phình seed mặc định dùng trong mọi lần khởi động container.

## API tra cứu (`GET /knowledge/search`)

- Router mới `app/routers/knowledge.py`, `prefix="/knowledge"`, dependency `require_any_role` (giống `/catalog/*` — lý do đã ghi trong đặc tả `teacher-only-exams`: không chặn màn quản trị kho kiến thức tương lai).
- Query params: `unit_id` (optional UUID), `grade_id` (optional UUID — lọc theo mọi unit thuộc khối lớp đó), `chunk_type` (optional enum), `q` (optional string, full-text qua `to_tsquery('simple', ...)`, cần escape/format input để tránh lỗi cú pháp tsquery), `limit` (default 20, max 100).
- Không có `q` → trả theo thứ tự `order_no` (dùng cho "xem toàn bộ chunk của 1 Unit"). Có `q` → dùng `plainto_tsquery` (an toàn hơn `to_tsquery` với input tự do, không cần escape thủ công) kết hợp `ts_rank` để sắp xếp kết quả.
- Response: danh sách chunk kèm `document.unit_id`, `document.file_name`, `chunk_type`, `section_title`, `raw_text`, `structured`.
- Chỉ trả chunk thuộc `document.is_published = true`.

## Test

- `test_knowledge_parser.py`: parse trực tiếp 2-3 file mẫu thật trong `Knowledge_Base/Global Success/G7` (không mock) để bắt hồi quy khi cấu trúc sách thay đổi — tương tự cách `test_exams.py` dùng golden reference Unit 3 thật. Assert: có đúng section types xuất hiện, ít nhất N chunk vocabulary có `structured` khớp, ít nhất 1 chunk grammar lấy từ table.
- `test_import_knowledge.py`: chạy import trên 1 file thật vào DB test, assert idempotent (chạy 2 lần không tăng số dòng), assert cập nhật lại khi checksum đổi (giả lập bằng sửa nội dung tạm rồi import lại).
- `test_knowledge_search.py`: seed catalog + import 1-2 file thật, gọi API filter theo `unit_id`, theo `q` (một từ vựng biết trước trong Unit 3 golden reference, ví dụ "volunteer"), assert Admin/Giáo viên đều gọi được (200), người chưa đăng nhập nhận 401.

## Không thuộc phạm vi

- Không nhập Cambridge, Tense, hay `Knowledge_Base/Global Success/G9/*` (cấu trúc hoàn toàn khác — tài liệu ôn tập gộp nhiều Unit, không tách theo Unit như G6-G8).
- Không có UI Admin xem/tìm kiếm tài liệu (đã dời sang Giai đoạn 1D theo DEVELOPMENT_PLAN mục 3, phần 1C).
- Không làm embedding/vector search, không làm reranker.
- Không tự động liên kết chunk `grammar` với `GrammarPoint` đã seed.
- Không nhập PDF/text thô — chỉ `.docx` theo cấu trúc Global Success.

## Tiêu chí hoàn thành

- Migration chạy được, bảng mới có GIN index trên `search_vector`.
- Import 36 file G6-G8 qua Docker Compose thật, không lỗi, chạy lại lần 2 không tạo trùng dòng.
- `GET /knowledge/search?unit_id=...` trả đúng chunk của Unit 3 lớp 7 (golden reference), tìm theo `q=volunteer` trả về chunk vocabulary chứa từ này.
- pytest mới + toàn bộ test cũ đều pass; backend lint sạch.

# Đặc tả nhập tài liệu ngữ pháp (Kiến thức chung) vào Kho kiến thức

## Bối cảnh

Trang "Kho kiến thức" (`feat/1c-admin-knowledge-base`) hiện chỉ hỗ trợ tài liệu bài học Global Success gắn với 1 Unit cụ thể, dùng `parse_lesson_docx` — parser nhận diện tiêu đề mục bằng quy tắc "dòng ngắn + viết HOA toàn bộ" (khớp đúng cách Global Success trình bày VOCABULARY/GRAMMAR/WORD FORM/PREPOSITION).

Chủ dự án gửi mẫu tài liệu ngữ pháp tổng hợp (ví dụ: The Simple Present — cấu trúc, cách dùng, trạng từ tần suất, cách phát âm -s/-es, action verbs) — đây là loại tài liệu cho mục "Kiến thức chung" (32 `GrammarPoint`: 12 thì + 20 cấu trúc câu, PRD 7.4), **không gắn với Unit nào cả**, mà gắn với 1 `GrammarPoint` cụ thể. Đã xác nhận bằng cách đọc code: nếu upload tài liệu này qua luồng hiện tại, tiêu đề mục sẽ không được nhận diện (không viết hoa toàn bộ) và **toàn bộ bảng (table) trong file sẽ bị bỏ qua** (`parse_lesson_docx` chỉ giữ bảng khi mục hiện tại đã được nhận diện là GRAMMAR).

## Mục tiêu

Cho phép Admin nhập tài liệu ngữ pháp gắn với 1 `GrammarPoint` (thay vì 1 `Unit`), dùng parser riêng phù hợp cấu trúc tài liệu dạng này (nhiều mục nhỏ: cấu trúc câu, cách dùng, trạng từ, cách phát âm...), không mất bảng.

Không làm trong task này: tự động chọn/gộp nội dung này vào prompt sinh câu AI (RAG chưa nối vào pipeline sinh đề — vẫn chờ Giai đoạn 1D, xem PRD mục 23.3 quyết định #15). Task này chỉ giải quyết phần nhập + lưu trữ + xem trong Kho kiến thức.

## Model

`KnowledgeDocument`:
- `unit_id` chuyển thành **nullable** (trước đây bắt buộc).
- Thêm `grammar_point_id: UUID | None` (FK `grammar_points.id`, nullable).
- Ràng buộc: đúng một trong hai (`unit_id` hoặc `grammar_point_id`) phải có giá trị — kiểm tra ở tầng service/router, không dùng DB CHECK constraint (giữ nguyên tắc đơn giản đã áp dụng cho `Exam`, xem PRD 22.1).
- Unique constraint cũ `(unit_id, file_name)` giữ nguyên cho nhánh Unit; thêm `(grammar_point_id, file_name)` cho nhánh ngữ pháp (Postgres coi NULL khác NULL nên 2 constraint không xung đột nhau).

Migration mới: nới lỏng `unit_id` + thêm cột `grammar_point_id` + unique constraint mới.

## Parser mới

`app/services/grammar_parser.py`, hàm `parse_grammar_reference_docx(path: Path) -> list[ParsedChunk]`:

- Dùng chung helper duyệt block (`_iter_block_items`) và `_table_to_text` với `knowledge_parser.py` — tách 2 hàm này sang `app/services/docx_utils.py` để dùng chung, tránh trùng lặp.
- Nhận diện tiêu đề mục bằng **định dạng in đậm** của đoạn văn (`paragraph.runs và tất cả run có `.bold` truthy) thay vì quy tắc viết hoa toàn bộ — phù hợp hơn với tài liệu ngữ pháp tiếng Việt (tiêu đề như "Cách dùng:", "Cách thêm đuôi 's/es' vào động từ:" không viết hoa nhưng thường được in đậm trong Word).
- Toàn bộ nội dung trong tài liệu này đều là `DocumentChunkType.GRAMMAR` (không phân biệt VOCABULARY/WORD_FORM/PHRASE như Global Success) — `section_title` mang tên mục con (Cách dùng, Trạng từ chỉ tần suất, Cách phát âm...).
- Bảng (table) **luôn được giữ lại** làm 1 chunk riêng dưới `section_title` hiện tại — không gate theo điều kiện loại mục như parser cũ, vì toàn bộ tài liệu này vốn đã là ngữ pháp.
- Không raise exception với cấu trúc lệch chuẩn — tệ nhất mọi đoạn rơi vào `section_title=""` nhưng vẫn được lưu (không mất dữ liệu), cùng triết lý với `parse_lesson_docx`.

## API

`admin_knowledge.py`:
- `upload_document`: `unit_id` đổi thành optional (`Form(None)`), thêm `grammar_point_id: uuid.UUID | None = Form(None)`. Validate: đúng một trong hai được cung cấp (400 nếu cả hai hoặc không có cái nào; 400 nếu `grammar_point_id` không tồn tại). Khi có `grammar_point_id`: idempotent theo checksum trên `(grammar_point_id, file_name)`, dùng `parse_grammar_reference_docx`.
- `_document_out`: `unit` trở thành optional; thêm `grammar_point: {id, name, group_name, topic_name} | None`.
- `list_documents`: không đổi endpoint, chỉ trả thêm field mới.

Schema `KnowledgeDocumentAdminOut`: `unit: KnowledgeUnitRefOut | None`, thêm `grammar_point: KnowledgeGrammarPointRefOut | None`.

## Frontend

`AdminKnowledgePage.tsx`:
- Popup "Nhập tài liệu" thêm chọn "Loại nguồn": **Theo Unit (Global Success)** / **Theo ngữ pháp (Kiến thức chung)**. Chọn ngữ pháp thì hiện 2 select lồng nhau: Chuyên đề (`GrammarTopic`) → Cấu trúc/Thì (`GrammarPoint`, gộp qua các `GrammarGroup`) — tái dùng `listGrammarTopics()` đã có.
- Cột "Khối / Unit" trong bảng đổi thành "Nguồn": hiện "Lớp X · Unit Y — Tên" hoặc "Kiến thức chung · Tên GrammarPoint".
- Bộ lọc: thêm lọc theo "Loại nguồn" (Tất cả / Global Success / Kiến thức chung); lọc khối lớp chỉ áp dụng cho tài liệu theo Unit.

## Kiểm thử

Backend: upload tài liệu ngữ pháp tạo đúng chunk theo mục in đậm, giữ nguyên bảng; idempotent theo checksum trên `(grammar_point_id, file_name)`; từ chối khi thiếu cả hai hoặc có cả hai nguồn; từ chối `grammar_point_id` không tồn tại; liệt kê trả đúng `grammar_point` khi có; xóa tài liệu ngữ pháp vẫn cascade đúng.

Frontend: chọn "Theo ngữ pháp" hiện đúng 2 select lồng nhau; upload gọi API với đúng `grammar_point_id`; bảng hiển thị đúng cột Nguồn cho cả 2 loại; lọc theo loại nguồn hoạt động đúng.

Verification cuối: `pytest`, Vitest, `npm run lint`, `npm run build`, rebuild + verify qua Docker Compose.

## Git workflow

Tiếp tục trên nhánh `feat/1c-admin-knowledge-base` (cùng PR #15 đang mở, cùng chủ đề Kho kiến thức) — không tạo nhánh/PR mới.

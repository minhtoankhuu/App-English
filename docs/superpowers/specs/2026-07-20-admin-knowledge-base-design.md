# Đặc tả trang Admin quản lý kho kiến thức

## Bối cảnh

`DEVELOPMENT_PLAN.vi.md` mục 1C liệt kê "kho kiến thức" là 1 trong 3 màn Admin còn thiếu chức năng chỉnh sửa. Sau khi bỏ kế hoạch thư viện hình ảnh (PRD 23.3 #18) và xác định "dạng bài & template" nên dời sang Giai đoạn 1D (gắn với prompt LLM thật), kho kiến thức là việc còn lại **làm được ngay** — không phụ thuộc AI thật, chỉ là CRUD + upload trên dữ liệu đã có model từ trước (`KnowledgeDocument`/`KnowledgeChunk`, nhập bằng script `python -m app.import_knowledge` từ nhánh `feat/1a-knowledge-base-global-success`).

Hiện trạng: model + `GET /knowledge/search` (đọc, full-text) đã có; **chưa có API quản trị nào** (liệt kê, xuất bản/ẩn, xóa, upload qua UI).

## Mục tiêu

Trang Admin `/admin/knowledge` cho phép:
- Xem danh sách toàn bộ tài liệu đã nhập (khối lớp, Unit, tên file, số đoạn, trạng thái xuất bản, ngày nhập).
- Xuất bản/ẩn một tài liệu (`is_published`) — tài liệu ẩn không xuất hiện trong `GET /knowledge/search` (route đã lọc `is_published.is_(True)` sẵn, không cần đổi).
- Xóa một tài liệu (xóa cứng, cascade toàn bộ chunk).
- **Upload tài liệu mới trực tiếp qua UI** (.docx) thay vì chỉ chạy script CLI — tái dùng đúng parser `parse_lesson_docx` hiện có, cùng logic idempotent theo checksum SHA-256 như `app/import_knowledge.py` (file trùng checksum → không đổi; file cùng Unit+tên nhưng khác checksum → thay toàn bộ chunk cũ; mới → tạo).

Không làm trong task này: sửa nội dung từng chunk, phiên bản hóa (versioning) tài liệu, hỗ trợ Cambridge/Tense/G9 (cấu trúc khác, task riêng theo ghi chú ở 1A).

## API

Router mới `app/routers/admin_knowledge.py`, prefix `/admin/knowledge-documents`, `require_admin` — cùng khuôn mẫu `admin.py`/`audit.py` hiện có.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/admin/knowledge-documents` | – | `list[KnowledgeDocumentAdminOut]` |
| POST | `/admin/knowledge-documents` | multipart: `unit_id` (form), `file` (.docx) | `KnowledgeDocumentAdminOut` (201, hoặc 200 nếu checksum không đổi) |
| PATCH | `/admin/knowledge-documents/{id}` | `{is_published: bool}` | `KnowledgeDocumentAdminOut` |
| DELETE | `/admin/knowledge-documents/{id}` | – | 204 |

`KnowledgeDocumentAdminOut`: `id, file_name, is_published, chunk_count, created_at, updated_at, unit: {id, order_no, title, grade_number}`.

Upload validate: `unit_id` phải tồn tại (400 nếu không), file phải đuôi `.docx` (400 nếu không). Nội dung file được ghi ra file tạm (`tempfile.NamedTemporaryFile`) để tái dùng `parse_lesson_docx(path: Path)` không đổi chữ ký hàm. Không raise lỗi nếu file lệch cấu trúc — parser vốn không raise, chunk lệch rơi vào `DocumentChunkType.OTHER` (đã ghi trong docstring gốc).

## Frontend

- `frontend/src/api/client.ts`: thêm `apiUpload<T>(path, formData)` — không set header `Content-Type` (để trình duyệt tự set `multipart/form-data; boundary=...`), khác với `apiRequest` hiện luôn ép `application/json`.
- `frontend/src/api/adminKnowledge.ts` (mới): `listKnowledgeDocuments`, `uploadKnowledgeDocument(unitId, file)`, `updateKnowledgeDocument(id, payload)`, `deleteKnowledgeDocument(id)`.
- `frontend/src/pages/AdminKnowledgePage.tsx` (mới), route `/admin/knowledge`: bảng `data-table` (Khối/Unit, Tên file, Số đoạn, Trạng thái, Ngày nhập, hành động Ẩn/Xuất bản + Xóa), nút "+ Nhập tài liệu" mở `Modal` chọn Khối lớp → Unit (tái dùng `listGrades`/`listUnitsForGrade`) + input file `.docx`, xác nhận xóa bằng `window.confirm` (cùng khuôn mẫu `AdminTeachersPage`/`ExamListPage`).
- `AdminOverviewPage.tsx`: card "Kho kiến thức & RAG" đổi `implemented: true`, `to: "/admin/knowledge"`, chip hiển thị số tài liệu đã xuất bản (gọi `listKnowledgeDocuments` để đếm, giống cách card "Tài khoản & phân quyền" đang đếm giáo viên hoạt động).
- `App.tsx`: thêm route `/admin/knowledge` (`adminOnly(<AdminKnowledgePage />)`).

## Kiểm thử

Backend pytest: liệt kê trả đúng `chunk_count`/`unit.grade_number`; upload file mới tạo document + chunk đúng số lượng parser trả về; upload lại file checksum không đổi → không tạo chunk trùng, trả document cũ; upload file cùng Unit+tên nhưng nội dung khác → thay toàn bộ chunk cũ; từ chối file không phải `.docx`; từ chối `unit_id` không tồn tại; xóa tài liệu xóa cascade chunk; PATCH xuất bản/ẩn đúng; giáo viên (không phải Admin) bị 403; chưa đăng nhập 401.

Frontend Vitest: hiển thị danh sách, mở popup upload chọn khối/unit/file rồi gọi đúng API, toggle xuất bản/ẩn, xóa có xác nhận, lỗi hiển thị không làm mất bảng.

Verification cuối: `pytest`, Vitest, `npm run lint`, `npm run build`, rebuild + verify qua Docker Compose.

## Git workflow

- Branch: `feat/1c-admin-knowledge-base` từ `main` (đã merge các PR trước đó).
- Commit tài liệu: `doc: đặc tả trang Admin kho kiến thức`.
- Commit backend, frontend theo lớp, commit tiến độ cuối `doc: cập nhật tiến độ trang Admin kho kiến thức`.
- Push, tạo PR vào `main`, không tự merge.

# Thiết kế đồng bộ luồng đề thi (list/builder/review/export) theo prototype

## Mục tiêu

Sau khi đồng bộ khung (sidebar/login), tiếp tục port giao diện 4 trang còn lại của luồng giáo viên theo đúng `prototype/index.html` + `styles.css`: `ExamListPage`, `ExamBuilderPage` (+ `SortableBlockList`, `ExamPreview`), `ExamReviewPage`, `ExamExportPage`.

## Quyết định kiến trúc quan trọng: giữ nguyên routing, chỉ đổi giao diện

Prototype dựng cả 4 bước ("Nguồn kiến thức" → "Cấu trúc đề" → "Duyệt câu hỏi" → "Xuất DOCX") như 1 trang tĩnh, chuyển "view" bằng JS thuần, không đổi URL. Code thật hiện tách thành route riêng (`/exams`, `/exams/:id/builder`, `/exams/:id/review`, `/exams/:id/export`) với cơ chế bảo vệ race-condition theo route (`useRouteGeneration`, đã làm ở nhánh `fix/exam-page-route-races`) — đây là hạ tầng quan trọng chống lỗi khi chuyển đề nhanh hoặc back/forward trình duyệt.

**Quyết định: giữ nguyên cấu trúc route hiện tại, không gộp thành 1 trang.** Chỉ port phần **giao diện** (màu sắc, layout, card, badge, icon) của từng bước sang đúng trang route tương ứng. Điều này giữ được toàn bộ hạ tầng chống race-condition, không cần sửa `App.tsx` hay backend.

Khác biệt còn lại so với prototype (chấp nhận, không cố match 100%):
- Nguồn kiến thức (khối lớp/Unit/trình độ) chọn 1 lần lúc **tạo đề** (`ExamListPage`), không sửa lại giữa chừng ở bước 2 như prototype — đúng theo API/model hiện tại (`Exam.grade_id/unit_id` cố định sau khi tạo).
- Bản xem trước A4 là **nội dung thật** dựng động từ API `GET /exams/{id}/preview` (nhiều trang, câu hỏi thật), không phải các đường kẻ giả lập như prototype — chỉ áp style `.paper` (khung A4, font Cambria, shadow), giữ nguyên nội dung động.
- Không dựng `<dialog class="block-editor">` riêng cho việc sửa từng block — giữ nguyên cách sửa số câu/điểm tại chỗ (inline) đã có, chỉ đổi style thẻ.

## Ánh xạ trang ↔ phần prototype

| Trang thật | Phần prototype | Class chính sẽ port |
|---|---|---|
| `ExamListPage` | `#myexams-view` + phần tạo đề | `.exam-list`, `.exam-row`, `.configuration` (form tạo đề) |
| `ExamBuilderPage` | bước 2 "Cấu trúc đề" | `.builder-grid`, `.configuration`, `.type-grid`/`.type-option`, `.section-heading`, `.config-footer` |
| `SortableBlockList` | `.block-list` trong bước 2 | `.block-list`, `.exam-block`, `.block-badge` (badge màu theo dạng bài), `.chips`/`.chip`, `.drag`, `.item-actions` |
| `ExamPreview` | `.preview-panel`/`.paper` | `.preview-panel`, `.paper`, `.paper-header`, `.metrics` |
| `ExamReviewPage` | bước 3 "Duyệt câu hỏi" | `.review-head`, `.review-block`, `.q-card`, `.q-head`, `.q-status`, `.q-passage`, `.q-options`, `.q-answer`, `.q-warning`, `.q-actions`, `.review-footer` |
| `ExamExportPage` | bước 4 "Xuất DOCX" | `.export-card`, `.export-options`, `.radio-row`, `.answer-red` |

Thêm `StepsIndicator` (component mới, dùng chung) — port `.steps`/`.step(.completed/.active)` của prototype, hiển thị bước hiện tại theo route (`/builder`→2, `/review`→3, `/export`→4); bước 1 "Nguồn kiến thức" luôn coi là hoàn thành khi đã có đề (đã tạo ở `ExamListPage`).

## CSS cần thêm vào `index.css`

Từ `prototype/styles.css`, port nguyên khối (giữ tên class):
`.workspace` steps: `.steps`, `.step(.completed/.active)`, `.step-dot`
`.builder-grid`, `.configuration`, `.section-heading`, `.form-grid`, `.type-grid`, `.type-option`, `.block-heading`
`.block-list`, `.exam-block(.dragging/.hidden)`, `.block-badge` (+ biến thể màu `.t-pron/.t-vocab/.t-read/.t-write` — mở rộng thêm biến thể cho các dạng còn lại vì đề thật có 10 dạng chứ không chỉ 4 như ví dụ prototype), `.chips`, `.chip(.score)`, `.drag`, `.item-actions`
`.preview-panel`, `.paper`, `.paper-header`, `.metrics`
`.review-head`, `.review-progress`, `.review-block`, `.review-block-title`, `.q-card(.approved/.locked)`, `.q-head`, `.q-no`, `.q-status`, `.q-passage`, `.q-text`, `.q-options`, `.q-answer`, `.q-warning`, `.q-actions`, `.review-footer`
`.exam-list`, `.exam-row`, `.exam-info`, `.exam-meta`, `.exam-actions`
`.export-card`, `.export-meta`, `.export-options`, `.radio-row`, `.export-actions`, `.answer-red`

Không port: `.role-switch`, `.block-editor` dialog, phần JS demo (crc32/zip DOCX — code thật export qua API thật).

## Không thuộc phạm vi

- Không đổi bất kỳ API call, state machine, hay logic race-condition nào.
- Không đổi `AdminOverviewPage`/`AdminAuditLogsPage` (đã port basic, không thuộc luồng đề thi).
- Không thêm block-editor dialog riêng (giữ inline edit số câu/điểm như hiện tại).
- Không đổi cấu trúc route.

## Test

- Chạy toàn bộ test hiện có của 5 file sau mỗi lần sửa (`ExamListPage` chưa có test — chỉ sanity qua build/lint); không đổi hành vi nên test dựa trên text/role phải vẫn pass. Nếu test có assert style inline cụ thể (hiếm), sửa theo cấu trúc DOM mới mà không đổi ý nghĩa test.
- `npm test -- --run`, `npm run lint`, `npm run build` phải xanh sau khi xong toàn bộ.

## Tiêu chí hoàn thành

- Cả 4 trang + preview + block list dùng đúng bảng màu/spacing/class đã dùng cho sidebar, nhìn nhất quán với khung đã port.
- Toàn bộ test/lint/build pass.

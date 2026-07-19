# Đặc tả kéo-thả block và xem trước đề A4

## Mục tiêu

Hoàn thiện trải nghiệm xây dựng đề trong Giai đoạn 1C bằng hai khả năng:

- Giáo viên kéo-thả để đổi thứ tự block, đồng thời vẫn có nút Lên/Xuống hỗ trợ bàn phím và màn hình nhỏ.
- Trang Builder hiển thị bản xem trước nhiều trang A4, cập nhật theo cấu trúc đề hiện tại trước khi gọi AI.

Task triển khai cả backend và frontend. Giao diện dùng phong cách tối giản hiện có để người dùng có thể chỉnh thẩm mỹ sau. Task không thay đổi DOCX renderer, không thêm thao tác chỉnh câu hỏi, không tạo migration và không tiêu thụ hạn mức sinh đề.

## Kiến trúc

Backend cung cấp một read model chuyên biệt qua `GET /exams/{exam_id}/preview`. Dịch vụ preview đọc đề và chuyển dữ liệu thành danh sách trang, block và dòng câu hỏi đã chuẩn hóa. Backend là nguồn sự thật cho thứ tự, số câu đánh dồn, tổng điểm và phân trang; frontend chỉ render response thành các tờ A4 bằng HTML/CSS.

Kéo-thả và nút Lên/Xuống cùng dùng endpoint `POST /exams/{exam_id}/blocks/reorder` hiện có. Frontend cập nhật thứ tự lạc quan, lưu toàn bộ danh sách block ID và rollback nếu request lỗi.

Không thêm thư viện drag-and-drop. Frontend dùng HTML Drag and Drop API, React state và các event `dragstart`, `dragover`, `drop`, `dragend`.

## API preview

Endpoint:

```text
GET /exams/{exam_id}/preview
```

Endpoint yêu cầu Admin hoặc Teacher đăng nhập và dùng cùng quy tắc sở hữu với các endpoint đề hiện tại: không tìm thấy trả 404, người dùng khác sở hữu trả 403. Endpoint chỉ đọc dữ liệu, không ghi database và không gọi quota service.

Response:

```json
{
  "exam_id": "uuid",
  "title": "Unit 3 — Revision Test",
  "total_questions": 12,
  "total_points": "10.0",
  "page_count": 2,
  "pages": [
    {
      "page_number": 1,
      "blocks": [
        {
          "block_id": "uuid",
          "section_number": 1,
          "section_label": "I",
          "title": "Pronunciation",
          "instruction": null,
          "question_start": 1,
          "question_end": 5,
          "question_count": 5,
          "points": "2.0",
          "continuation": false,
          "questions": [
            {
              "question_number": 1,
              "prompt_text": null,
              "passage_text": null,
              "is_placeholder": true
            }
          ]
        }
      ]
    }
  ]
}
```

`section_number` và `section_label` phản ánh thứ tự block toàn đề. Nếu một block bị tách giữa hai trang, phần tiếp theo giữ cùng section và có `continuation=true`. `question_start`/`question_end` là phạm vi nằm trên đoạn của trang đó, không phải toàn bộ block.

`total_points` là tổng `points` của block theo Decimal và serialize thành chuỗi một chữ số thập phân. Đề chưa có block trả `total_questions=0`, `total_points="0.0"`, `page_count=1` và một trang có `blocks=[]`.

## Quy tắc dựng nội dung preview

Block được xử lý theo `order_no`. Số câu đánh liên tục từ 1 qua mọi block.

- Nếu block chưa có câu hỏi, dịch vụ tạo đủ `question_count` item placeholder với `prompt_text=null`, `passage_text=null`, `is_placeholder=true`.
- Nếu block đã có câu, câu thật được sắp theo `order_no` và trả `prompt_text`, `passage_text`, `is_placeholder=false`.
- Nếu số câu thật ít hơn `question_count`, dịch vụ nối placeholder đến đủ cấu hình block.
- Nếu số câu thật nhiều hơn `question_count`, preview vẫn hiển thị toàn bộ câu thật để không che dữ liệu đã lưu.
- Passage lặp lại trên từng câu theo dữ liệu hiện có; frontend chỉ render passage khi khác passage của item ngay trước trong cùng đoạn block.

Nhãn section dùng số La Mã từ `I` trở lên và hỗ trợ số block lớn hơn 20 bằng hàm chuyển số nguyên dương tổng quát.

## Ước tính và ngắt trang A4

Preview là ước tính ổn định, không cam kết pixel-perfect với Word. Dịch vụ dùng đơn vị dòng logic:

- Mỗi trang có sức chứa `42` dòng.
- Header đề ở trang đầu tốn `5` dòng; header trang tiếp theo tốn `2` dòng.
- Header block tốn `2` dòng, cộng `1` nếu có instruction.
- Mỗi câu placeholder tốn `2` dòng.
- Câu thật tốn `2 + ceil(len(prompt_text) / 90)` dòng.
- Passage tốn thêm `ceil(len(passage_text) / 90)` dòng khi passage cần render.
- Footer/số trang được chừa sẵn `2` dòng trong sức chứa và không xuất hiện trong block data.

Khi block không vừa phần còn lại, dịch vụ đưa header block và câu đầu sang trang kế tiếp nếu trang hiện tại chưa có câu của block. Khi một block dài hơn một trang, dịch vụ tách tại ranh giới câu; đoạn tiếp theo có `continuation=true` và header section được tính lại. Không tách một câu giữa hai trang. Một câu đơn lẻ vượt sức chứa còn lại được chuyển sang trang mới; nếu bản thân câu vượt sức chứa một trang, câu vẫn đứng riêng trong trang đó để thuật toán luôn kết thúc.

## Giao diện Builder

Desktop dùng grid hai cột: vùng cấu hình block bên trái và preview bên phải. Preview dùng `position: sticky` ở màn hình đủ rộng để giáo viên theo dõi khi chỉnh cấu trúc. Ở breakpoint nhỏ, hai vùng xếp dọc và preview nằm sau cấu hình.

Mỗi trang preview:

- Có tỷ lệ A4 dọc `210 / 297`, nền trắng, bóng nhẹ và padding mô phỏng lề.
- Hiển thị tiêu đề đề, section, instruction, phạm vi câu, điểm và dòng câu hỏi.
- Placeholder hiển thị `Câu N. ................................................................`.
- Câu thật hiển thị prompt rút gọn; passage được hiển thị theo quy tắc không lặp liên tiếp.
- Footer hiển thị `Trang X/Y`.
- Phía trên preview hiển thị tổng số câu và tổng điểm.
- Đề rỗng hiển thị một trang với thông báo “Thêm phần để xem trước đề”.

Preview được tải cùng exam. Sau thêm, xóa, sửa block, lưu grammar selection hoặc reorder thành công, frontend làm mới cả exam và preview. Preview có trạng thái loading riêng nên không chặn phần chỉnh sửa. Nếu tải lỗi, vùng preview hiện thông báo và nút `Thử lại`.

## Kéo-thả và reorder

Mỗi card block có tay nắm `⠿` với nhãn truy cập `Kéo để sắp xếp <tên block>`. Toàn card nhận trạng thái drag thông qua tay nắm; con trỏ và viền thể hiện block đang kéo cùng vị trí thả.

Luồng thả:

1. Lưu snapshot danh sách block hiện tại.
2. Tính danh sách mới bằng `moveBlock(blocks, sourceId, targetId)`; target là block mà source được chèn trước.
3. Cập nhật React state ngay để UI và thứ tự card phản hồi tức thời.
4. Khóa các điều khiển reorder và gọi API với toàn bộ block ID.
5. Khi thành công, thay state bằng response của API và làm mới preview.
6. Khi thất bại, khôi phục snapshot, giữ preview cũ và hiển thị thông báo lỗi.

Thả lên chính block nguồn không gọi API. `dragend` luôn xóa trạng thái drag. Trong lúc request reorder đang chạy, không nhận thêm thao tác kéo hoặc nút Lên/Xuống.

Nút Lên/Xuống dùng cùng helper thuần `moveBlock` và cùng hàm lưu reorder. Nút ở biên bị disable thay vì gửi request không thay đổi.

## Phân tách component

- `frontend/src/exam-builder/blockOrder.ts`: helper thuần tính thứ tự mới, không phụ thuộc React.
- `frontend/src/exam-builder/SortableBlockList.tsx`: render block card, drag events và nút fallback; nhận callbacks nghiệp vụ từ page.
- `frontend/src/exam-preview/ExamPreview.tsx`: render loading, error, empty và nhiều trang A4.
- `frontend/src/api/exams.ts`: thêm `getExamPreview(examId)`.
- `frontend/src/types/examPreview.ts`: type phản ánh response backend.
- `backend/app/services/exam_preview.py`: đánh số, tính dòng và chia trang.
- `backend/app/schemas/exam_preview.py`: response models.
- `backend/app/routers/exams.py`: endpoint preview và kiểm tra quyền sở hữu hiện có.

`ExamBuilderPage` tiếp tục điều phối tải dữ liệu và mutation nhưng không chứa thuật toán phân trang hoặc thuật toán move.

## Xử lý lỗi

- Preview 401/403/404 giữ semantics API hiện có.
- Lỗi preview không làm trang Builder biến mất và không khóa CRUD block.
- Lỗi reorder rollback đúng snapshot, hiển thị thông báo từ `ApiError` nếu có và không tải lại preview.
- Lỗi reload sau mutation hiển thị lỗi chung hiện có; dữ liệu preview cuối cùng vẫn được giữ cho đến lần tải thành công tiếp theo.
- Không retry mutation reorder tự động để tránh thay đổi thứ tự ngoài ý muốn.

## Kiểm thử

Backend pytest:

- Đề rỗng trả một trang và tổng bằng 0.
- Placeholder đủ theo `question_count`, số câu liên tục qua nhiều block và nhãn La Mã đúng.
- Câu thật được dùng, thiếu câu được bù placeholder, nhiều hơn cấu hình vẫn không bị ẩn.
- Tổng điểm dùng Decimal chính xác.
- Đề dài tạo nhiều trang; block dài tách theo câu và đánh dấu continuation.
- Câu quá dài không làm thuật toán lặp vô hạn.
- Chưa đăng nhập trả 401, người không sở hữu trả 403, ID không tồn tại trả 404.

Frontend Vitest/Testing Library:

- `moveBlock` xử lý kéo lên, kéo xuống và source bằng target.
- Preview render empty, loading, error/retry và nhiều trang với footer đúng.
- Placeholder và câu thật hiển thị đúng, passage liên tiếp không lặp.
- Drag/drop gửi đúng mảng ID, cập nhật lạc quan và rollback khi API lỗi.
- Nút Lên/Xuống dùng cùng reorder, disable ở biên và trong lúc đang lưu.
- Builder tải lại preview sau mutation thành công nhưng không tải lại khi reorder thất bại.

Verification cuối gồm toàn bộ `pytest`, Vitest, `npm run lint` và `npm run build`.

## Git workflow

- Branch: `feat/1c-exam-builder-preview` từ `main` sau khi pull merge mới nhất.
- Commit tài liệu: `doc: đặc tả kéo thả và xem trước đề` và `doc: lập kế hoạch kéo thả và xem trước đề`.
- Commit backend: `feat: thêm API xem trước đề A4`.
- Commit frontend: `feat: thêm kéo thả và xem trước đề A4`.
- Commit tiến độ: `doc: cập nhật tiến độ trình dựng đề`.
- Push branch và tạo Draft PR vào `main`; không tự merge.

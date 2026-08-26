# Đề thi thật — nguồn câu mẫu cho RAG

Đặt file `.docx` đề thi thật vào đây, chia theo khối lớp.

## Quy ước tên file

Tên file **phải chứa số Unit** để hệ thống gắn đúng Unit (cùng quy ước với thư mục
`Global Success/`, xem `_UNIT_NUMBER_RE` trong `backend/app/import_knowledge.py`):

    Knowledge_Base/Exams/G8/GS8 - UNIT 1 - DE THI.docx
    Knowledge_Base/Exams/G7/GS7 - UNIT 3 - KIEM TRA GIUA KY.docx

Không có chữ `UNIT <số>` trong tên thì file bị bỏ qua.

## Vì sao cần

Sách trong `Global Success/` gần như không có câu ví dụ — `GS7 - UNIT 1 - LESSON.docx`
chỉ có 2/231 đoạn là câu tiếng Anh hoàn chỉnh, toàn bộ còn lại là mục từ điển. Model
vì thế không có câu thật nào để bắt chước nên tự bịa, ra đề nhạt và lặp ngữ cảnh.

Đề thật nạp vào đây trở thành câu mẫu **đúng Unit đang ra đề** — thay cho kho mẫu viết
tay chung trong `backend/app/services/prompts.py`.

## Định dạng bên trong

File Word bình thường, giữ nguyên như đề gốc. Càng gần đề in ra càng tốt:
đánh số câu, các lựa chọn A/B/C/D, dòng câu lệnh của từng phần.

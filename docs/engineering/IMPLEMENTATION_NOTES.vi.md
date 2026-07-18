# GHI CHÚ TRIỂN KHAI KỸ THUẬT

**Mục đích:** gom mọi chi tiết đã chốt ở mức triển khai để đội code (hoặc phiên làm việc sau) bắt đầu được ngay, không phải đọc lại lịch sử thảo luận. Yêu cầu sản phẩm ở [../product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md](../product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md); prototype tham chiếu ở `prototype/` là **reference implementation** cho hành vi UI và DOCX renderer.

**Cập nhật:** 18/07/2026.

## 1. Dữ liệu seed đã được giáo viên duyệt

### 1.1 Trình độ

- Trục chuẩn lưu dữ liệu: CEFR `A1, A2, B1, B2, C1`. Cambridge chỉ là nhãn/nguồn kiến thức.
- Quy đổi Cambridge → CEFR (mặc định, Admin chỉnh được): `Starters→A1, Movers→A1, Flyers→A2, KET→B1, PET→B2`. Lưu ý: cao hơn chuẩn Cambridge chính thức một bậc, theo mặt bằng luyện thi thực tế.
- Gợi ý trình độ theo lớp: `1–4→A1, 5–7→A2, 8–9→B1, 10–12→B2` (bảng `SUGGEST` trong prototype). Gợi ý được ghi đè tự do.

### 1.2 Chuyên đề "Tense" — 12 thì, kèm trình độ tối thiểu

| Nhóm | Thì (trình độ tối thiểu) |
|---|---|
| Hiện tại | Present Simple (A1) · Present Continuous (A1) · Present Perfect (A2) · Present Perfect Continuous (B1) |
| Quá khứ | Past Simple (A1) · Past Continuous (A2) · Past Perfect (B1) · Past Perfect Continuous (B2) |
| Tương lai | Future Simple (A1) · Future Continuous (B1) · Future Perfect (B2) · Future Perfect Continuous (B2) |

### 1.3 Chuyên đề "Các dạng cấu trúc câu" — 20 node

| Nhóm | Cấu trúc (trình độ tối thiểu) |
|---|---|
| Nền tảng (Primary) | Khẳng định/phủ định/nghi vấn (A1) · There is/are (A1) · Câu mệnh lệnh (A1) · Câu cảm thán (A2) · So sánh hơn/nhất/bằng (A2) · Câu hỏi đuôi (A2) |
| Trọng tâm THCS | Điều kiện loại 0-1-2 (A2) · Bị động (B1) · Tường thuật (B1) · Mệnh đề quan hệ (B1) · Câu ước (B1) · Used to (B1) · too...to/enough/so...that (B1) · Gerund & infinitive (B1) |
| Nâng cao THPT | Điều kiện loại 3/hỗn hợp (B2) · Đảo ngữ (B2) · Câu chẻ (B2) · Truyền khiến (B2) · Rút gọn mệnh đề (B2) · Câu giả định (C1) |

Quy tắc chung: node vượt trình độ của đề → **cảnh báo, không chặn**.

### 1.4 Danh mục Unit Global Success

- Lớp 6–9: 12 Unit/lớp; lớp 10–12: 10 Unit/lớp — tên Unit đầy đủ đã nhập trong `GS_UNIT_TITLES` của prototype, dùng làm seed.
- Lớp 1–5: **chưa xác nhận** tên Unit (prototype tạm đánh số; lớp 1–2: 16, lớp 3–5: 20). Cần giáo viên duyệt trước khi seed.

### 1.5 Thư viện dạng bài khởi đầu (10 dạng) và câu lệnh tiếng Anh mặc định

Danh sách dạng và câu lệnh chuẩn nằm trong `KIND_INSTRUCTIONS` của prototype (ví dụ Trắc nghiệm → "Choose the best answer A, B, C or D."). Mỗi dạng bài lưu câu lệnh mặc định, giáo viên ghi đè được theo block.

### 1.6 Độ dài nội dung theo khối lớp

**Câu hỏi trắc nghiệm / word form** (số từ mỗi câu, Admin chỉnh được):

| Cấp học | Số từ | Trạng thái |
|---|---|---|
| THCS | 12–14 | giáo viên đã chốt |
| Tiểu học | 6–10 | đề xuất, chờ xác nhận |
| THPT | 14–18 | đề xuất, chờ xác nhận |

Yêu cầu prompt sinh (bắt buộc): mỗi câu đủ ngữ cảnh + có dấu hiệu nhận biết đáp án (câu chia thì phải có trạng từ/mốc thời gian; câu từ vựng có ngữ cảnh gợi nghĩa). Validation: đếm từ, cảnh báo khi lệch khoảng; heuristic tùy chọn: kiểm tra sự hiện diện của dấu hiệu theo thì (danh sách marker: yesterday, last..., ago, since, for, at the moment, always, every day, next..., by the time...); thẩm định cuối cùng thuộc giáo viên khi duyệt.

**Bài đọc** — áp dụng cho các dạng có đoạn văn (đọc hiểu True/False, cloze test). Bảng mặc định (Admin chỉnh được):

| Khối lớp | Số từ |
|---|---|
| 1–2 | 20–40 |
| 3–5 | 40–80 |
| 6–7 | 80–150 |
| 8–9 | 150–250 |
| 10–12 | 250–350 |

Khoảng số từ đưa vào prompt sinh; giáo viên đặt số từ mục tiêu theo block; validation đếm từ của đoạn sinh ra và cảnh báo khi lệch khoảng (không chặn). Hàm tham chiếu: `passageRange(grade)` trong prototype.

## 2. DOCX Renderer — thông số đã chốt và kiểm chứng

Định dạng chuẩn (quyết định #12, đã xác thực bằng python-docx trên file sinh thử):

| Thuộc tính | Giá trị | Trong OOXML |
|---|---|---|
| Font | Times New Roman | `w:rFonts` |
| Tiêu đề đề | in hoa, 14pt, đậm, căn giữa | `w:sz w:val="28"` |
| Nội dung | 11.5pt | `w:sz w:val="23"` |
| Lề (Narrow) | 1,27 cm bốn phía | `w:pgMar` 720 twips |
| Khổ giấy | A4 dọc | `w:pgSz` 11906×16838 twips |
| Giãn dòng | 1,15; không space trước/sau đoạn | `w:spacing w:line="276" w:lineRule="auto" w:before="0" w:after="0"` |
| Lựa chọn A–D | ký hiệu `A.` in đậm; dàn tab 4 cột đều | tab stops 2616 / 5233 / 7850 twips (bề rộng dùng được 10466) |
| Lựa chọn dài | >24 ký tự → 2 cột/dòng (A./B. trên, C./D. dưới) | tab stop 5233 |
| Đáp án tô đỏ | cả lựa chọn đúng đỏ + đậm; tự luận điền đáp án đỏ | `w:color w:val="C00000"` |
| Bài đọc | justify | `w:jc w:val="both"` |
| Ngăn section | một đoạn trống giữa các phần I/II/III | |

Kinh nghiệm kỹ thuật đã xác nhận:

- `.docx` tối thiểu chỉ cần 3 file trong ZIP: `[Content_Types].xml`, `_rels/.rels`, `word/document.xml`. ZIP có thể để chế độ stored (không nén) — Word và python-docx đều đọc tốt.
- Thứ tự phần tử trong `w:pPr` phải là: `w:tabs` → `w:spacing` → `w:jc`.
- Phần gạch chân trong câu phát âm (br<u>ea</u>d) tách thành run riêng có `w:u`.
- Hai kiểu xuất: chỉ đề (không đáp án) và đáp án tô đỏ inline; với câu không có lựa chọn (tự luận), kiểu tô đỏ chèn dòng đáp án đỏ sau câu hỏi.
- Prototype có bản cài đặt đầy đủ bằng JS thuần (hàm `buildZip`, `buildDocumentXml` trong `prototype/index.html`) — dùng làm tham chiếu; sản phẩm thật nên dùng thư viện DOCX phía server nhưng phải cho ra đúng các thông số trên.

## 3. Hành vi UI đã chốt qua prototype (bản đặc tả hành vi)

1. **Luồng 4 bước:** Cấu trúc đề → Sinh (validate cấu hình trước khi gọi AI) → Duyệt câu hỏi → Cấu hình xuất + lưu. Tải DOCX **chỉ** từ "Đề của tôi", chỉ với đề trạng thái Sẵn sàng xuất đã lưu cấu hình xuất.
2. **Checklist dạng bài ↔ block đồng bộ hai chiều:** tick tạo block (mặc định "block ma" chờ cấu hình), bỏ tick/xóa block gỡ nhau; dạng bài của block không sửa trong dialog block (một nguồn chỉnh sửa duy nhất).
3. **Chọn nguồn kiến thức 3 mục:** Global Success (Unit theo lớp) · Kiến thức chung (chuyên đề → hiện picker thì/cấu trúc) · Cambridge (chứng chỉ → tự gợi ý CEFR).
4. **Block:** kéo thả sắp xếp, số La Mã tự đánh lại; dialog chỉnh block gồm tiêu đề, hướng dẫn, độ khó (Nhận biết/Thông hiểu/Vận dụng/Hỗn hợp), số câu, điểm (bước 0.5), trình độ ghi đè, 2 cờ đảo câu/đảo đáp án, prompt riêng.
5. **Màn duyệt:** mỗi câu hiển thị đáp án, lời giải, chip kiến thức + trình độ + nguồn RAG; cảnh báo (trùng ngân hàng theo ngưỡng cosine 0.90, vượt trình độ); hành động Duyệt (toggle), Sinh lại (bị chặn khi câu đã khóa hoặc đã duyệt), Khóa (toggle). Nút hoàn tất chỉ mở khi 100% câu duyệt.
6. **Đề của tôi:** danh sách đề + trạng thái (Nháp/Đã kiểm duyệt/Sẵn sàng xuất); lưu snapshot — file đã xuất không đổi khi đề bị sửa sau đó; câu sửa tay phải duyệt lại.
7. **Xem trước A4** cập nhật trực tiếp theo mọi thao tác cấu hình; số câu đánh dồn qua các section.

## 4. Việc cần chốt trước khi code

- Danh mục Unit lớp 1–5 (giáo viên xác nhận).
- Nguồn nội dung mục Cambridge: tài liệu luyện thi riêng hay tái dùng Global Success gắn nhãn.
- Spike Giai đoạn 0 (đặc tả mục 21): sinh thử dạng phát âm/trọng âm/đọc hiểu có hình trên nội dung Unit 3 thật trước khi đầu tư nền móng.
- Lựa chọn công nghệ theo tiêu chí đặc tả mục 22 + nguyên tắc hạ tầng tối thiểu 22.1 (job table trong DB, vector extension, một tiến trình).

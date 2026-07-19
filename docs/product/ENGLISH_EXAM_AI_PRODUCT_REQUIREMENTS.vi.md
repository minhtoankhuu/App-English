# ĐẶC TẢ Ý TƯỞNG SẢN PHẨM

## Nền tảng AI tạo bài tập và đề tiếng Anh theo kiến thức sách giáo khoa

**Phiên bản:** 1.6  
**Ngày:** 19/07/2026  
**Trạng thái:** Đã bắt đầu triển khai (Giai đoạn 1A + lõi 1B). 1.1: bổ sung tiêu chí định lượng, quản lý hình ảnh, spike khả thi, nguyên tắc hạ tầng tối thiểu. 1.2: bổ sung trình độ mục tiêu (CEFR/Cambridge) và chọn dạng bài bằng checklist. 1.3: bảng ánh xạ lớp → trình độ, phân nhóm theo cấp học và ba mục kho kiến thức (Kiến thức chung: Tense, cấu trúc câu / Global Success / Cambridge theo chứng chỉ) do giáo viên xác nhận. 1.4: skeleton Giai đoạn 1A (backend FastAPI, frontend React/TS, Docker Compose) đã dựng và kiểm chứng chạy được. 1.5: lõi tạo đề Giai đoạn 1B (Exam/Block/Question, MockAIProvider, Validation Engine, API + frontend đầy đủ đến xuất DOCX, mã đề A/B/C/D) chạy trên MockAIProvider, chưa gồm RAG. 1.6: Admin quản lý tài khoản giáo viên (tạo/khóa/đặt lại mật khẩu) — API + trang thật, có phân quyền theo vai trò ở cả backend và frontend.

## 1. Tóm tắt điều hành

Dự án là một ứng dụng web hỗ trợ giáo viên tạo bài tập và đề tiếng Anh có cấu trúc, dựa trên kiến thức đã được quản trị trong kho RAG. Giáo viên chọn lớp, bộ sách, Unit, kiến thức, dạng bài, độ khó và template; có thể bổ sung yêu cầu tự do; hệ thống dùng AI sinh câu hỏi có cấu trúc, cung cấp đáp án, lời giải và nguồn kiểm chứng. Giáo viên bắt buộc kiểm duyệt, chỉnh sửa và khóa nội dung trước khi xuất DOCX khổ A4 để in hoặc tiếp tục biên tập trong Microsoft Word.

MVP phục vụ một Admin và khoảng 1–3 giáo viên, chưa chia theo trường hoặc trung tâm. Học sinh làm bài online, chấm điểm, phân tích kết quả và ứng dụng mobile là các hướng mở rộng, không thuộc phạm vi phiên bản đầu tiên.

## 2. Vấn đề cần giải quyết

- Soạn đề thủ công mất nhiều thời gian, đặc biệt khi phải tạo nhiều dạng bài và nhiều mã đề.
- AI sinh văn bản tự do khó kiểm soát phạm vi kiến thức, đáp án và bố cục in.
- File Word mẫu thường có cấu trúc linh hoạt theo các phần I/II/III và A/B/C, không phù hợp với một template bất biến.
- Kiến thức từ nhiều lớp, bộ sách và Unit dễ bị trộn lẫn nếu không có metadata và truy xuất nguồn chặt chẽ.
- Nội dung AI không thể được đưa thẳng vào bản in nếu chưa kiểm tra và giáo viên chưa duyệt.

## 3. Mục tiêu sản phẩm

1. Giúp giáo viên tạo đề hoàn chỉnh mà không cần viết prompt phức tạp.
2. Kết hợp form cấu hình bắt buộc với ô yêu cầu tự do.
3. Bảo đảm câu hỏi bám theo kho kiến thức đã được Admin xuất bản.
4. Cho phép thay đổi từng khối của đề mà không phải sinh lại toàn bộ.
5. Lưu đáp án, lời giải, kiến thức mục tiêu và nguồn RAG cho từng câu.
6. Tạo mã A/B/C/D bằng cách đảo câu và đáp án một cách an toàn.
7. Xuất DOCX A4 có thể chỉnh sửa và in.
8. Giữ kiến trúc mở để bổ sung local LLM, học sinh làm online và mobile.

### 3.1 Chỉ số thành công chính

Giá trị cốt lõi của sản phẩm là tiết kiệm thời gian soạn đề mà vẫn giữ chất lượng. MVP theo dõi tối thiểu hai chỉ số:

- **Tỷ lệ chấp nhận:** phần trăm câu do AI sinh được giáo viên duyệt mà không cần sửa nội dung. Mục tiêu MVP: ≥ 70% với các dạng bài chuẩn.
- **Thời gian tạo đề:** thời gian từ lúc bắt đầu cấu hình đến khi xuất DOCX, so với soạn tay. Mục tiêu MVP: giảm ít nhất 50%.

Hai chỉ số này được đo qua dữ liệu duyệt/sửa câu và thời gian thao tác đã có sẵn trong hệ thống, không cần công cụ đo riêng.

## 4. Phạm vi MVP

### 4.1 Trong phạm vi

- Đăng nhập và phân quyền Admin/Giáo viên.
- Danh mục đa lớp, đa bộ sách, đa phiên bản và đa Unit.
- Admin nhập PDF có text, DOCX hoặc văn bản vào kho kiến thức.
- RAG với metadata filtering, hybrid search và rerank tùy chọn.
- Lớp AI Provider dùng API trước, có thể thêm local LLM sau.
- Thư viện dạng bài chuẩn và các biến thể do Admin cấu hình.
- Thư viện hình ảnh do Admin quản lý cho các dạng bài có hình.
- Trình độ mục tiêu theo CEFR (A1–C1) và Cambridge (Starters/Movers/Flyers/KET/PET) gắn cho đề và từng khối; kiến thức nhóm theo cấp học.
- Chọn dạng bài bằng danh sách tick khi tạo đề; đề chỉ sinh các dạng đã chọn.
- Template chuẩn dạng khối; giáo viên clone và tùy chỉnh bản riêng.
- Sinh, chỉnh sửa, khóa, tạo lại từng câu/từng khối.
- Ma trận đề tùy chọn; dùng mặc định nếu giáo viên không thiết lập.
- Ngân hàng chỉ chứa câu đã được giáo viên duyệt.
- Tạo mã đề bằng đảo thứ tự câu và đáp án.
- Xuất DOCX: chỉ đề (bản phát học sinh) hoặc đề có đáp án tô đỏ (bản giáo viên).
- Audit log, quản lý lỗi, hạn mức và theo dõi sử dụng AI ở mức cơ bản.

### 4.2 Ngoài phạm vi

- Tài khoản học sinh, lớp học, giao bài và làm bài online.
- Chấm điểm, thống kê và đề xuất luyện tập.
- Ứng dụng mobile.
- Quản lý trường/trung tâm hoặc multi-tenant.
- OCR cho ảnh và PDF scan.
- Xuất PDF trực tiếp.
- Sinh các mã đề có câu hỏi khác nhau nhưng tương đương độ khó.

## 5. Vai trò và quyền hạn

### 5.1 Admin

- Quản lý tài khoản giáo viên và trạng thái tài khoản.
- Quản lý khối lớp, bộ sách, phiên bản, Unit, chủ đề và kiến thức.
- Nhập, kiểm tra, xuất bản, ngừng sử dụng và lập phiên bản tài liệu RAG.
- Quản lý dạng bài, schema đầu ra, prompt, validation rule và renderer.
- Tạo, cập nhật, xuất bản và ngừng sử dụng template chuẩn.
- Cấu hình AI provider, model, API key, embedding và reranker.
- Quản lý thư viện hình ảnh (biển báo, thông báo, minh họa) dùng cho các dạng bài có hình.
- Xem lịch sử tác vụ, lỗi, chi phí và audit log.

### 5.2 Giáo viên

- Chọn nguồn kiến thức đã được Admin xuất bản.
- Chọn trình độ mục tiêu (CEFR hoặc Cambridge) cho đề và tick các dạng bài muốn xuất hiện.
- Clone template chuẩn thành bản cá nhân và chỉnh cấu trúc khối.
- Cấu hình đề, ma trận tùy chọn và prompt bổ sung.
- Sinh, xem nguồn, sửa, khóa hoặc tạo lại nội dung.
- Thêm/xóa câu thủ công và kéo thả thứ tự.
- Duyệt đề, đưa câu đạt yêu cầu vào ngân hàng.
- Tạo mã A/B/C/D và xuất DOCX.

### 5.3 Học sinh

Không phải vai trò hoạt động trong MVP. Mô hình dữ liệu câu hỏi vẫn phải đủ cấu trúc để tái sử dụng cho bài làm online trong giai đoạn sau.

## 6. Kiến trúc mô-đun đề xuất

| Mô-đun | Trách nhiệm chính |
|---|---|
| Authentication & Users | Đăng nhập, mật khẩu, vai trò và trạng thái tài khoản |
| Academic Catalog | Khối lớp, bộ sách, phiên bản, Unit, chủ đề và mục tiêu học tập |
| Knowledge Base & RAG | Nhập tài liệu, trích xuất, metadata, chunking, indexing và retrieval |
| Exercise Type Library | Schema, prompt, validation và renderer của từng dạng bài |
| Block Template Builder | Template gồm section và block có thể thêm/xóa/sắp xếp |
| Exam Generator | Điều phối cấu hình, RAG, AI và sinh dữ liệu có cấu trúc |
| Validation Engine | Kiểm tra schema, đáp án, trùng lặp, nguồn và ma trận |
| Exam Editor | Biên tập, khóa, tạo lại, kéo thả và kiểm duyệt |
| Question Bank | Lưu, tìm kiếm và tái sử dụng câu đã duyệt |
| Exam Variants | Tạo mã đề và ánh xạ đáp án theo seed |
| DOCX Renderer | Dựng đề A4 từ dữ liệu có cấu trúc |
| Configuration & Audit | Provider, model, API key, hạn mức, lỗi và lịch sử |

Các mô-đun giao tiếp qua interface rõ ràng. RAG, AI và DOCX không phụ thuộc trực tiếp vào giao diện, giúp bổ sung mobile hoặc học sinh làm online mà không viết lại lõi tạo đề.

## 7. Template và thư viện dạng bài

### 7.1 Cấu trúc template

Một template gồm thông tin đầu đề, các Section I/II/III, các Block A/B/C bên trong và khu vực đáp án. Ký hiệu hiển thị được tự đánh lại theo thứ tự; mỗi section/block có ID ổn định trong dữ liệu.

Mỗi block có:

- Tiêu đề và hướng dẫn.
- Dạng bài hoặc biến thể.
- Số câu, điểm và độ khó.
- Trình độ mục tiêu (kế thừa từ đề, có thể ghi đè theo khối).
- Kiến thức/kỹ năng mục tiêu.
- Quy tắc dùng hình, đoạn đọc hoặc ngữ cảnh chung.
- Quy tắc đảo câu/đáp án.
- Khoảng trống trả lời và quy tắc ngắt trang.
- Prompt bổ sung và trạng thái bật/tắt.

Admin duy trì template chuẩn. Giáo viên clone, tùy chỉnh và có thể lưu thành template cá nhân; thay đổi không ảnh hưởng mẫu gốc.

### 7.2 Các dạng bài khởi đầu

Dựa trên đề tham chiếu Global Success 7 – Unit 3, thư viện đầu tiên nên hỗ trợ:

- Chọn từ có phần gạch chân phát âm khác.
- Chọn từ có trọng âm khác.
- Trắc nghiệm ngữ pháp, từ vựng và giao tiếp.
- Đọc biển báo/thông báo có hình ảnh.
- Cloze test chọn từ điền đoạn văn.
- Đọc hiểu True/False kết hợp câu hỏi trắc nghiệm.
- Word form/verb form.
- Bài tập dựa trên mục từ điển.
- Viết lại câu theo từ gợi ý hoặc cấu trúc tương đương.
- Nối (matching) từ/cụm từ với nghĩa, hình ảnh hoặc vế câu.
- Điền từ vào chỗ trống không cho sẵn lựa chọn (gap fill).

Cấu trúc và renderer của dạng chuẩn được kiểm soát bằng code. Admin được thay prompt, quy tắc và tạo biến thể; dạng hoàn toàn mới có cấu trúc đặc biệt có thể cần bổ sung code.

### 7.3 Rủi ro riêng theo dạng bài

Một số dạng bài có rủi ro kỹ thuật đã được nhận diện và phải xử lý ngay trong thiết kế:

- **Phát âm và trọng âm:** LLM sai nhiều ở kiến thức ngữ âm. Đáp án của hai dạng này phải được kiểm chứng bằng từ điển phát âm máy đọc được (ví dụ CMU Pronouncing Dictionary hoặc dữ liệu IPA tương đương) trong Validation Engine, không tin kết quả LLM đơn thuần. Câu không kiểm chứng được bị đánh dấu cảnh báo bắt buộc giáo viên xem.
- **Đọc biển báo/thông báo có hình:** AI không sinh được hình ảnh biển báo đạt chất lượng in. Hình lấy từ thư viện hình ảnh do Admin quản lý (upload, gắn metadata chủ đề/Unit); AI chỉ chọn hình từ thư viện và sinh câu hỏi xoay quanh hình đó. Nếu thư viện chưa có hình phù hợp, block báo thiếu nguồn thay vì tự sinh.

### 7.4 Trình độ mục tiêu

Ngoài khối lớp, đề và từng khối được gắn trình độ mục tiêu theo hai hệ quy chiếu phổ biến:

- **CEFR:** A1, A2, B1, B2, C1.
- **Cambridge:** Starters, Movers, Flyers, KET, PET.

Quy đổi Cambridge → CEFR dùng làm mặc định (theo mặt bằng giảng dạy thực tế do giáo viên xác nhận):

| Cambridge | CEFR tương ứng |
|---|---|
| Starters, Movers | A1 |
| Flyers | A2 |
| KET | B1 |
| PET | B2 |

Ánh xạ gợi ý khối lớp → trình độ, nhóm theo cấp học:

| Cấp học | Khối lớp | Trình độ gợi ý |
|---|---|---|
| Primary (Tiểu học) | 1–5 | A1 → A2 (Starters/Movers/Flyers) |
| Secondary (THCS) | 6–7 | A2 |
| Secondary (THCS) | 8–9 | A2–B1 |
| High school (THPT) | 10–12 | B1+ → B2; C1 cho nâng cao |

Bảng trên cao hơn chuẩn đầu ra của chương trình GDPT 2018 (hết lớp 9 đạt A2, hết lớp 12 đạt B1) vì phản ánh mặt bằng luyện thi thực tế; đây là giá trị mặc định, Admin chỉnh được toàn bộ bảng ánh xạ.

Khi chọn nguồn kiến thức, kho hiển thị cho giáo viên theo **ba mục** (đã chốt với giáo viên):

- **Kiến thức chung:** không phụ thuộc bộ sách, chia theo 3 cấp học Primary/Secondary/High school, gồm các chuyên đề khởi đầu **Tense (12 thì tiếng Anh)** và **Các dạng cấu trúc câu**; Admin thêm được chuyên đề khác sau này. Mỗi thì/cấu trúc là một node kiến thức (`GrammarPoint`); giáo viên tick chọn từng node làm phạm vi sinh đề (nhóm theo Hiện tại/Quá khứ/Tương lai đối với thì), node vượt trình độ của đề được đánh dấu cảnh báo nhưng không bị chặn.
- **Global Success:** kiến thức bám bộ sách, tổ chức theo lớp và Unit; nội dung của cả 3 cấp học gom về một cây Global Success. Số lượng Unit và chủ đề khác nhau theo từng lớp (ví dụ lớp 6–9 có 12 Unit, lớp 10–12 có 10 Unit); danh mục Unit của mỗi lớp do Admin nhập và là dữ liệu, không gán cứng trong code.
- **Cambridge:** kiến thức luyện thi chứng chỉ, tổ chức theo cấp độ Starters/Movers/Flyers/KET/PET. Chọn chứng chỉ sẽ gợi ý trình độ CEFR tương ứng theo bảng quy đổi; ô trình độ của đề chỉ hiển thị trục CEFR (A1–C1), nhất quán với nguyên tắc CEFR là trục chuẩn.

Bộ node khởi đầu của chuyên đề **Các dạng cấu trúc câu** (mỗi mục một node kèm trình độ tối thiểu, giáo viên đã duyệt danh sách):

- **Nền tảng (Primary):** khẳng định/phủ định/nghi vấn (A1), There is/are (A1), câu mệnh lệnh (A1), câu cảm thán (A2), so sánh hơn/nhất/bằng (A2), câu hỏi đuôi (A2).
- **Trọng tâm THCS (Secondary):** câu điều kiện loại 0–2 (A2–B1), câu bị động (B1), câu tường thuật (B1), mệnh đề quan hệ (B1), câu ước (B1), used to (B1), too...to/enough/so...that (B1), gerund & infinitive (B1).
- **Nâng cao THPT (High school):** câu điều kiện loại 3 và hỗn hợp (B2), đảo ngữ (B2), câu chẻ (B2), câu truyền khiến (B2), rút gọn mệnh đề (B2), câu giả định (C1).

Đây là cách trình bày ở bước chọn nguồn; cấu trúc danh mục nền (Grade/BookSeries/Unit/cấp học) không thay đổi, nên bổ sung bộ sách khác sau này chỉ là thêm một mục hiển thị mới.

Nguyên tắc áp dụng:

- Hệ thống gợi ý trình độ mặc định từ khối lớp theo bảng trên; giáo viên điều chỉnh được.
- CEFR là trục chuẩn lưu trên dữ liệu câu hỏi; nhãn Cambridge là quy đổi hiển thị, tránh hai hệ song song gây mâu thuẫn khi lọc ngân hàng.
- Trình độ được đưa vào prompt sinh để kiểm soát độ phức tạp từ vựng và cấu trúc; mỗi câu sinh ra lưu lại trình độ mục tiêu.
- Validation kiểm tra trình độ theo danh sách từ vựng tham chiếu (ví dụ danh mục từ vựng Cambridge theo cấp độ) ở mức **cảnh báo**, không chặn cứng — vì phân loại trình độ của một câu chỉ mang tính tương đối.
- Admin quản lý danh mục trình độ và ánh xạ gợi ý khối lớp → trình độ.

### 7.5 Chọn dạng bài bằng checklist

Bên cạnh việc chỉnh block trực tiếp, giáo viên chọn dạng bài bằng danh sách tick khi cấu hình đề:

- Danh sách hiển thị các dạng bài đã xuất bản trong thư viện (matching, điền vào chỗ trống, trắc nghiệm, phát âm...).
- Tick dạng nào, đề chỉ chứa các block thuộc dạng đó; block của template thuộc dạng không được tick sẽ bị loại và hệ thống báo rõ.
- Tick thêm dạng chưa có trong template sẽ tạo block mới với cấu hình mặc định của dạng bài, giáo viên chỉnh tiếp số câu/điểm.
- Checklist là cách nhập nhanh; kết quả cuối cùng vẫn là danh sách block, nên toàn bộ cơ chế sinh, kiểm duyệt và xuất không thay đổi.

### 7.6 Độ dài nội dung theo khối lớp

**a) Độ dài câu hỏi (trắc nghiệm, word form):**

| Cấp học | Số từ mỗi câu |
|---|---|
| Secondary (THCS) | 12–14 từ — giáo viên đã chốt |
| Primary (Tiểu học) | 6–10 từ — đề xuất, chờ xác nhận |
| High school (THPT) | 14–18 từ — đề xuất, chờ xác nhận |

Yêu cầu chất lượng đi kèm (bắt buộc trong prompt sinh): mỗi câu phải **đủ ngữ cảnh** và chứa **dấu hiệu nhận biết** để xác định đáp án — ví dụ câu chia thì phải có trạng từ/mốc thời gian ("last month", "at the moment", "since 2020"), câu từ vựng phải có ngữ cảnh gợi nghĩa. Không chấp nhận câu cụt kiểu "She ______ to school." vì thiếu căn cứ chọn đáp án. Validation đếm số từ và cảnh báo khi lệch khoảng; tiêu chí "đủ dấu hiệu nhận biết" do giáo viên thẩm định khi duyệt (có thể hỗ trợ bằng heuristic danh sách dấu hiệu theo thì).

**b) Độ dài bài đọc:**

Các dạng bài có đoạn văn (đọc hiểu True/False, cloze test...) dùng độ dài bài đọc phù hợp với khối lớp. Bảng số từ gợi ý mặc định:

| Khối lớp | Số từ bài đọc (gợi ý) |
|---|---|
| Lớp 1–2 | 20–40 từ |
| Lớp 3–5 | 40–80 từ |
| Lớp 6–7 | 80–150 từ |
| Lớp 8–9 | 150–250 từ |
| Lớp 10–12 | 250–350 từ |

Nguyên tắc áp dụng:

- Khoảng số từ được đưa vào prompt sinh; giáo viên chỉnh được số từ mục tiêu theo từng block.
- Validation đếm số từ đoạn văn sinh ra; lệch khỏi khoảng cấu hình thì cảnh báo, không chặn.
- Bảng mặc định do Admin quản lý, chỉnh theo thực tế giảng dạy.

## 8. Luồng tạo và kiểm duyệt đề

1. Giáo viên chọn lớp, sách, Unit/chủ đề, phạm vi kiến thức và trình độ mục tiêu.
2. Chọn template chuẩn và tạo bản sao.
3. Tick các dạng bài muốn có; hệ thống giữ/dựng block theo dạng đã tick (xem 7.5).
4. Thêm/xóa/sắp xếp block; đặt số câu, điểm và độ khó.
5. Thiết lập ma trận tùy chọn hoặc dùng mặc định của template.
6. Nhập yêu cầu bổ sung bằng ngôn ngữ tự nhiên.
7. Hệ thống kiểm tra cấu hình trước khi gọi AI.
8. RAG tìm và rerank các nguồn liên quan.
9. AI sinh từng block theo JSON schema.
10. Validation Engine kiểm tra và đánh dấu cảnh báo/lỗi.
11. Giáo viên sửa, khóa hoặc sinh lại từng câu/khối.
12. Đề chuyển trạng thái: Nháp → Đã kiểm duyệt → Sẵn sàng xuất.

100% câu trong bản xuất phải được giáo viên duyệt. Sinh lại không được thay đổi câu đã khóa.

## 9. Thiết kế RAG và rerank

Pipeline đề xuất:

**Metadata filter → Hybrid search → Rerank → Context selection → Structured generation → Validation**

### 9.1 Metadata filter

Lọc trước theo khối lớp, bộ sách, phiên bản, Unit/chủ đề, loại kiến thức và trạng thái xuất bản. Đây là lớp bảo vệ chính để tránh trộn kiến thức.

### 9.2 Hybrid search

Kết hợp vector search và keyword/full-text search. Vector search tìm tương đồng ngữ nghĩa; keyword search giữ độ chính xác cho tên Unit, từ vựng và cấu trúc ngữ pháp.

### 9.3 Rerank

Reranker xếp hạng lại khoảng 20–30 đoạn ứng viên và chọn 5–10 đoạn phù hợp nhất. Thành phần rerank được trừu tượng hóa để có thể thay thế: tắt hẳn khi kho nhỏ, dùng API/model chuyên dụng, local cross-encoder hoặc LLM rerank dự phòng. Admin cấu hình số ứng viên đầu vào/đầu ra.

### 9.4 Nguyên tắc nguồn

- AI chỉ nhận các đoạn đã qua lọc và rerank.
- Mỗi câu lưu ID đoạn nguồn đã sử dụng.
- Khi nguồn không đủ, hệ thống cảnh báo; không âm thầm sinh ngoài phạm vi.
- Tài liệu đã dùng trong đề cũ không bị xóa cứng; dùng version và trạng thái ngừng sử dụng.

## 10. Thiết kế AI

Hệ thống dùng interface AI Provider chung. MVP kết nối API trước; local LLM được bổ sung bằng adapter sau này. Admin chọn provider/model và quản lý API key tại backend.

LLM phải trả JSON theo schema của dạng bài, tối thiểu gồm:

- Nội dung câu hỏi và lựa chọn/ô trả lời.
- Đáp án đúng và lời giải.
- Kiến thức mục tiêu, độ khó và trình độ mục tiêu (CEFR/Cambridge).
- ID nguồn RAG.
- Cảnh báo/giả định khi nguồn chưa đủ.

Mỗi lần sinh lưu provider, model, prompt version, tham số, thời gian, token/chi phí và nguồn. API key được mã hóa, che trên giao diện và không ghi vào log.

## 11. Validation Engine

Các kiểm tra bắt buộc:

- JSON đúng schema và đủ trường.
- Đáp án hợp lệ và nằm trong các lựa chọn khi áp dụng.
- Không có lựa chọn trùng nhau.
- Số câu và tổng điểm khớp cấu hình.
- Có nguồn RAG và không vượt phạm vi lớp/Unit.
- Câu không trùng hoặc gần giống ngân hàng: đo bằng tương đồng embedding kết hợp so khớp chuỗi mờ (fuzzy match); ngưỡng mặc định 0.90 tương đồng cosine, Admin điều chỉnh được. Câu vượt ngưỡng bị đánh dấu cảnh báo kèm liên kết tới câu tương tự.
- Ma trận thực tế không lệch quá ngưỡng cấu hình so với ma trận đã đặt; mặc định cho phép lệch ±10% số câu trên mỗi ô (làm tròn lên tối thiểu 1 câu), Admin điều chỉnh được.
- Đáp án dạng phát âm/trọng âm được kiểm chứng bằng từ điển phát âm (xem 7.3).
- Từ vựng/cấu trúc vượt trình độ mục tiêu: cảnh báo theo danh sách từ vựng tham chiếu, không chặn cứng (xem 7.4).
- Số từ của câu hỏi và bài đọc nằm trong khoảng cấu hình theo khối lớp (xem 7.6); lệch thì cảnh báo.
- Đề chỉ chứa block thuộc các dạng bài đã tick.
- Cụm đọc hiểu/hình ảnh có quan hệ cha–con hợp lệ.

Lỗi format nhẹ có thể tự sửa một lần. Lỗi kiến thức hoặc thiếu nguồn phải chuyển cho giáo viên, không tự phê duyệt.

## 12. Ngân hàng câu hỏi và versioning

Chỉ câu đã được giáo viên duyệt mới vào ngân hàng. Mỗi câu lưu nội dung, đáp án, lời giải, kiến thức, độ khó, nguồn, người duyệt và lịch sử sửa.

Đề lưu snapshot của template, block và câu hỏi tại thời điểm tạo. Việc sửa câu trong ngân hàng, cập nhật template hoặc thay tài liệu không làm thay đổi đề cũ. Dữ liệu có lịch sử sử dụng ưu tiên xóa mềm/ngừng sử dụng.

## 13. Mã đề

- Tạo mã A/B/C/D từ một đề gốc đã duyệt.
- Đảo câu trong phạm vi được phép và đảo lựa chọn.
- Không tách đoạn đọc, hình ảnh hoặc nhóm câu dùng chung ngữ cảnh.
- Lưu seed và ánh xạ thứ tự để tái tạo chính xác.
- Sinh đáp án riêng tương ứng cho từng mã.
- MVP không sinh nội dung khác nhau giữa các mã.

## 14. Xuất DOCX

DOCX được dựng từ dữ liệu đề đã duyệt, không dùng trực tiếp văn bản thô của LLM.

- Khổ A4, mặc định hướng dọc.
- Font, cỡ chữ, lề và khoảng cách do template kiểm soát. Định dạng chuẩn do giáo viên chốt:
  - Font Times New Roman; tiêu đề đề (UNIT...) in hoa cỡ 14; nội dung bài tập cỡ 11.5.
  - Lề Narrow 1,27 cm cả bốn phía; giãn dòng 1,15; không thêm khoảng cách trước/sau đoạn.
  - Ký hiệu A./B./C./D. in đậm; các lựa chọn dàn đều bằng tab thành 4 cột; lựa chọn dài thì xuống 2 cột mỗi dòng (A./B. trên, C./D. dưới).
  - Đoạn văn đọc hiểu canh đều hai lề (justify).
- Tự chảy trang, không đặt số trang mục tiêu và không ép số trang.
- Tránh để tiêu đề phần đứng một mình cuối trang.
- Cố gắng giữ câu hỏi và lựa chọn cùng nhau.
- Giữ nguyên cụm đoạn đọc/hình và câu phụ thuộc.
- Hỗ trợ header/footer, tên trường, môn, lớp, thời gian, mã đề, số trang và vùng thông tin học sinh.
- Xuất hai kiểu: (1) chỉ đề, không kèm đáp án — bản phát cho học sinh; (2) đề có đáp án tô đỏ — lựa chọn đúng in đỏ và đậm ngay tại vị trí của nó trong đề (theo mẫu giáo viên: "1. A. puzzles **B. messages** C. puddings D. flowers" với B đỏ), bố cục đề giữ nguyên; dạng tự luận thì điền đáp án màu đỏ vào chỗ trống. Dành cho giáo viên chấm và lưu trữ.
- Nhiều mã đề có thể xuất riêng hoặc đóng gói ZIP.

Word có thể dàn trang khác nhau theo phiên bản, font và hệ điều hành. Hệ thống không cam kết số trang tuyệt đối; giáo viên có thể chỉnh bản tải về.

## 15. Mô hình dữ liệu cốt lõi

Các nhóm entity chính:

- Người dùng: `User`, `Role`, `AuditLog`.
- Học thuật: `Grade`, `SchoolStage` (Primary/Secondary/High school), `BookSeries`, `BookVersion`, `Unit`, `Topic`, `LearningObjective`, `VocabularyItem`, `GrammarPoint`, `ProficiencyLevel` (trục CEFR A1–C1, nhãn Cambridge quy đổi, bảng ánh xạ lớp → trình độ).
- RAG: `KnowledgeDocument`, `DocumentVersion`, `KnowledgeChunk`, `ChunkEmbedding`, `IngestionJob`.
- Dạng bài/template: `ExerciseType`, `ExerciseVariant`, `OutputSchema`, `ValidationRule`, `Template`, `TemplateVersion`, `TemplateSection`, `TemplateBlock`.
- Hình ảnh: `ImageAsset` (file, metadata chủ đề/Unit, trạng thái xuất bản) dùng cho dạng bài có hình.
- Đề: `Exam`, `ExamBlueprint`, `ExamSection`, `ExamBlock`, `Question`, `QuestionOption`, `Answer`, `QuestionSource`, `QuestionRevision`, `QuestionLock`.
- Mã đề/xuất: `ExamVariant`, `VariantQuestionOrder`, `ExportJob`.

## 16. Trạng thái và background jobs

- Tài liệu: Đang xử lý → Chờ duyệt → Đã xuất bản → Ngừng sử dụng/Lỗi.
- Đề: Nháp → Đã kiểm duyệt → Sẵn sàng xuất.
- Tác vụ: Chờ → Đang chạy → Hoàn thành/Hoàn thành một phần/Thất bại.

Nhập tài liệu, embedding, rerank theo lô, sinh đề và xuất DOCX chạy dưới dạng background job. Một block lỗi không làm mất các block đã hoàn thành.

## 17. Xử lý lỗi

- AI API lỗi: retry có giới hạn; cho phép đổi provider/model.
- JSON lỗi: thử sửa một lần rồi báo rõ block thất bại.
- RAG thiếu nguồn: cảnh báo và yêu cầu thay phạm vi/bổ sung tài liệu.
- Trích xuất tài liệu lỗi: không cho xuất bản.
- DOCX lỗi: giữ nguyên đề và cho chạy lại export.
- Mọi lỗi có mã lỗi và log kỹ thuật; không chứa mật khẩu hoặc API key.

## 18. Bảo mật và vận hành

- Băm mật khẩu và kiểm tra phân quyền tại backend.
- Mã hóa API key; che khi hiển thị.
- Kiểm tra loại file, kích thước và nội dung upload.
- Giáo viên không truy cập tài liệu chưa xuất bản hoặc cấu hình hệ thống.
- Audit log cho tài khoản, tài liệu, template và AI config.
- Sao lưu database, file gốc và template.
- Chạy local khi phát triển; đóng gói để triển khai VPS/cloud mà không xây lại.

## 19. Chiến lược kiểm thử

- Unit test cho validation, ma trận, đánh số và đảo đáp án.
- Integration test cho RAG → rerank → AI → validation.
- Contract test cho AI provider và reranker provider.
- Permission test cho Admin/Giáo viên.
- Snapshot/version test để dữ liệu mới không làm đổi đề cũ.
- Render test DOCX và kiểm tra mọi trang.
- Golden test dựa trên đề Global Success 7 – Unit 3.
- User acceptance test với giáo viên và đề thật.

## 20. Tiêu chí nghiệm thu MVP

1. Admin nhập và xuất bản được tài liệu PDF/DOCX/text có metadata.
2. Giáo viên tạo được đề bằng form kết hợp prompt bổ sung.
3. Có thể thay đổi, khóa và sinh lại riêng từng block/câu.
4. Mỗi câu có đáp án, lời giải, kiến thức mục tiêu và nguồn RAG.
5. Ma trận tùy chọn hoạt động; template mặc định được dùng khi không chọn.
6. Chỉ câu đã duyệt được đưa vào ngân hàng.
7. Tạo mã A/B/C/D và đáp án tương ứng chính xác.
8. DOCX mở, chỉnh sửa và in bình thường trong Microsoft Word.
9. Đề cũ không thay đổi sau khi cập nhật template/tài liệu/câu hỏi.
10. Hệ thống có thể chạy local và triển khai VPS bằng cùng kiến trúc.
11. Giáo viên chọn được trình độ (CEFR/Cambridge); mỗi câu sinh ra gắn đúng trình độ mục tiêu.
12. Đề sinh ra chỉ chứa các dạng bài đã tick trong checklist.

## 21. Roadmap

### Giai đoạn 0 — Spike khả thi (trước hoặc song song 1A)

Chất lượng sinh câu hỏi là rủi ro sản phẩm lớn nhất, nên phải được kiểm chứng trước khi đầu tư xây nền móng đầy đủ. Spike ngắn (1–2 tuần) sinh thử bằng prompt thuần, không cần hệ thống:

- Chọn 2–3 dạng bài khó nhất: phát âm, trọng âm và đọc hiểu có hình.
- Dùng nội dung thật của Global Success 7 – Unit 3 làm nguồn kiến thức.
- Đo tỷ lệ câu đạt yêu cầu theo đánh giá của giáo viên.

Kết quả spike quyết định: dạng nào giữ trong MVP, dạng nào cần lớp kiểm chứng bổ sung (từ điển phát âm, thư viện hình) và dạng nào lùi sang giai đoạn sau.

### Giai đoạn 1A — Nền móng

Tài khoản, phân quyền, danh mục học thuật, nhập tài liệu, RAG/hybrid search, interface reranker và AI provider abstraction.

### Giai đoạn 1B — MVP tạo đề

Thư viện dạng bài, template builder, exam generator/editor, validation, ngân hàng câu hỏi và DOCX renderer.

### Giai đoạn 1C — Hoàn thiện

Mã đề, audit, hạn mức/chi phí, golden tests, thử nghiệm giáo viên, đóng gói local và triển khai VPS.

### Giai đoạn 2

Tài khoản học sinh, lớp học, giao bài, làm bài/chấm điểm online và thống kê.

### Giai đoạn 3

Mobile app, local LLM hoàn chỉnh, OCR, quản lý trường/trung tâm và phân tích chất lượng câu hỏi nâng cao.

## 22. Các quyết định kiến trúc dành cho giai đoạn lập kế hoạch

Các lựa chọn công nghệ cụ thể (backend, frontend, database, vector database, queue, provider AI và thư viện DOCX) chưa bị khóa trong tài liệu ý tưởng. Kế hoạch triển khai tiếp theo phải đánh giá chúng theo các tiêu chí: dễ chạy local, dễ đóng gói, phù hợp nhóm người dùng nhỏ, khả năng mở rộng, độ ổn định của DOCX và chi phí vận hành.

### 22.1 Nguyên tắc hạ tầng tối thiểu

Hệ thống phục vụ 1 Admin và 1–3 giáo viên. Kiến trúc mô-đun ở mục 6 mô tả ranh giới trách nhiệm, không phải yêu cầu về hạ tầng. Khi lập kế hoạch, mặc định chọn phương án đơn giản nhất đáp ứng được quy mô này và chỉ nâng cấp khi có nhu cầu thực tế:

- Background job dùng bảng job trong database chính; chưa cần message queue riêng.
- Vector search ưu tiên tiện ích trong database chính (ví dụ extension vector) trước khi cân nhắc vector database độc lập.
- Audit log là bảng ghi sự kiện đơn giản; chưa cần hệ thống log tập trung.
- Một tiến trình ứng dụng duy nhất là đủ; không tách microservice.

Ranh giới mô-đun được giữ ở tầng code (interface, package) để việc nâng cấp hạ tầng sau này không phải viết lại lõi.

## 23. Hiện trạng dự án, prototype và nhật ký quyết định

### 23.1 Hiện trạng và cấu trúc repo

Dự án đã bắt đầu triển khai: skeleton Giai đoạn 1A xong (nhánh `feat/1a-skeleton`), lõi tạo đề Giai đoạn 1B chạy trên `MockAIProvider` đã dựng và kiểm chứng chạy được trên nhánh `feat/1b-exam-core` (chưa gồm RAG/nhập tài liệu — cố ý để sau, xem quyết định #15). Tên làm việc: **ExamCraft AI**.

| Đường dẫn | Nội dung |
|---|---|
| `docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md` | Đặc tả sản phẩm (tài liệu này) — nguồn chân lý về yêu cầu |
| `docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.docx` | Bản DOCX sinh tự động từ file markdown |
| `docs/engineering/IMPLEMENTATION_NOTES.vi.md` | Ghi chú kỹ thuật cho đội code: dữ liệu seed, thông số DOCX renderer, đặc tả hành vi UI |
| `docs/engineering/DEVELOPMENT_PLAN.vi.md` | Kế hoạch phát triển đã chốt: stack, lộ trình 1A→1D, rủi ro, việc chờ xác nhận |
| `prototype/index.html`, `prototype/styles.css` | Prototype giao diện tương tác — reference implementation |
| `backend/` | FastAPI + SQLAlchemy + Alembic; auth, danh mục học thuật đã seed, `AIProvider`/`MockAIProvider`, Validation Engine, API đề thi đầy đủ (block, sinh câu, duyệt, mã đề, xuất DOCX), API Admin quản lý tài khoản giáo viên, 33 test pytest |
| `frontend/` | Vite + React + TypeScript strict + react-router; đăng nhập, Đề của tôi, Tạo đề, Duyệt câu hỏi, Xuất DOCX, Quản lý tài khoản (Admin) — nối API thật, điều hướng theo vai trò |
| `docker-compose.yml`, `.env.example` | Chạy toàn bộ stack: `docker compose up` (cần Docker + `.env` sao chép từ `.env.example`) |
| `tools/build_project_idea_docx.py` | Script build DOCX (`python tools/build_project_idea_docx.py`, cần `python-docx`) |

Quy trình cập nhật tài liệu: sửa file markdown → chạy script build → DOCX tự đồng bộ. Không sửa tay file DOCX.

### 23.2 Prototype — phạm vi đã demo

Mở trực tiếp `prototype/index.html` bằng trình duyệt, không cần server; HTML/CSS/JS thuần, không thư viện ngoài. Prototype mô phỏng màn hình bước 2 (Cấu trúc đề) của giáo viên và màn hình tổng quan Admin, với các tính năng hoạt động thật:

1. Chuyển vai trò Giáo viên/Admin; mỗi vai trò có menu và màn hình riêng.
2. Khối lớp 1–12 nhóm theo cấp học; đổi lớp tự gợi ý trình độ.
3. Nguồn kiến thức 3 mục: Global Success (Unit theo từng lớp, tên thật cho lớp 6–12; lớp 1–5 tạm theo số) · Kiến thức chung (Tense, Cấu trúc câu) · Cambridge (Starters/Movers/Flyers/KET/PET).
4. Trình độ trục CEFR A1–C1; chọn chứng chỉ Cambridge tự gợi ý CEFR.
5. Chọn thì: 12 thì chia 3 nhóm, nút chọn cả nhóm, vượt trình độ đánh dấu cam nhưng không chặn.
6. Chọn cấu trúc câu: 20 cấu trúc chia 3 nhóm theo cấp học, cùng cơ chế cảnh báo.
7. Checklist 10 dạng bài đồng bộ hai chiều với danh sách block.
8. Dialog chỉnh từng phần: tiêu đề, hướng dẫn, độ khó, số câu, điểm, trình độ ghi đè, quy tắc đảo, prompt riêng; dạng bài chỉ-đọc.
9. Kéo thả sắp xếp block, số La Mã tự đánh lại.
10. Xem trước A4 động: section, hướng dẫn theo dạng bài, số câu tính dồn, ước tính số trang.
11. Thống kê số câu / tổng điểm / số khối tự tính.
12. Bước 3 — Duyệt câu hỏi (6 câu mẫu/30): mỗi câu có đáp án, lời giải, kiến thức mục tiêu, trình độ, nguồn RAG; cảnh báo trùng ngân hàng và vượt trình độ; hành động Duyệt / Sinh lại / Khóa (khóa chặn sinh lại, câu 6 demo sinh lại đổi nội dung thật); đủ 100% câu duyệt mới mở được bước 4.
13. Bước 4 — cấu hình xuất: chọn kiểu (chỉ đề / đề có đáp án tô đỏ), số mã đề A/B/C/D, rồi **lưu vào "Đề của tôi"**; việc tải file DOCX thực hiện từ danh sách "Đề của tôi" (chỉ đề Sẵn sàng xuất mới tải được). Prototype tạo file DOCX thật ngay trên trình duyệt từ 6 câu mẫu.

Giới hạn chủ đích: chưa có màn hình bước 1 tách riêng (chọn nguồn đang gộp trong bước 2), các màn Admin con, và nút tải DOCX chỉ mô phỏng. Công tắc vai trò chỉ để xem thử; sản phẩm thật phân quyền theo tài khoản tại backend (mục 18).

### 23.3 Nhật ký quyết định đã chốt với giáo viên (18/07/2026)

| # | Quyết định |
|---|---|
| 1 | CEFR A1–C1 là trục chuẩn lưu dữ liệu; Cambridge là nhãn quy đổi |
| 2 | Quy đổi theo giáo viên: Starters/Movers ≈ A1, Flyers ≈ A2, KET ≈ B1, PET ≈ B2 (cao hơn chuẩn Cambridge chính thức một bậc; là mặc định, Admin chỉnh được) |
| 3 | Ánh xạ lớp → trình độ: 1–5: A1→A2 · 6–7: A2 · 8–9: A2–B1 · 10–12: B1+/B2, C1 nâng cao |
| 4 | Kiến thức chia theo cấp học Primary/Secondary/High school |
| 5 | Kho kiến thức 3 mục: Kiến thức chung (Tense 12 thì, Các dạng cấu trúc câu) · Global Success · Cambridge theo chứng chỉ |
| 6 | Chỉ dùng bộ sách Global Success; danh mục Unit mỗi lớp do Admin nhập, không gán cứng |
| 7 | Chọn dạng bài bằng checklist — tick dạng nào đề ra dạng đó |
| 8 | Chọn từng thì/cấu trúc bằng lưới tick nhóm; vượt trình độ chỉ cảnh báo |
| 9 | Bộ 20 cấu trúc câu khởi đầu chia 3 nhóm (mục 7.4) |
| 10 | Dạng bài của block không chỉnh trong dialog; checklist là nguồn chỉnh sửa duy nhất |
| 11 | Xuất DOCX hai kiểu: chỉ đề (bản học sinh) · đề có đáp án tô đỏ tại từng câu (bản giáo viên) |
| 12 | Định dạng DOCX: Times New Roman; tiêu đề in hoa 14, nội dung 11.5; lề Narrow 1,27 cm; giãn dòng 1,15; không space trước/sau đoạn; A./B./C./D. in đậm, dàn tab 4 cột (dài thì 2 cột); bài đọc justify |
| 13 | Độ dài bài đọc theo khối lớp (bảng số từ ở mục 7.6); giáo viên chỉnh theo block, lệch chỉ cảnh báo |
| 14 | Câu trắc nghiệm/word form cấp 2 dài 12–14 từ; mỗi câu phải đủ ngữ cảnh và dấu hiệu nhận biết đáp án |
| 15 | Tích hợp LLM/API key làm sau cùng (giai đoạn 1D), sau khi UI + BE + FE hoàn tất; phát triển trên MockAIProvider với fixture từ đề Unit 3 |
| 16 | Duyệt/khóa câu dùng PATCH tường minh, không dùng toggle (an toàn khi mất mạng/double-click); trùng lặp dùng fuzzy text-match tạm thời, cosine embedding chờ RAG |
| 17 | Admin quản lý tài khoản giáo viên: tạo, khóa/mở lại (không xóa cứng), đặt lại mật khẩu; chỉ áp dụng cho vai trò teacher, không dùng để quản trị tài khoản admin khác |

### 23.4 Việc tiếp theo

Kế hoạch phát triển đầy đủ (stack đã chốt, lộ trình 1A → 1D, rủi ro, việc chờ xác nhận) nằm tại `docs/engineering/DEVELOPMENT_PLAN.vi.md`. Theo quyết định chủ dự án, tích hợp LLM/API key thực hiện **sau cùng** (giai đoạn 1D); toàn bộ UI/BE/FE xây trước trên `MockAIProvider` với fixture từ đề Unit 3 thật.

Giai đoạn 1A xong phần nền: FastAPI + Postgres (pgvector) + Alembic migration + seed toàn bộ danh mục đã chốt (trình độ, ánh xạ lớp, 12 thì, 20 cấu trúc câu, 78 Unit lớp 6–12, 10 dạng bài, quy tắc độ dài), auth session/bcrypt phân quyền Admin/Giáo viên.

Giai đoạn 1B xong lõi tạo đề chạy trên `MockAIProvider`: model Exam/ExamBlock/Question/ExamVariant, Validation Engine (đếm từ, cảnh báo trình độ, trùng lặp fuzzy-match), API đầy đủ từ tạo đề đến xuất DOCX, mã đề A/B/C/D, và 4 trang frontend (Đề của tôi, Tạo đề, Duyệt câu hỏi, Xuất) nối API thật — không còn dữ liệu giả ở tầng UI. Đã kiểm chứng bằng 25 test pytest và luồng thật qua Docker Compose (tạo đề Unit 3 → sinh câu → duyệt → xuất DOCX, mở lại bằng python-docx). Toàn bộ chạy qua `docker compose up` (migration + seed tự động, idempotent).

Admin quản lý tài khoản giáo viên (tạo, khóa/mở lại, đặt lại mật khẩu) đã có API + trang thật, kèm điều hướng phân theo vai trò ở frontend (Admin thấy thêm mục "Quản lý tài khoản", Giáo viên không thấy).

Còn thiếu để hoàn tất 1A+1B+1C theo kế hoạch gốc: nhập tài liệu PDF/DOCX/text → trích xuất → full-text search (RAG, cố ý để sau — quyết định #15); màn hình Admin quản lý kho kiến thức/dạng bài/thư viện hình ảnh/cấu hình AI (mới làm phần tài khoản giáo viên, các khối quản trị khác trong prototype vẫn chỉ là ảnh tĩnh minh họa); số hóa fixture bank từ đề Unit 3 thật thành golden test tự động; kéo-thả thật và xem trước A4 động ở frontend (hiện dùng nút lên/xuống, chưa có preview); từ điển phát âm CMU và marker-heuristic theo thì; audit log. Bước kế tiếp: hoàn thiện các phần còn thiếu của 1A/1C hoặc **Giai đoạn 1D — tích hợp LLM thật** khi có API key.


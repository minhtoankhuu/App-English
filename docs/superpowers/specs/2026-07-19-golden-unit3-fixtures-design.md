# Thiết kế mở rộng fixture bank vàng Unit 3 (đủ 10 dạng bài)

## Mục tiêu

Hoàn thành mục còn lại của Giai đoạn 1A: "Fixture bank: số hóa đề Global Success 7 – Unit 3 thành JSON đúng schema". Hiện `GOLDEN_UNIT3_QUESTIONS` (`backend/app/services/fixtures.py`) mới có 4/10 dạng bài (pronunciation, multiple_choice, reading_true_false, sentence_rewrite) — 6 dạng còn lại (stress, matching, gap_fill, cloze_test, sign_reading, word_form) khi sinh đề cho Global Success 7 Unit 3 đang rơi vào `GENERIC_TEMPLATES` (nội dung hợp lý về chủ đề nhưng không được xác nhận là số hóa từ nguồn thật).

Nhánh `feat/1a-knowledge-base-global-success` vừa nhập xong từ vựng/word form/ngữ pháp thật của Unit 3 vào `knowledge_chunks` — dùng chính dữ liệu đó (word/ipa/pos/meaning có kiểm chứng qua parser + golden test) làm nguồn soạn 6 mục còn thiếu, thay vì tự bịa nội dung.

## Nguồn dữ liệu dùng

Từ `knowledge_chunks` của Unit 3 (Global Success 7, đã nhập ở nhánh trước), chỉ dùng các mục đã parse `structured` thành công (không bịa nghĩa/IPA):

- Trọng âm: `active /ˈæktɪv/`, `future /ˈfjuːtʃər/`, `problems /ˈprɑːbləmz/` (stress âm tiết 1) và `collect /kəˈlekt/` (stress âm tiết 2).
- Matching: `volunteer`, `donate`, `elderly`, `charity` (nghĩa tiếng Anh tự viết ngắn gọn dựa trên nghĩa tiếng Việt đã có, không phải trích nguyên văn — sách không có định nghĩa tiếng Anh sẵn).
- Gap fill: `donate` (nghĩa: quyên góp).
- Cloze test: cụm `community service` cộng các từ `elderly`, `donate`, `needy`, `rubbish`.
- Sign reading: không có thư viện hình ảnh (PRD 7 — chờ RAG), giữ dạng mô tả biển báo bằng văn bản như template cũ, nhưng đổi ngữ cảnh sang "donation box" để không trùng lặp với ví dụ generic.
- Word form: cặp `decide (v) → decision (n)` từ section WORD FORM thật của Unit 3.

## Thay đổi

- `backend/app/services/fixtures.py`: thêm 6 khóa mới vào `GOLDEN_UNIT3_QUESTIONS` (`stress`, `matching`, `gap_fill`, `cloze_test`, `sign_reading`, `word_form`), mỗi khóa 1 câu, theo đúng field schema hiện có của từng dạng (so với `GENERIC_TEMPLATES` cùng dạng bài).
- Không đổi `GENERIC_TEMPLATES`, không đổi `AIProvider`/`MockAIProvider`, không thêm dạng bài mới, không đổi schema `QuestionDraft`.

## Test

- `backend/tests/test_fixtures.py` (mới): với `context.grade_number=7, unit_order_no=3`, `MockAIProvider()._pool(block, context)` cho từng dạng trong 6 dạng mới phải trả **golden trước generic** (golden ở đầu list) — dùng để phát hiện hồi quy nếu sau này ai đó sửa nhầm thứ tự nối `golden + generic`.
- Với context khác Unit 3 (vd `unit_order_no=5`), pool của 6 dạng đó phải **không chứa** nội dung golden (chỉ generic) — xác nhận golden chỉ áp dụng đúng ngữ cảnh.
- Test tích hợp: mở rộng `test_full_golden_flow_create_generate_review_export` không bắt buộc (đã đủ chặt với 4 dạng cũ); thêm 1 test API riêng sinh đề Unit 3 với block `word_form` và `matching`, assert `answer_text` đúng nội dung vàng mới (không phải nội dung generic).

## Không thuộc phạm vi

- Không đổi golden 4 dạng đã có.
- Không thêm dạng bài thứ 11.
- Không làm thư viện hình ảnh thật cho sign_reading (vẫn mô tả bằng văn bản, đã ghi rõ trong PRD là chờ RAG).
- Không tự động sinh fixture từ `knowledge_chunks` bằng code — vẫn viết tay thủ công (fixture bank theo đúng cách 1B đã làm), chỉ *tham chiếu* dữ liệu thật khi soạn.

## Tiêu chí hoàn thành

- `GOLDEN_UNIT3_QUESTIONS` có đủ 10 khóa khớp 10 `exercise_types` đã seed.
- Toàn bộ nội dung mới (từ vựng/word form) khớp với dữ liệu thật trong `Knowledge_Base/Global Success/G7/GS7 - UNIT 3 - LESSON.docx`.
- Test mới pass; toàn bộ pytest backend hiện có vẫn pass.

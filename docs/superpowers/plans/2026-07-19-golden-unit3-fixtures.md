# Golden Unit 3 Fixtures Implementation Plan

**Goal:** Mở rộng `GOLDEN_UNIT3_QUESTIONS` từ 4/10 lên đủ 10/10 dạng bài, dùng dữ liệu thật đã nhập trong `knowledge_chunks` cho Unit 3 Global Success 7 — hoàn thành mục "Fixture bank" còn lại của Giai đoạn 1A.

**Architecture:** Thêm dữ liệu tĩnh vào `GOLDEN_UNIT3_QUESTIONS` (dict trong `fixtures.py`), không đổi logic `MockAIProvider._pool()` (đã ưu tiên golden trước generic khi `grade_number==7 and unit_order_no==3`).

**Tech Stack:** Python, pytest.

## Global Constraints

- Không đổi 4 dạng golden đã có, không đổi `GENERIC_TEMPLATES`.
- Không đổi `AIProvider` interface hay `QuestionDraft` schema.
- Nội dung mới phải bám từ vựng/word form thật của Unit 3 (đối chiếu `Knowledge_Base/Global Success/G7/GS7 - UNIT 3 - LESSON.docx`), không bịa từ ngoài Unit.
- Commit `doc: ...` rồi `feat: ...`, branch `feat/1a-golden-unit3-fixtures`.

---

### Task 0: Đặc tả và kế hoạch

- [x] Viết spec + plan.
- [ ] Commit: `doc: đặc tả mở rộng fixture bank vàng Unit 3`

### Task 1: Thêm 6 câu vàng còn thiếu

**Files:**
- Modify: `backend/app/services/fixtures.py`

- [ ] **Step 1:** Thêm khóa `stress` vào `GOLDEN_UNIT3_QUESTIONS`: 4 từ thật (`active`, `future`, `collect`, `problems`), đáp án `collect` (trọng âm âm tiết 2, 3 từ còn lại âm tiết 1).
- [ ] **Step 2:** Thêm khóa `matching`: 4 cặp từ-nghĩa thật (`volunteer`, `donate`, `elderly`, `charity`) với định nghĩa tiếng Anh ngắn.
- [ ] **Step 3:** Thêm khóa `gap_fill`: câu điền từ dùng `donate`.
- [ ] **Step 4:** Thêm khóa `cloze_test`: đoạn văn chủ đề community service dùng cụm `community service`, `elderly`, `donate`, `rubbish`, 1 câu hỏi cho blank 1 (đáp án `community`).
- [ ] **Step 5:** Thêm khóa `sign_reading`: biển báo "donation box" (khác nội dung với ví dụ trong `GENERIC_TEMPLATES` để không trùng).
- [ ] **Step 6:** Thêm khóa `word_form`: câu dùng cặp `decide → decision` từ Word Form thật của Unit 3.

### Task 2: Test hồi quy cho pool vàng/chung

**Files:**
- Add: `backend/tests/test_fixtures.py`

- [ ] **Step 1:** Viết test RED: với `GenerationContext(grade_number=7, unit_order_no=3, ...)`, với từng dạng trong 10 dạng, `MockAIProvider()._pool(block, context)[0]` phải là template vàng (so khớp `prompt_text` với `GOLDEN_UNIT3_QUESTIONS[code][0]["prompt_text"]`).
- [ ] **Step 2:** Viết test: với context khác (`unit_order_no=5`), pool của 6 dạng mới không chứa bất kỳ `prompt_text` nào trùng với golden Unit 3 (chỉ generic).
- [ ] **Step 3:** Chạy test — GREEN sau khi Task 1 xong.
- [ ] **Step 4:** Chạy toàn bộ `pytest backend/tests -q`.
- [ ] **Step 5:** Commit: `feat: bổ sung fixture vàng đủ 10 dạng bài cho Unit 3`

### Task 3: Cập nhật tài liệu tiến độ

**Files:**
- Modify: `docs/engineering/DEVELOPMENT_PLAN.vi.md`

- [ ] **Step 1:** Tick mục "Fixture bank" ở Giai đoạn 1A, ghi rõ đã đủ 10/10 dạng, tham chiếu dữ liệu thật từ `knowledge_chunks`.
- [ ] **Step 2:** Commit: `doc: cập nhật tiến độ fixture bank vàng Unit 3`

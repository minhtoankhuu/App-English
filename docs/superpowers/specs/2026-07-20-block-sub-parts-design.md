# Đặc tả phần con (sub-part) trong block đề thi

## Bối cảnh

Chủ dự án gửi mẫu đề thật "GS Unit 2 Revision Exercises" (Global Success 9, cấp 2). Mẫu cho thấy một mục La Mã (I, II, III...) của đề thật thường không phải một danh sách câu phẳng, mà chia thành nhiều phần con đánh số Ả Rập, mỗi phần một chủ đề/mẫu câu riêng, ví dụ:

- `I. PRONUNCIATION` → `1.` âm đuôi -ed/-s, `2.` trọng âm 2 âm tiết, `3.` trọng âm 3+ âm tiết.
- `IV. TRANSFORMATION PATTERNS` → `1.` so sánh kép, `2.` so sánh hơn/kém/nhất, `3.` cụm động từ.

Model hiện tại (`ExamBlock` → `Question` phẳng, xem `backend/app/models/exam.py`) không có khái niệm này: một block chỉ có một `instruction`, một `question_count`, một `prompt_override` áp dụng cho toàn bộ câu hỏi trong block. Quyết định: thêm cấu trúc dữ liệu **phần con** ngay bây giờ (không lùi sang Giai đoạn 1D), vì đây là thay đổi model/API độc lập với việc có LLM thật hay không — `MockAIProvider` vẫn sinh được câu hỏi theo từng phần con bằng cách gọi `generate()` nhiều lần với `question_count` nhỏ hơn.

## Nguyên tắc thiết kế

1. **Tương thích ngược tuyệt đối.** Một block không có phần con nào hoạt động y hệt hiện tại — không đổi hành vi của các đề đã tạo trước đây, không cần migrate dữ liệu cũ.
2. **Phần con là tuỳ chọn, không bắt buộc.** Đa số dạng bài (trắc nghiệm, gap-fill...) không cần chia phần con; chỉ dùng khi giáo viên chủ động thêm.
3. **Không tách exercise_type/points/difficulty ra phần con.** Mọi phần con trong 1 block dùng chung dạng bài, điểm và độ khó của block cha — khớp đúng mẫu thật (`IV. TRANSFORMATION PATTERNS` toàn bộ vẫn là `sentence_rewrite`). Phần con chỉ khác nhau ở tiêu đề, hướng dẫn, số câu và prompt bổ sung (để định hướng AI sinh đúng mẫu câu của phần đó).
4. **`order_no` của Question vẫn là một dãy chạy liên tục trong toàn block** (không reset theo từng phần con) — giữ nguyên unique constraint `(block_id, order_no)` hiện có, không cần đổi. Việc nhóm theo phần con dựa hoàn toàn vào `part_id` mới trên `Question`, không dựa vào khoảng `order_no`.
5. **`block.question_count` là tổng của các phần con khi block có phần con.** Khi phần con rỗng, trường này vẫn do giáo viên nhập trực tiếp như hiện tại.

## Model dữ liệu

Bảng mới `exam_block_parts`:

```python
class ExamBlockPart(Base):
    __tablename__ = "exam_block_parts"
    __table_args__ = (UniqueConstraint("block_id", "order_no", name="uq_block_part_order"),)

    id: UUID (pk)
    block_id: FK -> exam_blocks.id, not null
    order_no: int, not null          # 1, 2, 3... hiển thị làm số phần con
    title: str(255), not null        # ví dụ "So sánh kép"
    instruction: str | None          # hướng dẫn riêng của phần con, ghi đè phần chung của block khi hiển thị
    question_count: int, not null
    prompt_override: str | None      # ghi đè prompt_override của block khi sinh câu cho riêng phần này

    block = relationship("ExamBlock", back_populates="parts")
    questions = relationship("Question", back_populates="part", cascade="all, delete-orphan")
```

Thay đổi trên model có sẵn:

- `ExamBlock.parts: list[ExamBlockPart]` (`order_by=order_no`, `cascade="all, delete-orphan"`).
- `Question.part_id: UUID | None` (`ForeignKey("exam_block_parts.id")`, nullable — `None` khi block không dùng phần con).
- `Question.part = relationship("ExamBlockPart", back_populates="questions")`.

Xoá một phần con xoá luôn các câu hỏi thuộc phần con đó (cascade), giống hành vi xoá block hiện tại.

## Migration

Một migration Alembic mới (autogenerate sau khi thêm model + đăng ký `app/models/__init__.py`): tạo bảng `exam_block_parts`, thêm cột `part_id` (nullable) vào `questions`. Không cần backfill vì cột mới nullable và không có bảng nào phụ thuộc ngược.

## Schema (Pydantic)

```python
class BlockPartCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    instruction: str | None = None
    question_count: int = Field(ge=1, le=50)
    prompt_override: str | None = None

class BlockPartUpdateRequest(BaseModel):
    # tất cả field trên nhưng Optional, giống BlockUpdateRequest

class BlockPartReorderRequest(BaseModel):
    part_ids: list[uuid.UUID]

class BlockPartOut(BaseModel):
    id, order_no, title, instruction, question_count, prompt_override
```

`BlockOut` thêm `parts: list[BlockPartOut] = []`. `QuestionOut` thêm `part_id: uuid.UUID | None` để trang duyệt câu (`ExamReviewPage`) có thể nhóm câu hỏi theo phần con nếu cần sau này.

## API

Thêm vào `backend/app/routers/exams.py`, cùng nhóm quyền `require_teacher` + kiểm tra sở hữu như block hiện tại:

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/exams/{exam_id}/blocks/{block_id}/parts` | `BlockPartCreateRequest` | `BlockOut` (201) |
| PATCH | `/exams/{exam_id}/blocks/{block_id}/parts/{part_id}` | `BlockPartUpdateRequest` | `BlockOut` |
| DELETE | `/exams/{exam_id}/blocks/{block_id}/parts/{part_id}` | – | `BlockOut` |
| POST | `/exams/{exam_id}/blocks/{block_id}/parts/reorder` | `BlockPartReorderRequest` | `BlockOut` |

Trả về `BlockOut` (không phải `BlockPartOut` đơn lẻ hay `ExamDetailOut`) vì frontend cần thấy ngay `question_count` đã đồng bộ lại của block cha sau mỗi thao tác phần con — tránh phải gọi thêm request refetch riêng.

Sau mỗi create/update/delete phần con, service đồng bộ `block.question_count = sum(p.question_count for p in block.parts)` nếu block có ít nhất 1 phần con. Nếu giáo viên xoá hết phần con, `question_count` giữ nguyên giá trị cuối cùng (không reset về 0) — giáo viên chỉnh tay lại nếu muốn.

`BlockUpdateRequest.question_count` bị bỏ qua (không set) khi block đang có phần con — tránh xung đột hai nguồn sự thật; frontend ẩn ô sửa số câu cấp block khi phần con đang tồn tại và hướng giáo viên sửa số câu trong từng phần con.

## Sinh câu hỏi (generation service)

`generate_block_questions(db, exam, block)`:

- Nếu `block.parts` rỗng: **giữ nguyên 100% code hiện tại** (một `BlockSpec`, một lần gọi `_provider.generate()`, `part_id=None`).
- Nếu có phần con: lặp theo `order_no`, với mỗi phần con dựng `BlockSpec(question_count=part.question_count, prompt_override=part.prompt_override or block.prompt_override, ...)`, gọi `_provider.generate()` riêng cho phần đó, gán `part_id=part.id` cho các `Question` tạo ra. `order_no` vẫn là một bộ đếm chạy xuyên suốt cả block (không reset theo phần con) — xem nguyên tắc thiết kế #4.
- Xoá câu cũ chưa khoá: giữ nguyên logic xoá toàn bộ câu `is_locked=False` của block trước khi sinh lại (không cần lọc theo phần con vì sinh lại toàn block vẫn xoá sạch rồi build lại từ đầu như hiện tại).

`regenerate_question(...)`: nếu câu đang sinh lại có `question.part_id`, dùng `question.part.prompt_override or block.prompt_override` thay vì luôn lấy `block.prompt_override`.

`AIProvider`/`BlockSpec`/`MockAIProvider` **không đổi interface** — phần con chỉ là cách `generation.py` gọi `generate()` nhiều lần với tham số nhỏ hơn, bản thân provider không cần biết khái niệm phần con.

## Xáo trộn mã đề (`shuffle_variant`)

Hiện tại xáo trộn toàn bộ câu trong 1 block như một khối. Khi block có phần con, việc xáo trộn phải **giữ nguyên từng phần con làm nhóm liền mạch** (không trộn lẫn câu phần 1 với phần 2) — đúng tinh thần sư phạm của đề thật. Cách làm: với block có phần con, xáo trộn (nếu `shuffle_questions=True`) trong phạm vi từng phần con theo `order_no` của phần, rồi nối các phần theo đúng thứ tự phần con. Block không có phần con giữ nguyên logic xáo trộn toàn khối như hiện tại.

## DOCX renderer

Trong vòng lặp câu hỏi của mỗi block (`backend/app/services/docx_renderer.py`), theo dõi `part_id` của câu hiện tại so với câu trước; khi đổi phần con, in thêm một dòng tiêu đề phụ `"{part.order_no}. {part.title}"` (in đậm, không roman số) và dòng `instruction` của phần con nếu có, trước khi in câu hỏi đầu tiên của phần đó. Số thứ tự câu hỏi (`question_no`) tiếp tục đếm liên tục qua cả đề như hiện tại — không reset theo phần con (khớp mẫu thật: câu hỏi được đánh số liên tục 1..N toàn đề, còn phần con chỉ là nhãn chủ đề).

## Preview A4 (`exam_preview.py` + `ExamPreview.tsx`)

`PreviewQuestionOut` thêm 3 field tuỳ chọn: `part_number: int | None`, `part_title: str | None`, `part_instruction: str | None` (lấy từ `question.part` nếu có). `_preview_questions` điền các field này. `_question_lines`/`_paginate` cộng thêm dòng ước tính khi phần con đổi (giống cách đang cộng dòng khi `passage_text` đổi) để không tách tiêu đề phần con khỏi câu đầu tiên của phần đó khi ngắt trang.

`ExamPreview.tsx` theo dõi `previousPartNumber` tương tự `previousPassage` hiện có: khi `part_number` đổi và khác `null`, render một dòng tiêu đề phụ trước câu hỏi.

## Frontend

- `frontend/src/types/exam.ts`: thêm `BlockPartOut`, `BlockPartCreateRequest`, `BlockPartUpdateRequest`; `BlockOut.parts: BlockPartOut[]`.
- `frontend/src/types/examPreview.ts`: thêm 3 field ở trên vào `PreviewQuestionOut`.
- `frontend/src/api/exams.ts`: thêm `addBlockPart`, `updateBlockPart`, `deleteBlockPart`, `reorderBlockParts`.
- `frontend/src/pages/ExamBuilderPage.tsx`: trong popup chỉnh sửa block (`Modal size="lg"` đã có), thêm khu vực "Phần con" — danh sách phần con hiện có (tiêu đề, số câu, nút sửa/xoá), nút "+ Thêm phần con" mở form nhỏ (tiêu đề, hướng dẫn, số câu, prompt bổ sung) ngay trong popup. Khi block có ít nhất 1 phần con, ẩn ô "Số câu" cấp block (vì đã tính tự động) và hiện dòng tổng số câu read-only.

## Không làm trong task này

- Không hỗ trợ phần con lồng phần con (mẫu thật có "so sánh" chia 3 nhóm nhỏ hơn 20 câu mỗi nhóm — task này dừng ở 1 cấp phần con, coi nhóm nhỏ hơn là chi tiết nội dung câu hỏi chứ không phải cấu trúc riêng).
- Không đổi UI trang Duyệt câu (`ExamReviewPage`) để nhóm theo phần con — chỉ thêm `part_id` vào `QuestionOut` để làm sẵn cho việc này sau.
- Không xây dựng "template chuẩn A4 theo cấp học" rộng hơn (ví dụ tự động gợi ý cấu trúc phần con theo dạng bài) — đó là việc của Giai đoạn 1D khi có LLM thật để tự phân tích mẫu đề.

## Kiểm thử

Backend pytest: model constraint (`unique(block_id, order_no)` cho part), CRUD part qua router (kèm 404/403 theo exam sở hữu), đồng bộ `question_count` sau create/update/delete part, `generate_block_questions` sinh đúng số câu mỗi phần + gán đúng `part_id`, `regenerate_question` dùng đúng `prompt_override` của phần, `shuffle_variant` không trộn lẫn câu giữa các phần, docx renderer in đúng tiêu đề phần con, `build_preview` trả đúng `part_number`/`part_title` và không tách phần con giữa hai trang.

Frontend Vitest: hiển thị/thêm/sửa/xoá phần con trong popup block, ẩn ô số câu cấp block khi có phần con, `ExamPreview` render tiêu đề phần con đúng vị trí.

Verification cuối: toàn bộ `pytest`, Vitest, `npm run lint`, `npm run build`, chạy thật qua Docker Compose.

## Git workflow

- Branch: `feat/1c-block-subparts` (đã tạo từ `feat/1c-shell-prototype-parity` vì nhánh đó chưa merge vào `main`).
- Commit tài liệu đặc tả: `doc: đặc tả phần con trong block đề thi`.
- Commit backend (model/migration/schema/router/generation/docx/preview): các commit `feat:` riêng theo lớp.
- Commit frontend: `feat: thêm quản lý phần con vào popup chỉnh sửa block`.
- Commit tiến độ: `doc: cập nhật tiến độ phần con trong block`.
- Push branch; không tự merge.

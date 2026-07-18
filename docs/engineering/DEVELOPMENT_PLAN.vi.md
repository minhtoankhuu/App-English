# KẾ HOẠCH PHÁT TRIỂN — HƯỚNG ĐI ĐÃ CHỐT

**Cập nhật:** 19/07/2026. Phạm vi ưu tiên: **cấp 2 (THCS) trước**, các cấp khác bật dần bằng dữ liệu.
Tài liệu liên quan: [PRD](../product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md) · [Implementation Notes](IMPLEMENTATION_NOTES.vi.md) · prototype tham chiếu tại `prototype/`.

## 1. Nguyên tắc chỉ đạo

1. **Quyết định chủ dự án (19/07/2026):** tích hợp LLM/API key làm **sau cùng**, khi UI + BE + FE hoàn tất. Để điều này an toàn, mọi lời gọi AI đi qua interface `AIProvider` ngay từ đầu; trong suốt giai đoạn phát triển dùng `MockAIProvider` trả fixture lấy từ đề Global Success 7 – Unit 3 thật. Đánh đổi được chấp nhận: rủi ro chất lượng sinh phát hiện muộn hơn; bù lại pipeline được thiết kế để thay provider không phải sửa lõi.
2. **Hạ tầng tối thiểu** (PRD 22.1): 1 database, 1 tiến trình, job là bảng trong DB, không microservice/queue riêng.
3. **Giáo viên duyệt 100%** trước khi xuất; mọi cảnh báo là mềm, không chặn.
4. Prototype là **đặc tả hành vi UI** — code thật phải tái hiện đúng, không sáng tạo lại.
5. Mọi quyết định mới → ghi vào docs (nhật ký PRD mục 23.3) rồi mới code.

## 2. Stack đã chốt

| Tầng | Lựa chọn | Lý do chính |
|---|---|---|
| Backend | Python 3.12 + FastAPI | `python-docx` là thư viện DOCX tốt nhất (định dạng giáo viên đã kiểm chứng bằng nó); hệ sinh thái RAG mạnh nhất ở Python |
| Database | PostgreSQL 16 + pgvector | Một DB cho cả dữ liệu, full-text và vector search — đúng nguyên tắc 22.1 |
| ORM / migration | SQLAlchemy + Alembic | Chuẩn phổ biến, dễ tìm tài liệu |
| Frontend | React + Vite + **TypeScript (strict)** | Dữ liệu có cấu trúc sâu → type tĩnh bắt lỗi sớm; port từ prototype |
| Schema dữ liệu AI | Pydantic (backend) + Zod (frontend) | JSON schema dạng bài là hợp đồng cốt lõi; hai đầu validate cùng một đặc tả |
| DOCX renderer | python-docx | Thông số đã chốt ở Implementation Notes mục 2 |
| AI | Interface `AIProvider`; MVP dùng API (Claude/GPT), embedding qua API | PRD mục 10; local LLM là adapter thêm sau |
| Auth | Session cookie + bcrypt, phân quyền tại backend | Đủ cho 1 Admin + 3 giáo viên |
| Đóng gói | Docker Compose (app + postgres) | Chạy local và VPS cùng một cấu hình |

Cấu trúc repo đề xuất: `backend/` (FastAPI), `frontend/` (Vite React TS), giữ `prototype/` và `docs/` như hiện tại.

## 2.1 Quy ước Git

- **Branch:** `<loại>/<mô-tả-ngắn-gạch-ngang>` — ví dụ `feat/1a-skeleton`, `bug/docx-margin`, `doc/update-roadmap`.
- **Commit message:** `<loại>: <mô tả ngắn gọn>` — `feat: ...`, `bug: ...`, `doc: ...`. Không kèm trailer `Co-Authored-By`; lịch sử commit chỉ đứng tên chủ dự án (minhtoankhuu).

## 3. Lộ trình (đã điều chỉnh: LLM tích hợp sau cùng)

### Giai đoạn 1A — Nền móng (tuần 1–3) ⟵ BẮT ĐẦU TẠI ĐÂY

- Skeleton backend/frontend, Docker Compose, CI chạy test.
- Auth + vai trò Admin/Giáo viên.
- Danh mục học thuật + **seed toàn bộ dữ liệu đã duyệt** (trình độ, ánh xạ lớp, 12 thì, 20 cấu trúc, Unit lớp 6–9, 10 dạng bài, bảng độ dài).
- Nhập tài liệu PDF/DOCX/text → trích xuất → chunk + metadata → full-text search trước (hybrid/vector bổ sung ở giai đoạn tích hợp AI vì embedding cũng cần API).
- **Fixture bank:** số hóa đề Global Success 7 – Unit 3 thành JSON đúng schema — vừa là dữ liệu cho `MockAIProvider`, vừa là golden test sau này.
- **Nghiệm thu:** Admin nhập và xuất bản tài liệu Unit 3; tra cứu trả đúng đoạn theo filter lớp/Unit.

### Giai đoạn 1B — Lõi tạo đề trên MockAIProvider (tuần 4–7)

- JSON schema (Pydantic + Zod) cho 5 dạng cấp 2: trắc nghiệm, phát âm, word form, đọc hiểu T/F, viết lại câu.
- Interface `AIProvider` + `MockAIProvider` trả câu hỏi từ fixture bank (có chế độ trộn/nhiễu để test validation).
- Port UI builder từ prototype: cấu hình → checklist dạng bài → chọn thì/cấu trúc → block editor → kéo thả → xem trước A4.
- Pipeline sinh: validate cấu hình → retrieval → AIProvider theo block → Validation Engine (schema, đáp án, từ điển phát âm CMU, đếm từ 12–14, trùng lặp cosine 0.90, ma trận ±10%, marker heuristic).
- Màn duyệt (Duyệt/Sinh lại/Khóa), ngân hàng câu hỏi, "Đề của tôi" + snapshot.
- DOCX renderer python-docx theo đúng bảng thông số; hai kiểu xuất (chỉ đề / đáp án tô đỏ).
- **Nghiệm thu:** tạo trọn một đề Unit 3 từ đầu đến file DOCX in được **hoàn toàn bằng mock**, đối chiếu golden test.

### Giai đoạn 1C — Hoàn thiện không-AI (tuần 8–9)

- Mã đề A/B/C/D (seed + ánh xạ đáp án), audit log, hạn mức.
- Golden test tự động; đóng gói VPS; giáo viên dùng thử toàn luồng trên mock.

### Giai đoạn 1D — Tích hợp LLM thật (tuần 10–11, khi có API key)

- Adapter provider thật (Claude/GPT) cắm vào `AIProvider`; embedding + hybrid search + reranker interface.
- **Spike chất lượng chuyển về đây:** sinh thử 3 dạng khó nhất (phát âm, trọng âm, đọc hiểu) với prompt ràng buộc chuẩn đã chốt; tiêu chí ≥70% câu chấp nhận không sửa. Dạng nào rớt → giữ chạy bằng ngân hàng câu hỏi/mock, lùi sinh tự động của dạng đó.
- Theo dõi token/chi phí; UAT thật với giáo viên.

Ước lượng trên giả định 1 người code với AI hỗ trợ, làm gần như toàn thời gian; nếu bán thời gian thì nhân đôi.

## 4. Rủi ro chính và đối sách

| Rủi ro | Đối sách |
|---|---|
| Chất lượng AI phát hiện muộn (do hoãn LLM về 1D) | Interface `AIProvider` cách ly hoàn toàn; fixture bank chuẩn hóa từ đề thật nên pipeline không đổi khi cắm LLM; spike 1D vẫn giữ tiêu chí ≥70%, dạng rớt chạy tạm bằng ngân hàng câu hỏi |
| AI sinh dạng ngữ âm kém | Validation bằng từ điển phát âm CMU; sẵn sàng lùi dạng này khỏi sinh tự động |
| Trích xuất PDF giáo trình lỗi | Chỉ nhận PDF có text (PRD đã loại OCR); cho phép dán text thủ công làm đường vòng |
| DOCX lệch định dạng giữa máy | Thông số đã kiểm chứng bằng python-docx; golden test render + PRD đã tuyên bố không cam kết số trang |
| Phạm vi phình (thêm cấp 1/3, Cambridge content) | Khóa phạm vi cấp 2; cấp khác chỉ là thêm seed data, không thêm tính năng |

## 5. Đang chờ xác nhận từ giáo viên

1. Danh mục Unit lớp 1–5 (khi mở rộng Primary).
2. Nguồn nội dung mục Cambridge (tài liệu riêng hay tái dùng Global Success).
3. Số từ/câu cho Tiểu học (6–10?) và THPT (14–18?).
4. Bảng số từ bài đọc (hiện là đề xuất của hệ thống).

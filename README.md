# ExamCraft AI — Nền tảng AI tạo đề tiếng Anh

Ứng dụng web cho giáo viên tạo bài tập/đề tiếng Anh bằng AI theo kho kiến thức quản trị (RAG), kiểm duyệt từng câu và xuất DOCX A4. Dự án đang ở **giai đoạn ý tưởng + prototype giao diện**.

## Bắt đầu từ đâu

| Muốn... | Xem |
|---|---|
| Đọc đặc tả sản phẩm đầy đủ (v1.3) | [docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md](docs/product/ENGLISH_EXAM_AI_PRODUCT_REQUIREMENTS.vi.md) |
| Hiện trạng, prototype và nhật ký quyết định | Mục 23 của đặc tả trên |
| Bắt tay vào code: seed data, thông số DOCX, hành vi UI | [docs/engineering/IMPLEMENTATION_NOTES.vi.md](docs/engineering/IMPLEMENTATION_NOTES.vi.md) |
| Hướng đi và lộ trình phát triển đã chốt | [docs/engineering/DEVELOPMENT_PLAN.vi.md](docs/engineering/DEVELOPMENT_PLAN.vi.md) |
| Xem prototype giao diện | Mở `prototype/index.html` bằng trình duyệt (không cần server) |

## Build tài liệu DOCX

Đặc tả DOCX được sinh tự động từ file markdown — không sửa tay file `.docx`:

```bash
pip install python-docx   # lần đầu
python tools/build_project_idea_docx.py
```

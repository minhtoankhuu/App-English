# Đặc tả Giai đoạn 1D — Tích hợp OpenAI thật + RAG (embedding/hybrid search) + Cấu hình AI

## Bối cảnh

Từ đầu dự án, `AIProvider` (PRD mục 10) chỉ có `MockAIProvider` — sinh câu hỏi từ fixture viết tay, không gọi AI thật, không cần API key (quyết định chủ dự án 19/07/2026: tích hợp LLM làm sau cùng khi UI+BE+FE hoàn tất). Đến nay UI+BE+FE cho luồng đề thi + Kho kiến thức đã xong (Giai đoạn 1A-1C). Chủ dự án đã có API key **OpenAI** và xác nhận bắt đầu Giai đoạn 1D, chọn xây **RAG thật (embedding + hybrid search)** ngay từ đầu thay vì nối AI thật trước với ngữ cảnh đơn giản.

Đây cũng là lúc giải quyết nốt mục còn lại của Giai đoạn 1C: màn Admin "Cấu hình AI" (trước đó ghi nhận "chưa có chức năng vì gắn với prompt LLM thật, chờ 1D").

**Quyết định đã chốt với chủ dự án (21/07/2026):**
- Reranker dùng **Reciprocal Rank Fusion (RRF)** kết hợp full-text + vector, không thêm bước LLM rerank riêng (rẻ hơn, đủ tốt ở quy mô mỗi Unit/GrammarPoint chỉ vài chục-200 chunk).
- `GenerationLog` chỉ lưu metadata (provider/model/token/chunk ID tham chiếu), **không lưu** nguyên văn prompt/response (tránh lưu lâu dài nội dung sách giáo khoa có bản quyền).
- Giữ nguyên `daily_generation_limit = 10`/giáo viên/ngày dù giờ mỗi lượt sinh là tiền thật.

## Không làm trong đợt này

- Không xây `IngestionJob` (bảng job riêng theo PRD 15) — dùng script CLI đồng bộ giống `import_knowledge.py`, đơn giản hơn nhưng đủ dùng ở quy mô hiện tại.
- Không thêm LLM-based rerank (đã chốt ở trên).
- Không đổi `daily_generation_limit`.
- Không làm local LLM adapter (PRD: "local LLM là adapter thêm sau").
- Không đổi UI luồng sinh đề (`ExamBuilderPage`...) — chỉ đổi provider đứng sau, giao diện gọi API y hệt cũ.

## 1. Hạ tầng RAG

### 1.1 Cột embedding trên `KnowledgeChunk` (không tách bảng `ChunkEmbedding` riêng)

Thêm vào `app/models/knowledge.py`:
```python
embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
Lý do không tách bảng: quan hệ 1 chunk : tối đa 1 embedding hiện hành, không cần lịch sử nhiều embedding song song; nhất quán với cách `search_vector` (TSVECTOR) đã được thêm thẳng lên chunk thay vì tách bảng riêng. `embedding_model`/`embedded_at` cho phép script embed biết chunk nào cần embed lại khi đổi model, không cần bảng job riêng.

Model dùng: `text-embedding-3-small` (1536 chiều, rẻ nhất trong nhóm dùng được).

### 1.2 Cột embedding trên `Question` (cho Validation Engine, mục 5)

```python
embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
```
Chỉ populate khi câu được duyệt vào ngân hàng (`is_in_bank` chuyển `True`, hook tại `routers/exams.py` hàm `complete_review()` dòng set `q.is_in_bank = True`).

### 1.3 Migration

Một migration mới (`revises fb9639cd5a3a`), viết tay (không dùng autogenerate cho phần đụng tới `knowledge_chunks`/`questions` — gotcha đã biết: SQLAlchemy không phản chiếu đúng `ondelete=CASCADE` hiện có, autogenerate sẽ đề xuất xóa/tạo lại FK/index không liên quan, xem `c2e6a1f9d3b4_add_knowledge_base.py`):

1. `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`.
2. `ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(1536), embedding_model varchar(64), embedded_at timestamptz`.
3. `CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)` — HNSW (pgvector ≥0.5, image `pgvector/pgvector:pg16` đã hỗ trợ) thay vì ivfflat vì không cần biết trước số dòng để chọn tham số `lists`.
4. `ALTER TABLE questions ADD COLUMN embedding vector(1536)`.
5. Tạo bảng `ai_provider_configs`, `generation_logs` (mục 3) — phần này autogenerate được vì là bảng hoàn toàn mới.
6. `downgrade()`: drop 2 bảng mới, drop cột/index embedding; **không drop extension** `vector` (tránh lỗi nếu có object khác phụ thuộc).

`backend/tests/conftest.py`: engine fixture chạy `CREATE EXTENSION IF NOT EXISTS vector` (qua `text()`) ngay trước `Base.metadata.create_all(eng)` — test dùng `create_all` chứ không chạy Alembic, migration ở trên không tự áp dụng cho DB test.

### 1.4 Dependencies

`backend/requirements.txt` thêm (đã cài, đã pin — xem file):
```
openai==1.59.9
pgvector==0.3.6
cryptography==43.0.3
tiktoken==0.8.0
```

## 2. Hybrid search + fusion — `app/services/rag_search.py` (mới)

```python
@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    raw_text: str
    section_title: str
    chunk_type: DocumentChunkType
    fused_score: float

def hybrid_search(
    db: Session, embed_client: EmbeddingClient, *, query_text: str,
    unit_id: uuid.UUID | None = None, grammar_point_ids: list[uuid.UUID] | None = None,
    top_k: int = 8, candidate_k: int = 30,
) -> list[RetrievedChunk]
```

- Lọc phạm vi **trước** khi tính hạng: join `KnowledgeDocument`, filter `is_published=True` và đúng `unit_id` hoặc `grammar_point_id in grammar_point_ids` (tùy nguồn đề — không lọc cả hai cùng lúc).
- Nhánh full-text: tái dùng đúng cách `routers/knowledge.py` đang làm (`func.plainto_tsquery("simple", q)`, `ts_rank`) — factor thành hàm `_fts_candidates()` dùng chung.
- Nhánh vector: `embed_client.embed_one(query_text)` rồi `KnowledgeChunk.embedding.cosine_distance(query_vec)` (toán tử `<=>` của pgvector qua package `pgvector.sqlalchemy`).
- Fusion: **RRF**, `score = Σ 1/(60 + rank_i)` trên 2 danh sách hạng (full-text, vector) — hằng số 60 theo giá trị chuẩn phổ biến trong tài liệu RRF, không cần tune.
- Nguồn Cambridge (`Exam.source_type == CAMBRIDGE`) không có Knowledge Base (`import_knowledge.py`: "Không đụng Cambridge/Tense/G9") → `hybrid_search` trả `[]` khi không truyền `unit_id`/`grammar_point_ids` — `OpenAIProvider` phải xử lý tường minh (cảnh báo "không có nguồn RAG", không lỗi ngầm, đúng PRD mục 10/17).

`EmbeddingClient` là interface nhỏ (`embed_one(text) -> list[float]`, `embed_batch(texts) -> list[list[float]]`) implement bằng OpenAI SDK — tách riêng để `rag_search.py`/`validation.py` không phụ thuộc trực tiếp SDK, dễ test bằng fake client.

## 3. Model cấu hình AI + log sinh đề

### `app/models/ai_config.py` (mới)

```python
class AIProviderConfig(TimestampMixin, Base):
    __tablename__ = "ai_provider_configs"
    id: UUID (pk)
    provider: str                         # "openai" — string để mở rộng sau, không Enum cứng
    model: str                            # vd "gpt-4o-mini", whitelist ở tầng schema/router
    embedding_model: str                  # vd "text-embedding-3-small"
    api_key_encrypted: bytes              # Fernet token — KHÔNG BAO GIỜ trả nguyên qua API
    temperature: float = 0.7
    duplicate_similarity_threshold: float = 0.90   # PRD 11, Admin chỉnh được
    is_active: bool = True
    updated_by_user_id: UUID | None (FK users.id, nullable — set NULL nếu admin bị xóa)
```
Đúng 1 dòng "đang dùng" tại một thời điểm (`is_active=True`) — endpoint `PUT` là upsert dòng active duy nhất, không có khái niệm chọn provider theo từng lần sinh. Đơn giản nhất, đúng quy mô hệ thống (PRD 22.1 — 1 Admin).

### `app/models/generation_log.py` (mới)

```python
class GenerationLog(Base):
    __tablename__ = "generation_logs"
    id: UUID (pk)
    created_at: datetime (server_default now())
    exam_id: UUID | None (FK exams.id, ondelete="SET NULL")
    block_id: UUID | None (FK exam_blocks.id, ondelete="SET NULL")
    provider: str
    model: str
    prompt_version: str
    params: JSONB                          # temperature, max_tokens...
    question_count_requested: int
    source_chunk_ids: JSONB                # list[str(uuid)] — KHÔNG lưu raw_text
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost_usd: numeric(10,6) | None
    status: str                            # "success" | "error"
    error_message: str | None              # lọc bỏ API key trước khi ghi
```
Không có cột raw prompt/response (quyết định đã chốt ở Bối cảnh).

## 4. Mã hóa API key — `app/services/crypto.py` (mới)

```python
def encrypt_api_key(raw: str) -> bytes: ...   # Fernet(settings.ai_config_encryption_key).encrypt(...)
def decrypt_api_key(token: bytes) -> str: ...
```
`app/config.py` thêm `ai_config_encryption_key: str` (Fernet key hợp lệ — 32 byte urlsafe-base64). `.env.example` thêm dòng mẫu kèm chú thích "đổi ở production, tạo bằng `Fernet.generate_key()`".

Masking: API luôn trả `api_key_masked: str` (`"sk-...ab12"`, giữ 4 ký tự cuối), không bao giờ trả key đầy đủ/giải mã được qua bất kỳ response nào. `PUT` nhận `api_key: str | None` — `None`/rỗng = giữ nguyên key cũ (Admin sửa model/temperature không cần nhập lại key).

## 5. `OpenAIProvider` — `app/services/openai_provider.py` (mới)

Implement đúng `AIProvider` ABC hiện có (`generate`, `regenerate_one`) — **không đổi** `QuestionDraft`/`BlockSpec` dataclass, giữ tương thích với `generation.py` đang dùng.

`GenerationContext` (`app/services/ai_provider.py`) thêm 2 field mới (không đổi field cũ): `unit_id: uuid.UUID | None`, `grammar_point_ids: list[uuid.UUID] = field(default_factory=list)` — cần để `hybrid_search` lọc đúng phạm vi. `generation.py::_build_context()` set thêm 2 field này từ `exam.unit_id`/`exam.grammar_selections`.

Luồng `generate()`:
1. Build query text từ `context` + `block.exercise_type_code` → `hybrid_search()` lấy top-8 chunk.
2. Chọn prompt template theo `exercise_type_code` (thư mục `app/services/prompts/`, 1 hàm/dạng bài, mỗi template có `prompt_version` string).
3. Gọi Chat Completions với Structured Outputs (`response_format={"type": "json_schema", ...}`) — schema JSON tương ứng field `QuestionDraft` + `source_chunk_ids: list[str]` + `insufficient_source_warning: str | None`.
4. Parse bằng Pydantic model trung gian `OpenAIQuestionResponse` (tách hợp đồng với OpenAI khỏi hợp đồng nội bộ `QuestionDraft`) rồi map sang `QuestionDraft`.
5. Retry tối đa 2 lần bổ sung khi lỗi mạng/JSON/rate-limit, backoff cố định ngắn (PRD 17). Hết retry → raise `AIGenerationError` (mới, trong `ai_provider.py`) — router trả HTTP 502 tiếng Việt, **không** âm thầm rơi về Mock (tránh giáo viên tưởng nhầm AI thật).
6. Ghi `GenerationLog` sau mỗi lần gọi kể cả lỗi cuối cùng (`status="error"`).

`regenerate_one()`: tương tự, `question_count=1`, thêm `exclude_prompt` vào prompt.

## 6. Provider factory — sửa `generation.py`

Xóa `_provider: AIProvider = MockAIProvider()` (singleton cứng). Thêm `app/services/ai_provider_factory.py`:
```python
def get_active_provider(db: Session) -> AIProvider:
    config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
    return MockAIProvider() if config is None else OpenAIProvider(config, decrypt_api_key(config.api_key_encrypted))
```
`generate_block_questions`/`regenerate_question` gọi `get_active_provider(db)` ở đầu hàm (cả 2 đã nhận `db: Session` sẵn — không đổi chữ ký hàm public, không đổi call site ở `routers/exams.py`). Chưa cấu hình AI → tự động dùng Mock (an toàn, không lỗi cứng).

## 7. Validation Engine — sửa `app/services/validation.py`

Giữ nguyên fuzzy-match hiện có, **thêm** (không thay) kiểm tra cosine embedding (đúng nghĩa "kết hợp" PRD 11):
- `validate_draft()` thêm tham số `draft_embedding: list[float] | None = None` (không tự gọi OpenAI bên trong — giữ module này không phụ thuộc SDK, nhận vector đã tính sẵn từ caller).
- `generation.py` embed **theo batch** toàn bộ `drafts` của 1 block một lần (không embed từng câu trong vòng lặp — 1 block 20 câu chỉ 1 round-trip thay vì 20).
- So cosine với `Question.embedding` của các câu `is_in_bank=True`; ngưỡng đọc từ `AIProviderConfig.duplicate_similarity_threshold` (fallback 0.90 nếu chưa có config).
- Cảnh báo mới tách biệt: `"Có thể trùng câu trong ngân hàng (khớp {sim:.0%} theo embedding)."` — độc lập với cảnh báo fuzzy hiện có.

## 8. Ingestion embedding — `app/embed_knowledge.py` (mới, CLI riêng)

```
python -m app.embed_knowledge [--force] [--batch-size 100]
```
- Query chunk có `document.is_published=True` và (`embedding IS NULL` hoặc `embedding_model != config hiện tại`), trừ khi `--force`.
- Batch qua OpenAI embeddings endpoint, commit theo batch (crash giữa chừng không mất tiến trình — tự resumable nhờ điều kiện WHERE).
- In số chunk đã xử lý/còn lại + ước tính chi phí (đếm token bằng `tiktoken`).
- **Không tự động chạy** — lệnh này gọi OpenAI thật, tốn tiền thật (ước tính <1 USD cho ~7900 chunk hiện có ở giá `text-embedding-3-small`, nhưng vẫn cần chủ dự án bấm chạy tay).

## 9. Router + schema Admin — `app/routers/admin_ai_config.py` (mới, mirror `admin_knowledge.py`)

```
GET  /admin/ai-config        -> AIProviderConfigOut (key masked) hoặc 404 nếu chưa cấu hình
PUT  /admin/ai-config        -> upsert dòng active duy nhất; record_audit_log(action="ai_config.updated")
POST /admin/ai-config/test   -> gọi 1 request rẻ thật tới OpenAI xác nhận key hợp lệ trước khi lưu
```
`app/schemas/ai_config.py`: `AIProviderConfigOut` (id, provider, model, embedding_model, temperature, duplicate_similarity_threshold, is_active, api_key_masked, updated_at), `AIProviderConfigUpdateRequest` (model, temperature, duplicate_similarity_threshold, api_key: str | None). Model whitelist (vd `gpt-4o-mini`, `gpt-4o`) validate ở schema — không free-text, tránh Admin gõ sai tên model gây lỗi runtime khó hiểu (Structured Outputs cần model hỗ trợ).

Đăng ký router trong `app/main.py`.

**Tổng quát hóa `record_audit_log`** (`app/services/audit.py`): hiện chỉ nhận `target: User` (hardcode `target_type="teacher"`). Đổi chữ ký nhận trực tiếp `target_type: str, target_id: uuid.UUID, target_label: str` — cập nhật 6 call site hiện có trong `admin.py` (truyền `target_type="teacher", target_id=teacher.id, target_label=teacher.email`), không đổi hành vi audit log hiện tại.

## 10. Frontend

- `frontend/src/api/admin.ts`: `getAIConfig()`, `updateAIConfig()`, `testAIConfig()`.
- `frontend/src/types/admin.ts`: `AIProviderConfigOut`.
- `frontend/src/pages/AdminAIConfigPage.tsx` (mới, mirror cấu trúc `AdminKnowledgePage.tsx`): form 1 dòng cấu hình — dropdown model cố định (không free-text), input API key `type="password"` (hiện masked khi đã có, để trống = giữ nguyên), số cho `temperature`/`duplicate_similarity_threshold`, nút "Kiểm tra kết nối".
- `frontend/src/App.tsx`: route `/admin/ai-config`.
- `frontend/src/Layout.tsx`: thêm mục nav `{ to: "/admin/ai-config", label: "Cấu hình AI" }` vào `ADMIN_NAV`.
- `AdminOverviewPage.tsx`: card "Cấu hình AI" (hiện là mục "Sắp triển khai") chuyển sang hiển thị trạng thái thật (model đang active / "Chưa cấu hình").

## Kiểm thử

Backend: migration áp dụng sạch (`alembic upgrade head` + `downgrade` roundtrip); `rag_search.hybrid_search` với fixture nhỏ trong DB test (không gọi OpenAI thật — fake `EmbeddingClient` trả vector cố định); `OpenAIProvider` mock hẳn OpenAI SDK response (không gọi API thật trong test/CI); `crypto.py` encrypt/decrypt roundtrip + key khác nhau không giải mã chéo được; `admin_ai_config` router (masking đúng, giữ key cũ khi để trống, validate model whitelist, audit log ghi đúng); `generation.py` dùng `get_active_provider` (rà test cũ có mock `_provider` module-level không, cập nhật cách mock); Validation Engine test cosine threshold đọc đúng từ config, fallback 0.90 khi chưa có config.

Frontend: `AdminAIConfigPage` — hiển thị đúng khi chưa cấu hình, lưu thành công ẩn key, để trống ô key khi sửa không xóa key cũ, nút test gọi đúng API.

Không chạy `embed_knowledge.py` thật hay tạo đề thật qua OpenAI trong quá trình code/test (tốn tiền thật) — việc này để chủ dự án tự bấm chạy sau khi review code, có xác nhận riêng trước khi thực hiện.

Verification cuối (không tốn tiền OpenAI): `pytest` toàn bộ backend, `npm run lint && npm test && npm run build` frontend, rebuild Docker Compose xác nhận migration áp dụng sạch trên container thật (không cần gọi OpenAI thật để xác nhận việc này).

## Git workflow

Nhánh mới `feat/1d-openai-rag-integration` (Giai đoạn 1D là phase mới, tách khỏi `feat/1c-admin-knowledge-base` đã merge/còn PR #16 riêng).

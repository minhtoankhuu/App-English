"""OpenAIProvider — adapter AIProvider thật (Giai đoạn 1D), dùng OpenAI Chat
Completions API với Structured Outputs (JSON schema ép đúng cấu trúc) và ngữ cảnh
RAG lấy từ `rag_search.hybrid_search`. Xem
docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md.
"""

from __future__ import annotations

import json
import time

import openai
from sqlalchemy.orm import Session

from app.models.ai_config import AIProviderConfig
from app.models.generation_log import GenerationLog
from app.services.ai_provider import AIGenerationError, AIProvider, BlockSpec, GenerationContext, QuestionDraft
from app.services.openai_embedding import OpenAIEmbeddingClient
from app.services.prompts import PROMPT_VERSION, build_system_prompt, build_user_prompt
from app.services.rag_search import RetrievedChunk, hybrid_search, retrieval_profile
from app.services.text_markup import dedupe_pronunciation_suffix

_MAX_ATTEMPTS = 3  # 1 lần gọi đầu + tối đa 2 lần retry (PRD 17)


def _sanitize_options(options: list[dict] | None) -> list[dict] | None:
    """Chặn lỗi model nhân đôi ký tự đuôi phát âm ngay khi lưu (vd 'cats<u>s</u>' →
    'cat<u>s</u>') để cả DOCX lẫn preview web đều sạch, không phụ thuộc render (xem
    app/services/text_markup.py)."""
    if not options:
        return options
    return [{**opt, "text": dedupe_pronunciation_suffix(opt["text"])} if opt.get("text") else opt for opt in options]

# Giá tham khảo gpt-4o-mini (USD/1 triệu token) tại thời điểm viết — chỉ ước tính
# sơ bộ cho GenerationLog, không phải nguồn giá chính thức.
_PRICE_PER_1M_INPUT = 0.15
_PRICE_PER_1M_OUTPUT = 0.60

_QUESTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt_text": {"type": "string"},
        "passage_text": {"type": ["string", "null"]},
        "options": {
            "type": ["array", "null"],
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "text": {"type": "string"},
                    "is_correct": {"type": "boolean"},
                },
                "required": ["label", "text", "is_correct"],
                "additionalProperties": False,
            },
        },
        "answer_text": {"type": "string"},
        "explanation": {"type": "string"},
        "target_knowledge": {"type": "string"},
        "level_code": {"type": "string"},
        "source_chunk_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "prompt_text",
        "passage_text",
        "options",
        "answer_text",
        "explanation",
        "target_knowledge",
        "level_code",
        "source_chunk_ids",
    ],
    "additionalProperties": False,
}

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {"type": "array", "items": _QUESTION_ITEM_SCHEMA},
        "insufficient_source_warning": {"type": ["string", "null"]},
    },
    "required": ["questions", "insufficient_source_warning"],
    "additionalProperties": False,
}


class OpenAIProvider(AIProvider):
    def __init__(self, config: AIProviderConfig, api_key: str, db: Session):
        self._config = config
        self._client = openai.OpenAI(api_key=api_key)
        self._embed_client = OpenAIEmbeddingClient(api_key, config.embedding_model)
        self._db = db

    def _retrieve(self, block: BlockSpec, context: GenerationContext) -> list[RetrievedChunk]:
        # Không nhét exercise_type_code vào query — đó là mã dạng bài tiếng Anh
        # ("multiple_choice"...), không xuất hiện trong nội dung sách nên chỉ làm
        # plainto_tsquery (AND toàn bộ từ) trật khớp. prompt_override (nếu giáo
        # viên có nhập) là tín hiệu tìm kiếm tốt nhất; không có thì để trống — phạm
        # vi Unit/GrammarPoint đã đủ hẹp, rag_search có fallback khi không tìm được gì.
        # OpenAI embeddings từ chối input rỗng — luôn cần 1 chuỗi có nghĩa, kể cả khi
        # không có unit_title (đề "Kiến thức chung") lẫn prompt_override.
        query_text = block.prompt_override or context.unit_title or "kiến thức bài học"
        # Truy xuất theo dạng bài: lọc loại chunk phù hợp + top_k riêng cho dạng này,
        # thay vì cùng 1 rổ cho mọi dạng trong Unit (xem rag_search.retrieval_profile).
        chunk_types, top_k = retrieval_profile(block.exercise_type_code)
        return hybrid_search(
            self._db,
            self._embed_client,
            query_text=query_text,
            unit_id=context.unit_id,
            grammar_point_ids=context.grammar_point_ids or None,
            top_k=top_k,
            chunk_types=chunk_types,
        )

    def _call_openai(self, system_prompt: str, user_prompt: str) -> tuple[dict, int | None, int | None]:
        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = self._client.chat.completions.create(
                    model=self._config.model,
                    temperature=self._config.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "question_generation", "schema": _RESPONSE_SCHEMA, "strict": True},
                    },
                )
                parsed = json.loads(response.choices[0].message.content)
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else None
                completion_tokens = usage.completion_tokens if usage else None
                return parsed, prompt_tokens, completion_tokens
            except (openai.APIError, json.JSONDecodeError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(1)
        raise AIGenerationError(f"Sinh câu hỏi thất bại sau {_MAX_ATTEMPTS} lần thử: {last_error}") from last_error

    def _log(
        self,
        *,
        question_count: int,
        retrieved: list[RetrievedChunk],
        prompt_tokens: int | None,
        completion_tokens: int | None,
        status: str,
        error: str | None = None,
    ) -> None:
        cost = None
        if prompt_tokens is not None and completion_tokens is not None:
            cost = prompt_tokens / 1_000_000 * _PRICE_PER_1M_INPUT + completion_tokens / 1_000_000 * _PRICE_PER_1M_OUTPUT
        log = GenerationLog(
            provider="openai",
            model=self._config.model,
            prompt_version=PROMPT_VERSION,
            params={"temperature": self._config.temperature},
            question_count_requested=question_count,
            source_chunk_ids=[str(c.chunk_id) for c in retrieved],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost,
            status=status,
            error_message=error,
        )
        self._db.add(log)
        self._db.flush()

    def _draft_from_item(self, item: dict, block: BlockSpec, warning: str | None) -> QuestionDraft:
        source_ref = "; ".join(item.get("source_chunk_ids") or []) or "Không có nguồn RAG"
        if warning:
            source_ref = f"{source_ref} — CẢNH BÁO: {warning}"
        return QuestionDraft(
            prompt_text=item["prompt_text"],
            answer_text=item["answer_text"],
            explanation=item["explanation"],
            target_knowledge=item["target_knowledge"],
            level_code=item.get("level_code") or block.level_code,
            source_ref=source_ref,
            passage_text=item.get("passage_text"),
            options=_sanitize_options(item.get("options")),
        )

    def generate(self, block: BlockSpec, context: GenerationContext) -> list[QuestionDraft]:
        retrieved = self._retrieve(block, context)
        system_prompt = build_system_prompt(block.exercise_type_code, block.question_count, block.level_code)
        user_prompt = build_user_prompt(
            context.unit_title, [(str(c.chunk_id), c.raw_text) for c in retrieved], block.prompt_override, None
        )
        try:
            parsed, prompt_tokens, completion_tokens = self._call_openai(system_prompt, user_prompt)
        except AIGenerationError:
            self._log(
                question_count=block.question_count,
                retrieved=retrieved,
                prompt_tokens=None,
                completion_tokens=None,
                status="error",
                error="hết retry",
            )
            raise
        self._log(
            question_count=block.question_count,
            retrieved=retrieved,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success",
        )
        warning = parsed.get("insufficient_source_warning")
        return [self._draft_from_item(item, block, warning) for item in parsed["questions"]]

    def regenerate_one(
        self, block: BlockSpec, context: GenerationContext, exclude_prompt: str | None = None
    ) -> QuestionDraft:
        retrieved = self._retrieve(block, context)
        system_prompt = build_system_prompt(block.exercise_type_code, 1, block.level_code)
        user_prompt = build_user_prompt(
            context.unit_title,
            [(str(c.chunk_id), c.raw_text) for c in retrieved],
            block.prompt_override,
            exclude_prompt,
        )
        try:
            parsed, prompt_tokens, completion_tokens = self._call_openai(system_prompt, user_prompt)
        except AIGenerationError:
            self._log(
                question_count=1,
                retrieved=retrieved,
                prompt_tokens=None,
                completion_tokens=None,
                status="error",
                error="hết retry",
            )
            raise
        if not parsed["questions"]:
            self._log(
                question_count=1,
                retrieved=retrieved,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                status="error",
                error="nguồn không đủ để sinh câu",
            )
            raise AIGenerationError("OpenAI không sinh được câu hỏi nào — nguồn RAG không đủ.")
        self._log(
            question_count=1,
            retrieved=retrieved,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success",
        )
        warning = parsed.get("insufficient_source_warning")
        return self._draft_from_item(parsed["questions"][0], block, warning)

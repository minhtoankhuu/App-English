"""Interface AIProvider (PRD mục 10) và MockAIProvider dùng cho giai đoạn phát triển
trước khi tích hợp LLM thật + RAG (DEVELOPMENT_PLAN mục 3, Giai đoạn 1D).

MockAIProvider sinh câu hỏi từ fixture bank viết tay (không gọi AI thật, không cần
API key). Khi có RAG/LLM thật, chỉ cần thêm một adapter mới cùng implement
AIProvider — pipeline sinh đề (app/services/generation.py) không phải sửa.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services import fixtures


@dataclass
class GenerationContext:
    grade_number: int
    school_stage_code: str
    exam_level_code: str
    unit_title: str | None = None
    unit_order_no: int | None = None


@dataclass
class BlockSpec:
    exercise_type_code: str
    question_count: int
    level_code: str
    passage_word_target: int | None = None
    prompt_override: str | None = None


@dataclass
class QuestionDraft:
    prompt_text: str
    answer_text: str
    explanation: str
    target_knowledge: str
    level_code: str
    source_ref: str
    passage_text: str | None = None
    options: list[dict] | None = field(default=None)


class AIProvider(ABC):
    @abstractmethod
    def generate(self, block: BlockSpec, context: GenerationContext) -> list[QuestionDraft]:
        """Sinh đúng block.question_count câu hỏi cho block này."""

    @abstractmethod
    def regenerate_one(
        self, block: BlockSpec, context: GenerationContext, exclude_prompt: str | None = None
    ) -> QuestionDraft:
        """Sinh lại một câu duy nhất, tránh trùng nội dung câu cũ nếu có thể."""


class MockAIProvider(AIProvider):
    """Sinh câu hỏi từ fixture bank viết tay. Ưu tiên bộ câu "vàng" khớp golden test
    (Global Success 7 - Unit 3) nếu ngữ cảnh khớp, còn lại dùng template chung theo
    dạng bài — đủ đa dạng để test pipeline & Validation Engine mà không cần AI thật."""

    def _pool(self, block: BlockSpec, context: GenerationContext) -> list[dict]:
        golden: list[dict] = []
        if context.grade_number == 7 and context.unit_order_no == 3:
            golden = fixtures.GOLDEN_UNIT3_QUESTIONS.get(block.exercise_type_code, [])
        generic = fixtures.GENERIC_TEMPLATES.get(block.exercise_type_code, [])
        pool = golden + generic
        return pool or fixtures.fallback_template(block.exercise_type_code)

    def _draft_from_template(self, template: dict, block: BlockSpec) -> QuestionDraft:
        return QuestionDraft(
            prompt_text=template["prompt_text"],
            answer_text=template["answer_text"],
            explanation=template["explanation"],
            target_knowledge=template["target_knowledge"],
            level_code=template.get("level_code", block.level_code),
            source_ref=template.get("source_ref", "Mock — chưa có RAG"),
            passage_text=template.get("passage_text"),
            options=template.get("options"),
        )

    def generate(self, block: BlockSpec, context: GenerationContext) -> list[QuestionDraft]:
        pool = self._pool(block, context)
        return [self._draft_from_template(pool[i % len(pool)], block) for i in range(block.question_count)]

    def regenerate_one(
        self, block: BlockSpec, context: GenerationContext, exclude_prompt: str | None = None
    ) -> QuestionDraft:
        pool = self._pool(block, context)
        candidates = pool
        if exclude_prompt and len(pool) > 1:
            filtered = [t for t in pool if t["prompt_text"] != exclude_prompt]
            if filtered:
                candidates = filtered
        return self._draft_from_template(random.choice(candidates), block)

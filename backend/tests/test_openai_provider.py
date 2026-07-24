import json
from unittest.mock import MagicMock, patch

import openai
import pytest
from sqlalchemy import select

from app.models.academic import Grade, Unit
from app.models.ai_config import AIProviderConfig
from app.models.generation_log import GenerationLog
from app.models.knowledge import EMBEDDING_DIM, DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.services.ai_provider import AIGenerationError, BlockSpec, GenerationContext
from app.services.crypto import encrypt_api_key
from app.services.openai_provider import OpenAIProvider


def _unit3_grade7(db) -> Unit:
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def _make_config(db) -> AIProviderConfig:
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        api_key_encrypted=encrypt_api_key("sk-test"),
        temperature=0.7,
        is_active=True,
    )
    db.add(config)
    db.flush()
    return config


def _make_chunk(db, document, *, raw_text, order_no=1) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        document_id=document.id,
        order_no=order_no,
        chunk_type=DocumentChunkType.VOCABULARY,
        section_title="VOCABULARY",
        raw_text=raw_text,
    )
    db.add(chunk)
    db.flush()
    return chunk


def _valid_response_json(question_count: int = 1, warning=None) -> str:
    return json.dumps(
        {
            "questions": [
                {
                    "prompt_text": f"Question {i}",
                    "passage_text": None,
                    "options": [
                        {"label": "A", "text": "opt A", "is_correct": True},
                        {"label": "B", "text": "opt B", "is_correct": False},
                    ],
                    "answer_text": "A. opt A",
                    "explanation": "because reasons",
                    "target_knowledge": "Present Simple",
                    "level_code": "A2",
                    "source_chunk_ids": ["chunk-1"],
                }
                for i in range(question_count)
            ],
            "insufficient_source_warning": warning,
        }
    )


def _mock_completion(content: str, prompt_tokens=100, completion_tokens=50):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    response.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return response


@pytest.fixture
def provider_setup(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    _make_chunk(seeded_db, doc, raw_text="present simple usage rule")
    config = _make_config(seeded_db)
    context = GenerationContext(
        grade_number=7, school_stage_code="secondary", exam_level_code="A2",
        unit_title="Unit 3", unit_id=unit.id,
    )
    block = BlockSpec(exercise_type_code="multiple_choice", question_count=1, level_code="A2")
    return seeded_db, config, context, block


def _fake_embed_client():
    client = MagicMock()
    client.embed_one.return_value = [0.0] * EMBEDDING_DIM
    return client


def test_generate_returns_question_drafts(provider_setup):
    db, config, context, block = provider_setup
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = _mock_completion(_valid_response_json())
        provider = OpenAIProvider(config, "sk-test", db)
        drafts = provider.generate(block, context)

    assert len(drafts) == 1
    assert drafts[0].prompt_text == "Question 0"
    assert drafts[0].options[0]["label"] == "A"
    assert "chunk-1" in drafts[0].source_ref


def test_generate_writes_success_generation_log(provider_setup):
    db, config, context, block = provider_setup
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = _mock_completion(_valid_response_json())
        provider = OpenAIProvider(config, "sk-test", db)
        provider.generate(block, context)

    log = db.scalar(select(GenerationLog))
    assert log is not None
    assert log.status == "success"
    assert log.provider == "openai"
    assert log.prompt_tokens == 100
    assert log.completion_tokens == 50
    assert log.estimated_cost_usd is not None


def test_generate_retries_then_succeeds(provider_setup):
    db, config, context, block = provider_setup
    fake_request = MagicMock()
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls, \
         patch("app.services.openai_provider.time.sleep"):
        mock_openai_cls.return_value.chat.completions.create.side_effect = [
            openai.APIConnectionError(request=fake_request),
            _mock_completion(_valid_response_json()),
        ]
        provider = OpenAIProvider(config, "sk-test", db)
        drafts = provider.generate(block, context)

    assert len(drafts) == 1


def test_generate_raises_after_max_retries(provider_setup):
    db, config, context, block = provider_setup
    fake_request = MagicMock()
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls, \
         patch("app.services.openai_provider.time.sleep"):
        mock_openai_cls.return_value.chat.completions.create.side_effect = openai.APIConnectionError(
            request=fake_request
        )
        provider = OpenAIProvider(config, "sk-test", db)
        with pytest.raises(AIGenerationError):
            provider.generate(block, context)

    log = db.scalar(select(GenerationLog))
    assert log.status == "error"


def test_regenerate_one_raises_when_no_questions_returned(provider_setup):
    db, config, context, block = provider_setup
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = _mock_completion(
            _valid_response_json(question_count=0)
        )
        provider = OpenAIProvider(config, "sk-test", db)
        with pytest.raises(AIGenerationError):
            provider.regenerate_one(block, context)


def test_insufficient_source_warning_appended_to_source_ref(provider_setup):
    db, config, context, block = provider_setup
    with patch("app.services.openai_provider.OpenAIEmbeddingClient", return_value=_fake_embed_client()), \
         patch("app.services.openai_provider.openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = _mock_completion(
            _valid_response_json(warning="thiếu tài liệu về dạng bài này")
        )
        provider = OpenAIProvider(config, "sk-test", db)
        drafts = provider.generate(block, context)

    assert "CẢNH BÁO" in drafts[0].source_ref

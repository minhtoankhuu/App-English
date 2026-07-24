from app.models.ai_config import AIProviderConfig
from app.services.ai_provider import MockAIProvider
from app.services.ai_provider_factory import get_active_provider
from app.services.crypto import encrypt_api_key
from app.services.openai_provider import OpenAIProvider


def test_returns_mock_when_not_configured(seeded_db):
    provider = get_active_provider(seeded_db)
    assert isinstance(provider, MockAIProvider)


def test_returns_openai_provider_when_configured(seeded_db):
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        api_key_encrypted=encrypt_api_key("sk-test"),
        is_active=True,
    )
    seeded_db.add(config)
    seeded_db.flush()

    provider = get_active_provider(seeded_db)
    assert isinstance(provider, OpenAIProvider)


def test_ignores_inactive_config(seeded_db):
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        api_key_encrypted=encrypt_api_key("sk-test"),
        is_active=False,
    )
    seeded_db.add(config)
    seeded_db.flush()

    provider = get_active_provider(seeded_db)
    assert isinstance(provider, MockAIProvider)

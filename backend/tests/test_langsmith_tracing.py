"""Test công tắc tracing LangSmith — trọng tâm là fail-safe: tracing tắt/hỏng thì
pipeline sinh đề phải chạy y như chưa có gì (không kwargs lạ, không client lạ)."""

import pytest

from app.services import langsmith_tracing as lst


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)


def _enable(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_test")


class _FakeClient:
    pass


def test_disabled_by_default():
    assert lst.tracing_enabled() is False


@pytest.mark.parametrize("value, expected", [("true", True), ("1", True), ("TRUE", True), ("on", True),
                                             ("false", False), ("0", False), ("", False)])
def test_switch_reads_env(monkeypatch, value, expected):
    monkeypatch.setenv("LANGSMITH_TRACING", value)
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_test")
    assert lst.tracing_enabled() is expected


def test_stays_off_without_api_key(monkeypatch):
    """Bật công tắc mà quên API key -> SDK log lỗi mỗi lần gọi, thà tắt hẳn."""
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert lst.tracing_enabled() is False


def test_returns_client_untouched_when_disabled():
    client = _FakeClient()
    assert lst.wrap_openai_client(client) is client


def test_wraps_client_when_enabled(monkeypatch):
    """`wrap_openai` vá tại chỗ và trả chính client đó, nên kiểm `create` đã bị thay
    chứ không kiểm danh tính đối tượng."""
    import openai

    client = openai.OpenAI(api_key="sk-test-not-used")
    original_create = client.chat.completions.create

    _enable(monkeypatch)
    wrapped = lst.wrap_openai_client(client)

    assert wrapped.chat.completions.create is not original_create


def test_returns_client_when_langsmith_missing(monkeypatch):
    """Môi trường chưa cài gói langsmith thì bỏ qua tracing, không nổ ImportError."""
    _enable(monkeypatch)
    monkeypatch.setattr(lst, "_wrap_openai_fn", lambda: None)
    client = _FakeClient()
    assert lst.wrap_openai_client(client) is client


def test_returns_client_when_wrapping_raises(monkeypatch):
    _enable(monkeypatch)

    def _boom():
        def _raise(_client):
            raise RuntimeError("langsmith hỏng")

        return _raise

    monkeypatch.setattr(lst, "_wrap_openai_fn", _boom)
    client = _FakeClient()
    assert lst.wrap_openai_client(client) is client


def test_extra_is_empty_when_disabled():
    """Quan trọng: client lúc tắt là OpenAI thật, truyền langsmith_extra= sẽ bị API từ chối."""
    assert lst.langsmith_extra(name="generate", metadata={"exercise_type": "multiple_choice"}) == {}


def test_extra_carries_name_and_drops_none_metadata(monkeypatch):
    _enable(monkeypatch)
    extra = lst.langsmith_extra(
        name="generate:multiple_choice",
        metadata={"exercise_type": "multiple_choice", "unit_title": None, "grade": 9},
    )
    assert extra == {
        "langsmith_extra": {
            "name": "generate:multiple_choice",
            "metadata": {"exercise_type": "multiple_choice", "grade": 9},
        }
    }


def test_langsmith_extra_never_reaches_openai(monkeypatch):
    """Rủi ro lớn nhất của thiết kế này: `langsmith_extra` lọt xuống OpenAI thành tham số
    lạ và làm hỏng mọi lần sinh đề. Wrapper phải nuốt trọn nó."""
    import openai
    from langsmith.run_helpers import tracing_context

    _enable(monkeypatch)
    client = openai.OpenAI(api_key="sk-test-not-used")
    seen: dict = {}

    class _Response:
        choices: list = []
        usage = None

        def model_dump(self):
            return {"choices": []}

    def _fake_create(**kwargs):
        seen.update(kwargs)
        return _Response()

    client.chat.completions.create = _fake_create
    wrapped = lst.wrap_openai_client(client)

    # tracing_context(enabled=False): giữ nguyên lớp bọc nhưng không gửi run ra mạng.
    with tracing_context(enabled=False):
        wrapped.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            **lst.langsmith_extra(name="generate:multiple_choice", metadata={"grade": 9}),
        )

    assert "langsmith_extra" not in seen
    assert sorted(seen) == ["messages", "model"]

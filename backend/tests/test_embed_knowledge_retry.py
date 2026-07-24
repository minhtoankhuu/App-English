"""Test retry khi tiktoken tải file BPE gặp lỗi mạng thoáng qua (CI ephemeral runner
từng dính 503 "server is busy" từ blob Azure — xem app/embed_knowledge.py)."""

from unittest.mock import patch

import pytest
import requests

from app.embed_knowledge import _ENCODING_LOAD_ATTEMPTS, _load_cl100k_encoding


def test_retries_and_succeeds_after_transient_network_errors():
    calls = {"n": 0}

    def flaky(name):
        calls["n"] += 1
        if calls["n"] < _ENCODING_LOAD_ATTEMPTS:
            raise requests.exceptions.HTTPError("503 Server Error: The server is busy.")
        return "fake-encoding"

    with (
        patch("app.embed_knowledge.tiktoken.get_encoding", side_effect=flaky),
        patch("app.embed_knowledge.time.sleep") as sleep_mock,
    ):
        result = _load_cl100k_encoding()

    assert result == "fake-encoding"
    assert calls["n"] == _ENCODING_LOAD_ATTEMPTS
    assert sleep_mock.call_count == _ENCODING_LOAD_ATTEMPTS - 1


def test_raises_clear_error_after_exhausting_all_retries():
    def always_fails(name):
        raise requests.exceptions.ConnectionError("network unreachable")

    with (
        patch("app.embed_knowledge.tiktoken.get_encoding", side_effect=always_fails),
        patch("app.embed_knowledge.time.sleep"),
        pytest.raises(RuntimeError, match="Tải file mã hoá tiktoken"),
    ):
        _load_cl100k_encoding()


def test_succeeds_immediately_without_retry_when_no_error():
    with patch("app.embed_knowledge.tiktoken.get_encoding", return_value="ok") as mock_get, patch(
        "app.embed_knowledge.time.sleep"
    ) as sleep_mock:
        result = _load_cl100k_encoding()

    assert result == "ok"
    assert mock_get.call_count == 1
    sleep_mock.assert_not_called()

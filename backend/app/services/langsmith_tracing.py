"""Bọc client OpenAI bằng LangSmith để xem token/chi phí/prompt của từng lần sinh đề
trên smith.langchain.com.

Nguyên tắc: tracing là tuỳ chọn quan sát, KHÔNG được làm vỡ pipeline sinh đề. Vì vậy
mọi thứ ở đây đều fail-safe — thiếu biến môi trường, thiếu gói `langsmith`, hay
`wrap_openai` ném lỗi thì trả lại client gốc và chạy tiếp như chưa có gì.

Bật bằng đúng bộ biến môi trường chuẩn của LangSmith (xem .env.example):

    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=lsv2_...
    LANGSMITH_PROJECT=EngLish

Bản thân SDK langsmith đọc thẳng các biến này, nên ở đây chỉ cần kiểm tra công tắc bật/tắt.
"""

from __future__ import annotations

from typing import Any

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def tracing_enabled() -> bool:
    """Đọc env mỗi lần gọi (không cache) để test bật/tắt được bằng monkeypatch."""
    if os.getenv("LANGSMITH_TRACING", "").strip().lower() not in _TRUTHY:
        return False
    # Không có API key thì SDK sẽ log lỗi mỗi lần gọi — thà tắt hẳn cho sạch.
    return bool(os.getenv("LANGSMITH_API_KEY", "").strip())


def _wrap_openai_fn():
    try:
        from langsmith.wrappers import wrap_openai
    except ImportError:  # langsmith là dependency tuỳ chọn của môi trường chạy
        return None
    return wrap_openai


def wrap_openai_client(client: Any) -> Any:
    """Trả client đã bọc tracing, hoặc chính client đó nếu tracing tắt/không dùng được."""
    if not tracing_enabled():
        return client
    wrap = _wrap_openai_fn()
    if wrap is None:
        return client
    try:
        return wrap(client)
    except Exception:  # noqa: BLE001 — tracing hỏng không được chặn sinh đề
        return client


def langsmith_extra(*, name: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Kwargs gắn tên + metadata cho một run, dùng khi gọi client ĐÃ bọc.

    Trả `{}` khi tracing tắt, vì client lúc đó là OpenAI thật — truyền
    `langsmith_extra=` vào sẽ bị API từ chối là tham số lạ.
    """
    if not tracing_enabled() or _wrap_openai_fn() is None:
        return {}
    clean = {k: v for k, v in metadata.items() if v is not None}
    return {"langsmith_extra": {"name": name, "metadata": clean}}

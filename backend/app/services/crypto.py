"""Mã hóa API key provider AI trước khi lưu DB (PRD mục 10: "API key được mã hóa,
che trên giao diện và không ghi vào log"). Dùng Fernet (symmetric, AES-128-CBC +
HMAC) — đủ cho nhu cầu 1 giá trị bí mật/cấu hình, không cần public-key crypto.
"""

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().ai_config_encryption_key.encode())


def encrypt_api_key(raw: str) -> bytes:
    return _fernet().encrypt(raw.encode())


def decrypt_api_key(token: bytes) -> str:
    return _fernet().decrypt(token).decode()


def mask_api_key(raw: str) -> str:
    """Hiển thị dạng "sk-...ab12" — giữ 4 ký tự cuối để Admin nhận ra key nào mà
    không lộ giá trị đầy đủ."""
    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:3]}...{raw[-4:]}"

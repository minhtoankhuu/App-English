from cryptography.fernet import Fernet, InvalidToken

from app.services import crypto


def test_encrypt_decrypt_roundtrip():
    token = crypto.encrypt_api_key("sk-test-1234567890")
    assert crypto.decrypt_api_key(token) == "sk-test-1234567890"


def test_encrypted_value_is_not_plaintext():
    token = crypto.encrypt_api_key("sk-test-1234567890")
    assert b"sk-test-1234567890" not in token


def test_different_key_cannot_decrypt():
    token = crypto.encrypt_api_key("sk-test-1234567890")
    other = Fernet(Fernet.generate_key())
    try:
        other.decrypt(token)
        assert False, "phải raise InvalidToken khi dùng sai key"
    except InvalidToken:
        pass


def test_mask_api_key_keeps_last_four_chars():
    assert crypto.mask_api_key("sk-proj-abcd1234") == "sk-...1234"


def test_mask_api_key_short_value_fully_masked():
    assert crypto.mask_api_key("ab") == "**"

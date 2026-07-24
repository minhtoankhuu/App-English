from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Mặc định trỏ ra Knowledge_Base/ ở gốc repo khi chạy bằng Python host (không qua
# container). Trong container, biến môi trường KNOWLEDGE_BASE_DIR trỏ vào volume
# mount riêng (xem docker-compose.yml) vì cấu trúc thư mục khác nhau.
_DEFAULT_KNOWLEDGE_BASE_DIR = str(Path(__file__).resolve().parents[2] / "Knowledge_Base")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft"
    knowledge_base_dir: str = _DEFAULT_KNOWLEDGE_BASE_DIR
    session_secret: str = "dev-secret-change-me"
    session_cookie_name: str = "examcraft_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 ngày
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"
    daily_generation_limit: int = Field(default=10, gt=0)

    # Fernet key (32 byte urlsafe-base64, vd Fernet.generate_key()) mã hóa API key
    # provider AI trước khi lưu DB (app/services/crypto.py) — đổi ngay ở production.
    ai_config_encryption_key: str = "RzeAmI7PNoRVVxdZyyEaHC1Asjbmt2Af7jWpUvhRdug="

    # Chỉ dùng để seed tài khoản Admin đầu tiên; đổi ngay ở môi trường thật.
    # Lưu ý: không dùng TLD đặc biệt (.local/.test/.example/.invalid) vì
    # pydantic EmailStr (qua email-validator) từ chối theo RFC 6761.
    seed_admin_email: str = "admin@examcraft.dev"
    seed_admin_password: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()

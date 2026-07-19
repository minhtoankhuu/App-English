from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://examcraft:examcraft@localhost:5432/examcraft"
    session_secret: str = "dev-secret-change-me"
    session_cookie_name: str = "examcraft_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 ngày
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"
    daily_generation_limit: int = Field(default=10, gt=0)

    # Chỉ dùng để seed tài khoản Admin đầu tiên; đổi ngay ở môi trường thật.
    # Lưu ý: không dùng TLD đặc biệt (.local/.test/.example/.invalid) vì
    # pydantic EmailStr (qua email-validator) từ chối theo RFC 6761.
    seed_admin_email: str = "admin@examcraft.dev"
    seed_admin_password: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""
Ilova konfiguratsiyasi. Barcha sozlamalar .env faylidan o'qiladi.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/zavod_health"

    # JWT
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 soat (bitta ish smenasi)

    class Config:
        env_file = ".env"


settings = Settings()

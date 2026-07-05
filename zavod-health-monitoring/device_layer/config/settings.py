"""
Device Layer konfiguratsiyasi.

Barcha sozlamalar .env faylidan o'qiladi. Bu servisning yagona
"single source of truth" joyi — boshqa hech bir modulda
os.getenv() to'g'ridan-to'g'ri chaqirilmasligi kerak. Agar yangi
sozlama kerak bo'lsa, avval shu yerga qo'shiladi.

Talab qilinadigan kutubxona: pydantic-settings
    pip install pydantic-settings
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Dahua qurilmasi
    # ------------------------------------------------------------------
    dahua_host: str = Field(..., description="Dahua qurilmasining IP manzili yoki hostnamesi")
    dahua_port: int = Field(default=80, ge=1, le=65535)
    dahua_username: str = Field(..., description="Qurilma login")
    dahua_password: str = Field(..., description="Qurilma paroli")
    dahua_use_https: bool = Field(default=False)
    dahua_timeout_seconds: float = Field(default=5.0, gt=0)

    # ------------------------------------------------------------------
    # Backend (asosiy FastAPI backend)
    # ------------------------------------------------------------------
    backend_base_url: str = Field(..., description="Backendning bazaviy URL manzili")
    backend_api_key: str = Field(..., description="Backend bilan ichki autentifikatsiya uchun kalit")
    backend_timeout_seconds: float = Field(default=5.0, gt=0)

    # ------------------------------------------------------------------
    # Qayta urinish (retry) siyosati — utils/retry.py shu qiymatlarni ishlatadi
    # ------------------------------------------------------------------
    retry_max_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_base_seconds: float = Field(default=1.0, gt=0)
    retry_backoff_max_seconds: float = Field(default=30.0, gt=0)

    # ------------------------------------------------------------------
    # Navbat (queue) — event yo'qolmasligi uchun
    # ------------------------------------------------------------------
    queue_backend: Literal["memory", "redis"] = Field(default="memory")
    redis_url: str | None = Field(default=None)
    queue_max_size: int = Field(default=1000, ge=1)

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_dir: str = Field(default="logs")

    # ------------------------------------------------------------------
    # Healthcheck
    # ------------------------------------------------------------------
    healthcheck_interval_seconds: int = Field(default=30, ge=5)

    @model_validator(mode="after")
    def _validate_redis_required_when_selected(self) -> "Settings":
        """queue_backend='redis' tanlansa, redis_url majburiy bo'lishi kerak."""
        if self.queue_backend == "redis" and not self.redis_url:
            raise ValueError(
                "queue_backend='redis' tanlangan, lekin REDIS_URL berilmagan (.env fayliga qo'shing)"
            )
        return self

    def dahua_base_url(self) -> str:
        """Dahua qurilmasiga so'rov yuborish uchun to'liq bazaviy URL."""
        scheme = "https" if self.dahua_use_https else "http"
        return f"{scheme}://{self.dahua_host}:{self.dahua_port}"


@lru_cache
def get_settings() -> Settings:
    """
    Settings obyektini butun ilova davomida bitta marta yaratadi (singleton).

    Foydalanish:
        from config.settings import get_settings
        settings = get_settings()
    """
    return Settings()
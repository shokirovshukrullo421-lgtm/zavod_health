"""
Bir nechta Dahua qurilmasining sozlamalarini (host, login, parol)
boshqarish.

MUHIM: har bir qurilmaning login/paroli har xil bo'lgani uchun, ular
config/settings.py'dagi global .env faylida emas, balki alohida JSON
faylda (devices.json) saqlanadi. Bu fayl parollarni ochiq matnda
saqlagani uchun **.gitignore'ga albatta qo'shilishi kerak**
(.env fayli qanday himoyalangan bo'lsa, xuddi shunday).

devices.json formati:
[
    {
        "device_code": "DEV-001",
        "host": "192.168.1.50",
        "port": 80,
        "use_https": false,
        "username": "admin",
        "password": "secret123"
    },
    {
        "device_code": "DEV-002",
        "host": "192.168.1.51",
        "username": "admin2",
        "password": "secret456"
    }
]

("port", "use_https", "timeout_seconds" ixtiyoriy — berilmasa default
qiymat ishlatiladi.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class DeviceConfigError(Exception):
    """devices.json topilmasa yoki formati noto'g'ri bo'lsa qo'zg'atiladi."""


@dataclass(frozen=True)
class DeviceCredentials:
    """Bitta qurilmaning ulanish ma'lumotlari."""

    device_code: str
    host: str
    username: str
    password: str
    port: int = 80
    use_https: bool = False
    timeout_seconds: float = 5.0

    def base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"


class DeviceRegistry:
    """devices.json'dan yuklangan device_code -> DeviceCredentials xaritasi."""

    def __init__(self, credentials: dict[str, DeviceCredentials]) -> None:
        self._credentials = credentials

    def get(self, device_code: str) -> DeviceCredentials:
        """
        Berilgan device_code uchun ulanish ma'lumotini qaytaradi.

        Raises:
            KeyError: device_code ro'yxatda yo'q bo'lsa. api/routes.py
                buni ushlab 404 qaytarishi kerak — noma'lum qurilmadan
                so'rov kelishi noto'g'ri sozlash yoki suiiste'mol qilishga
                urinish belgisi bo'lishi mumkin.
        """
        try:
            return self._credentials[device_code]
        except KeyError as exc:
            raise KeyError(f"Noma'lum device_code: {device_code!r}") from exc

    def all_device_codes(self) -> list[str]:
        return list(self._credentials.keys())

    @classmethod
    def from_json_file(cls, path: str | Path) -> DeviceRegistry:
        path = Path(path)
        if not path.exists():
            raise DeviceConfigError(f"devices fayli topilmadi: {path}")

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DeviceConfigError(f"devices fayli to'g'ri JSON emas: {path} ({exc})") from exc

        if not isinstance(raw, list):
            raise DeviceConfigError(f"devices fayli ro'yxat (list) bo'lishi kerak: {path}")

        credentials: dict[str, DeviceCredentials] = {}
        for i, item in enumerate(raw):
            try:
                cred = DeviceCredentials(
                    device_code=item["device_code"],
                    host=item["host"],
                    username=item["username"],
                    password=item["password"],
                    port=item.get("port", 80),
                    use_https=item.get("use_https", False),
                    timeout_seconds=item.get("timeout_seconds", 5.0),
                )
            except KeyError as exc:
                raise DeviceConfigError(f"devices.json[{i}]: majburiy maydon yo'q: {exc}") from exc

            if cred.device_code in credentials:
                raise DeviceConfigError(
                    f"devices.json'da takrorlangan device_code: {cred.device_code!r}"
                )
            credentials[cred.device_code] = cred

        if not credentials:
            raise DeviceConfigError(f"devices.json bo'sh: {path}")

        return cls(credentials)


@lru_cache
def get_device_registry(devices_file: str = "devices.json") -> DeviceRegistry:
    """
    Butun ilova davomida bitta marta yuklanadi (singleton, get_settings
    kabi). Test yoki boshqa fayl yo'lini ishlatish uchun:
        get_device_registry.cache_clear()
        get_device_registry("path/to/other.json")
    """
    return DeviceRegistry.from_json_file(devices_file)
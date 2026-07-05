"""
Qurilma (Dahua) bilan bog'liq xatoliklar ierarxiyasi.

QOIDA: connectors/parsers ichida hech qachon requests.RequestException,
KeyError, json.JSONDecodeError kabi xom kutubxona xatoliklari
tashqariga "raise" qilinmaydi. Ular ushbu maxsus sinflarga
o'rab (wrap) qilinib qayta chiqariladi. Shunda yuqori qatlamlar
(masalan health/healthcheck.py yoki logging) faqat shu bazaviy
sinflarni bilishi kifoya qiladi — qaysi kutubxona ishlatilganidan
qat'i nazar.

Foydalanish namunasi (connectors/dahua.py ichida):

    try:
        response = requests.get(url, auth=..., timeout=settings.dahua_timeout_seconds)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise DeviceTimeoutError(
            "Dahua qurilmasi javob bermadi", device_code=device_code
        ) from exc
    except requests.ConnectionError as exc:
        raise DeviceConnectionError(
            "Dahua qurilmasiga ulanib bo'lmadi", device_code=device_code
        ) from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 403):
            raise DeviceAuthError(
                "Dahua login/parol noto'g'ri", device_code=device_code
            ) from exc
        raise DeviceResponseError(
            f"Dahua qurilmasi xato status qaytardi: {status}",
            device_code=device_code, status_code=status,
        ) from exc
"""

from __future__ import annotations


class DeviceError(Exception):
    """Barcha qurilma bilan bog'liq xatoliklar uchun bazaviy sinf."""

    def __init__(self, message: str, *, device_code: str | None = None) -> None:
        self.device_code = device_code
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        return f"[device={self.device_code}] {base}" if self.device_code else base


class DeviceConnectionError(DeviceError):
    """Qurilmaga tarmoq orqali ulanib bo'lmadi (offline, DNS, tarmoq xatosi)."""


class DeviceTimeoutError(DeviceConnectionError):
    """Qurilma belgilangan vaqt ichida javob bermadi.

    retry.py uchun signal: bu holatda qayta urinish mantiqiy,
    chunki muammo vaqtinchalik bo'lishi mumkin.
    """


class DeviceAuthError(DeviceError):
    """Qurilma login/parol noto'g'ri yoki ruxsat berilmadi (401/403).

    retry.py uchun signal: qayta urinishning ma'nosi yo'q — parol
    o'zgarmasa, natija bir xil bo'ladi. Darhol alert/log qilinishi kerak.
    """


class DeviceResponseError(DeviceError):
    """Qurilma javob berdi, lekin status kod xato (masalan 500, 503)."""

    def __init__(
        self,
        message: str,
        *,
        device_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, device_code=device_code)

    def is_retryable(self) -> bool:
        """5xx — vaqtinchalik server xatosi, qayta urinsa bo'ladi. 4xx — bo'lmaydi."""
        return self.status_code is not None and self.status_code >= 500


class DeviceParseError(DeviceError):
    """Qurilmadan kelgan ma'lumot formati kutilganidan farq qiladi.

    raw_payload saqlanadi — log qilib, keyinchalik nima o'zgarganini
    (masalan Dahua firmware yangilanishi) tekshirish uchun.
    """

    def __init__(
        self,
        message: str,
        *,
        device_code: str | None = None,
        raw_payload: dict | None = None,
    ) -> None:
        self.raw_payload = raw_payload or {}
        super().__init__(message, device_code=device_code)
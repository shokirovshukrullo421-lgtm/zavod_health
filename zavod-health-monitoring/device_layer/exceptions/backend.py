"""
Asosiy backend (FastAPI) bilan bog'liq xatoliklar ierarxiyasi.

Bu xatoliklar services/backend_client.py ichida qo'zg'atiladi va
queue/event_client.py tomonidan ushlanadi: qaysi xatolik turi
kelganiga qarab, event qayta urinish uchun navbatga qaytariladimi
yoki "buzilgan" deb belgilanib chetlatiladimi hal qilinadi.

Umumiy qoida:
    BackendConnectionError / BackendUnavailableError  -> qayta urinish mantiqiy
    BackendValidationError                            -> qayta urinish befoyda
    BackendAuthError                                  -> darhol alert, urinishni to'xtatish
"""

from __future__ import annotations


class BackendError(Exception):
    """Barcha backend bilan bog'liq xatoliklar uchun bazaviy sinf."""

    def __init__(self, message: str, *, event_id: str | None = None) -> None:
        self.event_id = event_id
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        return f"[event={self.event_id}] {base}" if self.event_id else base


class BackendConnectionError(BackendError):
    """Backendga tarmoq orqali ulanib bo'lmadi. Qayta urinish tavsiya etiladi."""


class BackendTimeoutError(BackendConnectionError):
    """Backend belgilangan vaqt ichida javob bermadi."""


class BackendAuthError(BackendError):
    """API key noto'g'ri yoki ruxsat berilmagan (401/403).

    Qayta urinishning ma'nosi yo'q — sozlash muammosi, darhol
    log/alert qilinishi va operator xabardor bo'lishi kerak.
    """


class BackendUnavailableError(BackendConnectionError):
    """Backend vaqtincha ishlamayapti (503) yoki ortiqcha yuklangan (429).

    Agar backend `Retry-After` header qaytarsa, shu yerda saqlanadi —
    queue/event_client.py qayta urinishni shuncha vaqtdan keyin rejalashtiradi.
    """

    def __init__(
        self,
        message: str,
        *,
        event_id: str | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message, event_id=event_id)


class BackendValidationError(BackendError):
    """
    Backend ma'lumotni rad etdi (422) — masalan employee_external_id
    topilmadi yoki maydon formati noto'g'ri.

    MUHIM: bu holatda qayta urinishning ma'nosi yo'q, chunki
    ma'lumotning o'zi noto'g'ri — qayta yuborilsa ham natija bir xil
    bo'ladi. queue/event_client.py bunday event'larni "dead letter"
    holatiga o'tkazishi kerak, cheksiz qayta urinish emas.
    """

    def __init__(
        self,
        message: str,
        *,
        event_id: str | None = None,
        validation_errors: list[dict] | None = None,
    ) -> None:
        self.validation_errors = validation_errors or []
        super().__init__(message, event_id=event_id)
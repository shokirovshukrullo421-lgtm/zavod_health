"""
Device Layer ichida ishlatiladigan ma'lumot modellari (Pydantic v2).

MUHIM: bu modellar DB jadvallarining o'zi emas — ular "qurilmadan
kelgan ma'lumot qanday tozalanib, backend'ga qanday shaklda
yuborilishi kerak" degan shartnomani belgilaydi.

Moslik (db/schema.sql bilan):
    RecognizedEvent   -> access_events   (auth_method, temperature, mask_on)
    UnrecognizedEvent -> unrecognized_attempts (device_id, note)

Eslatma: schema.sql'da employee_id INTEGER FK. Lekin device_layer
xodimning ichki DB ID'sini bilmaydi — qurilma faqat o'zining
ichki identifikatorini (masalan Dahua UserID/karta raqami) beradi.
Shu sabab bu yerda `employee_external_id` ishlatiladi; xodimni
DB'dagi employee_id bilan bog'lash (mapping) backend tomonida,
`routers/device.py`da amalga oshiriladi.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# schema.sql: access_events.temperature NUMERIC(4,1)
# Jismoniy mumkin bo'lgan (inson tanasi) oraliq bilan cheklaymiz —
# qurilma xatosi yoki sensor nosozligi tufayli kelgan absurd
# qiymatlarni (masalan 0 yoki 90) erta bosqichda ushlab qolish uchun.
MIN_VALID_TEMPERATURE = Decimal("30.0")
MAX_VALID_TEMPERATURE = Decimal("45.0")


class AuthMethod(str, Enum):
    """schema.sql: access_events.auth_method CHECK constraint bilan bir xil."""

    FACE = "face"
    FINGERPRINT = "fingerprint"


class EventType(str, Enum):
    """Qurilma xodimni tanidimi yoki yo'qmi — qaysi jadvalga borishini belgilaydi."""

    RECOGNIZED = "recognized"
    UNRECOGNIZED = "unrecognized"


class RawDahuaPayload(BaseModel):
    """
    connectors/dahua.py qurilmadan olgan xom ma'lumotni shu konvertga soladi.

    parsers/dahua_parser.py keyin `raw_body`ni o'qib, RecognizedEvent
    yoki UnrecognizedEvent'ga aylantiradi. Xom formatni saqlab qolish
    muhim — parse xato bersa ham, log/debug uchun asl ma'lumot yo'qolmaydi.
    """

    device_serial: str = Field(..., min_length=1)
    raw_body: dict = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=datetime.utcnow)


class DeviceEventBase(BaseModel):
    """RecognizedEvent va UnrecognizedEvent uchun umumiy maydonlar."""

    device_code: str = Field(..., min_length=1, description="devices.device_code bilan mos")
    scanned_at: datetime
    event_type: EventType

    @field_validator("scanned_at")
    @classmethod
    def scanned_at_not_in_future(cls, v: datetime) -> datetime:
        # Qurilma soati backend/serverdan bir necha soniya farq qilishi normal,
        # lekin soatlab kelajakdagi vaqt — qurilma soati noto'g'ri sozlangani
        # yoki parse xatosi belgisi.
        from datetime import timedelta

        now = datetime.utcnow()
        if v > now + timedelta(minutes=5):
            raise ValueError(
                f"scanned_at kelajakda: {v.isoformat()} (server vaqti: {now.isoformat()})"
            )
        return v


class RecognizedEvent(DeviceEventBase):
    """
    Qurilma xodimni muvaffaqiyatli tanigan holat.

    access_events jadvaliga to'g'ridan-to'g'ri mos keladi (status,
    reviewed_by, reviewed_at, doctor_note maydonlari bundan mustasno —
    ular shifokor tomonidan portal orqali to'ldiriladi, device_layer
    ularga tegmaydi).
    """

    event_type: EventType = EventType.RECOGNIZED
    employee_external_id: str = Field(
        ..., min_length=1, description="Qurilmadagi ichki ID (Dahua UserID/karta raqami)"
    )
    auth_method: AuthMethod
    temperature: Decimal | None = Field(default=None)
    mask_on: bool | None = None

    @field_validator("temperature", mode="before")
    @classmethod
    def parse_temperature(cls, v):
        """Qurilma harorat ba'zan '36,6' yoki bo'sh satr shaklida yuborishi mumkin."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v = v.replace(",", ".")
        try:
            return Decimal(str(v))
        except InvalidOperation as exc:
            raise ValueError(f"temperature raqamga aylantirilmadi: {v!r}") from exc

    @field_validator("temperature")
    @classmethod
    def validate_temperature_range(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        v = v.quantize(Decimal("0.1"))
        if not (MIN_VALID_TEMPERATURE <= v <= MAX_VALID_TEMPERATURE):
            raise ValueError(
                f"temperature jismoniy oraliqdan tashqarida: {v} "
                f"(kutilgan: {MIN_VALID_TEMPERATURE}-{MAX_VALID_TEMPERATURE})"
            )
        return v


class UnrecognizedEvent(DeviceEventBase):
    """
    Qurilma xodimni tanimagan holat.

    unrecognized_attempts jadvaliga mos keladi.
    """

    event_type: EventType = EventType.UNRECOGNIZED
    note: str | None = Field(default=None, max_length=500)


# services/event_service.py va queue/event_client.py shu union tipni ishlatadi
DeviceEvent = RecognizedEvent | UnrecognizedEvent
"""
Dahua qurilmasidan JSON formatida kelgan xom ma'lumotni
models/event.py'dagi RecognizedEvent/UnrecognizedEvent'ga aylantiradi.

****************************************************************
MUHIM: pastdagi FIELD MAPPING qismi — bu qurilmangizning HAQIQIY
JSON payload'iga qarab albatta tekshirilishi va moslashtirilishi
kerak. Bu yerda Dahua kirish nazorati (access control)
qurilmalarida eng ko'p uchraydigan formatga asoslanilgan, lekin
firmware versiyasiga qarab maydon nomlari farq qilishi mumkin.

TAVSIYA: birinchi real webhook so'rovi kelganda, uni
api/routes.py ichida debug levelda to'liq log qiling
(logger.debug("Dahua raw payload: %s", raw_body)) va shu yerdagi
_FIELD nomlarini/_AUTH_METHOD_MAP qiymatlarini moslang.
****************************************************************
"""

from __future__ import annotations

import logging
from datetime import datetime

from exceptions.device import DeviceParseError
from models.event import AuthMethod, DeviceEvent, RecognizedEvent, UnrecognizedEvent

logger = logging.getLogger(__name__)

# Taxminiy Dahua struktura:
#   {
#       "Code": "AccessControl",
#       "Data": {
#           "UserID": "1024",
#           "Status": "Success",        # yoki "Failure" / "NoMatch"
#           "Method": "Face",           # yoki "Fingerprint"
#           "Temperature": 36.5,        # ixtiyoriy
#           "IsWearingMask": true,      # ixtiyoriy
#           "Time": "2026-07-05 12:34:56"
#       }
#   }

# "Method" maydonidagi qiymatlarni bizning AuthMethod enum'ga
# moslashtirish uchun lug'at. Real payload qiymati boshqacha
# yozilsa (masalan "FaceRecognition" o'rniga boshqa so'z),
# shu yerga qo'shing.
_AUTH_METHOD_MAP: dict[str, AuthMethod] = {
    "face": AuthMethod.FACE,
    "facerecognition": AuthMethod.FACE,
    "fingerprint": AuthMethod.FINGERPRINT,
    "fingerprintrecognition": AuthMethod.FINGERPRINT,
}

# "Status" maydonida qaysi qiymatlar "xodim tanilmadi" degani.
_UNRECOGNIZED_STATUSES = {"failure", "nomatch", "notallowed", "unknown"}


def parse_dahua_event(*, raw_body: dict, device_code: str) -> DeviceEvent:
    """
    Dahua'dan kelgan JSON body'ni DeviceEvent'ga (Recognized/Unrecognized)
    aylantiradi.

    Args:
        raw_body: FastAPI endpoint `request.json()` orqali olgan xom dict.
        device_code: qaysi qurilmadan kelgani (api/routes.py aniqlaydi,
            masalan URL path'dagi identifikator orqali).

    Raises:
        DeviceParseError: struktura kutilganidan farq qilsa, majburiy
            maydon yo'q bo'lsa yoki qiymatlar validatsiyadan o'tmasa.
            api/routes.py buni ushlab, mos HTTP status (masalan 400)
            bilan javob qaytarishi kerak.
    """
    try:
        data = raw_body["Data"]
        if not isinstance(data, dict):
            raise TypeError("'Data' dict emas")
    except (KeyError, TypeError) as exc:
        raise DeviceParseError(
            "'Data' maydoni topilmadi yoki noto'g'ri formatda",
            device_code=device_code,
            raw_payload=raw_body,
        ) from exc

    scanned_at = _parse_timestamp(
        data.get("Time"), device_code=device_code, raw_payload=raw_body
    )
    status_raw = str(data.get("Status", "")).strip().lower()

    # Tanilmagan urinish: status mos kelsa YOKI UserID umuman bo'lmasa
    if status_raw in _UNRECOGNIZED_STATUSES or not data.get("UserID"):
        logger.info(
            "device=%s: tanilmagan urinish (status=%r)", device_code, data.get("Status")
        )
        return UnrecognizedEvent(
            device_code=device_code,
            scanned_at=scanned_at,
            note=f"status={data.get('Status')!r}",
        )

    method_raw = str(data.get("Method", "")).strip().lower()
    auth_method = _AUTH_METHOD_MAP.get(method_raw)
    if auth_method is None:
        raise DeviceParseError(
            f"Noma'lum auth method: {data.get('Method')!r} "
            f"(_AUTH_METHOD_MAP'ga qo'shish kerak bo'lishi mumkin)",
            device_code=device_code,
            raw_payload=raw_body,
        )

    try:
        return RecognizedEvent(
            device_code=device_code,
            scanned_at=scanned_at,
            employee_external_id=str(data["UserID"]),
            auth_method=auth_method,
            temperature=data.get("Temperature"),
            mask_on=data.get("IsWearingMask"),
        )
    except Exception as exc:
        # models/event.py'dagi Pydantic validatsiyasi ishlamasa
        # (masalan harorat jismoniy oraliqdan tashqarida), shu yerda
        # tutib DeviceParseError'ga o'raymiz — yuqori qatlam
        # (api/routes.py) faqat bitta xatolik turini bilishi kifoya.
        raise DeviceParseError(
            f"Event validatsiyadan o'tmadi: {exc}",
            device_code=device_code,
            raw_payload=raw_body,
        ) from exc


def _parse_timestamp(raw_time: str | None, *, device_code: str, raw_payload: dict) -> datetime:
    """Dahua odatda 'YYYY-MM-DD HH:MM:SS' formatida vaqt yuboradi."""
    if not raw_time:
        raise DeviceParseError(
            "'Time' maydoni topilmadi", device_code=device_code, raw_payload=raw_payload
        )
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw_time, fmt)
        except ValueError:
            continue
    raise DeviceParseError(
        f"'Time' formatini tushunib bo'lmadi: {raw_time!r}",
        device_code=device_code,
        raw_payload=raw_payload,
    )
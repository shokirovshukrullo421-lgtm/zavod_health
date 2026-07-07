"""
Umumiy validatsiya yordamchi funksiyalari.

models/event.py'dagi Pydantic validatsiyasidan farqli o'laroq, bu
yerdagi funksiyalar hech qanday modelga bog'liq emas — config
yuklashda yoki connector/parser ichida erta tekshiruv qilish uchun
ishlatiladi.
"""

from __future__ import annotations

import re

# device_code URL path'da ishlatiladi (api/routes.py), shuning uchun
# faqat harf/raqam/tire/pastki chiziqqa ruxsat beramiz — boshqa
# belgilar (masalan '/', '..') xavfsizlik muammosi tug'dirishi mumkin.
_DEVICE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


def is_valid_device_code(device_code: str) -> bool:
    """device_code formati xavfsiz va kutilgan shaklda ekanini tekshiradi."""
    return bool(_DEVICE_CODE_PATTERN.match(device_code))


def is_valid_host(value: str) -> bool:
    """Juda oddiy tekshiruv: host/IP bo'sh emas va probel yo'q."""
    return bool(value) and " " not in value


def truncate_for_log(value: str, *, max_length: int = 300) -> str:
    """
    Log fayllari haddan tashqari katta bo'lib ketmasligi uchun uzun
    qatorlarni (masalan xom JSON payload) qisqartiradi.
    """
    if len(value) <= max_length:
        return value
    return value[:max_length] + f"...[{len(value) - max_length} ta belgi qisqartirildi]"
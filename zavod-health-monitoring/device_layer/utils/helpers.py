"""
Device Layer'ning turli qismlarida ishlatiladigan umumiy yordamchi
funksiyalar.
"""

from __future__ import annotations

from typing import Any


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """
    Ichma-ich dict'dan xavfsiz qiymat oladi.

        safe_get(payload, "Data", "UserID", default="")

    Har qanday oraliq qiymat dict bo'lmasa yoki kalit topilmasa,
    exception ko'tarmasdan default qaytaradi. parsers/dahua_parser.py
    kabi ishonchsiz (qurilmadan kelgan) xom ma'lumot bilan ishlashda
    foydali.
    """
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def mask_secret(value: str, *, visible_chars: int = 2) -> str:
    """
    Parol/API-key kabi maxfiy qiymatlarni log qilishda to'liq
    ko'rsatmaslik uchun.

        mask_secret("secret123") -> "se*******"
    """
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
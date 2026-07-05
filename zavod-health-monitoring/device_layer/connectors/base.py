"""
Barcha qurilma connector'lari uchun abstrakt shartnoma (interfeys).

MUHIM: bu loyihada qurilmalar hodisalarni (event) o'zlari webhook
(HTTP callback) orqali device_layer'ga yuboradi — device_layer ularni
"poll" qilmaydi. Shu sababli connector'ning vazifasi odatdagidan farq
qiladi:

    1. Kiruvchi webhook so'rovi haqiqatan ham ishonchli qurilmadan
       kelganini tasdiqlash (authenticate_incoming_request).
       Event'ning o'zini PARSE qilish bu yerda emas — bu
       parsers/dahua_parser.py vazifasi.
    2. Qurilmaning o'zi bilan chiquvchi (outbound) aloqa — health-check
       va qurilma ma'lumotini (serial, model) olish.

Har bir yangi brend (masalan Hikvision) shu interfeysni implement
qiladi; api/routes.py va health/healthcheck.py connector'ning qaysi
brend ekanini bilishi shart emas — faqat shu shartnoma bilan ishlaydi.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceStatus:
    """get_device_status() natijasi — health/healthcheck.py shuni ishlatadi."""

    is_online: bool
    device_code: str
    detail: str | None = None


@dataclass(frozen=True)
class DeviceInfo:
    """get_device_info() natijasi — qurilma o'zi haqida bergan ma'lumot."""

    device_code: str
    serial_number: str
    model: str | None = None
    firmware_version: str | None = None


class BaseDeviceConnector(ABC):
    """
    Har bir brend uchun connector shu klassdan meros oladi.

    __init__ argumentlari brendga xos bo'lgani uchun bazaviy klassda
    belgilanmagan — har bir implementatsiya o'zi config'dan kerakli
    narsalarni oladi.
    """

    @abstractmethod
    def authenticate_incoming_request(
        self, *, headers: dict[str, str], remote_addr: str
    ) -> bool:
        """
        Webhook orqali kelgan so'rov haqiqatan ham ushbu qurilmadan
        kelayotganini tekshiradi (masalan Basic Auth yoki IP whitelist
        orqali).

        api/routes.py har bir kiruvchi so'rovda shu metodni chaqiradi —
        False qaytsa, so'rov 401 bilan rad etilishi kerak.
        """
        raise NotImplementedError

    @abstractmethod
    def get_device_status(self) -> DeviceStatus:
        """
        Qurilmaga chiquvchi so'rov yuborib, u onlaynligini tekshiradi.
        health/healthcheck.py davriy ravishda shu metodni chaqiradi.

        Eslatma: tarmoq xatosi bo'lsa ham exception emas, balki
        is_online=False bilan DeviceStatus qaytarilishi kutiladi —
        health-check uchun bu "kutilgan" holat, favqulodda emas.
        """
        raise NotImplementedError

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """
        Qurilmaning o'zidan seriya raqami/model kabi ma'lumotni oladi.
        Odatda ilova ishga tushganda bir marta chaqiriladi — qurilma
        seriya raqamini config'dagi device_code bilan solishtirish uchun.
        """
        raise NotImplementedError
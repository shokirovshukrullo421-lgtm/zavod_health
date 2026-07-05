"""
Dahua qurilmalari uchun connector implementatsiyasi.

MUHIM: bu loyihada Dahua qurilmasi event'larni o'zi webhook (HTTP
callback) orqali device_layer'ga (api/routes.py'ga) yuboradi. Shu
sababli bu klass ikki xil yo'nalishda ishlaydi:

    1. INBOUND (qurilma -> biz): faqat kelgan so'rovni autentifikatsiya
       qilish. Haqiqiy event ma'lumotini PARSE qilish
       parsers/dahua_parser.py vazifasi — bu yerda emas.
    2. OUTBOUND (biz -> qurilma): health-check va qurilma ma'lumotini
       olish uchun Dahua CGI API'ga so'rov yuborish.

Dahua CGI API odatda HTTP Digest Authentication ishlatadi.
Talab qilinadigan kutubxona: requests
    pip install requests
"""

from __future__ import annotations

import base64
import logging

import requests
from requests.auth import HTTPDigestAuth

from config.devices import DeviceCredentials
from connectors.base import BaseDeviceConnector, DeviceInfo, DeviceStatus
from exceptions.device import (
    DeviceAuthError,
    DeviceConnectionError,
    DeviceParseError,
    DeviceResponseError,
    DeviceTimeoutError,
)

logger = logging.getLogger(__name__)


class DahuaConnector(BaseDeviceConnector):
    """
    Bitta Dahua qurilmasi bilan ishlaydigan connector.

    Har bir qurilmaning o'z login/paroli bo'lgani uchun, connector
    global Settings emas, balki shu qurilmaga tegishli DeviceCredentials
    obyektini oladi (config/devices.py'dagi DeviceRegistry orqali).

    Foydalanish:
        credentials = get_device_registry().get("DEV-001")
        connector = DahuaConnector(credentials=credentials)
    """

    def __init__(self, *, credentials: DeviceCredentials) -> None:
        self._credentials = credentials
        self._device_code = credentials.device_code
        self._base_url = credentials.base_url()
        self._auth = HTTPDigestAuth(credentials.username, credentials.password)
        self._timeout = credentials.timeout_seconds

    # ------------------------------------------------------------------
    # INBOUND: webhook so'rovini tasdiqlash
    # ------------------------------------------------------------------
    def authenticate_incoming_request(
        self, *, headers: dict[str, str], remote_addr: str
    ) -> bool:
        """
        Dahua qurilmasi callback yuborayotganda odatda Basic Auth
        header qo'shadi (qurilmaning "Alarm Server" sozlamalarida
        kiritilgan login/parol bilan). Shu yerda solishtiramiz.

        Eslatma: agar qo'shimcha IP whitelist kerak bo'lsa (masalan
        qurilma faqat ma'lum ichki tarmoq oralig'idan kelishi kerak
        bo'lsa), remote_addr'ni config'dagi ruxsat etilgan ro'yxat
        bilan solishtirish shu yerga qo'shiladi.
        """
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            logger.warning(
                "device=%s: webhook so'rovida Basic Auth header topilmadi (remote=%s)",
                self._device_code, remote_addr,
            )
            return False

        try:
            encoded = auth_header.removeprefix("Basic ").strip()
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, _, password = decoded.partition(":")
        except Exception:
            logger.warning(
                "device=%s: Authorization header decode qilinmadi (remote=%s)",
                self._device_code, remote_addr,
            )
            return False

        is_valid = (
            username == self._credentials.username
            and password == self._credentials.password
        )
        if not is_valid:
            logger.warning(
                "device=%s: webhook autentifikatsiyasi muvaffaqiyatsiz (remote=%s)",
                self._device_code, remote_addr,
            )
        return is_valid

    # ------------------------------------------------------------------
    # OUTBOUND: health-check
    # ------------------------------------------------------------------
    def get_device_status(self) -> DeviceStatus:
        """
        Dahua CGI orqali qurilma holatini tekshiradi.
        Endpoint: /cgi-bin/magicBox.cgi?action=getDeviceType
        (deyarli barcha Dahua modellarida mavjud bo'lgani uchun
        umumiy health-check uchun qulay).

        Tarmoq xatosi is_online=False bilan qaytariladi (exception
        emas) — health-check uchun bu kutilgan holat.
        """
        url = f"{self._base_url}/cgi-bin/magicBox.cgi"
        try:
            response = requests.get(
                url,
                params={"action": "getDeviceType"},
                auth=self._auth,
                timeout=self._timeout,
            )
        except requests.Timeout:
            return DeviceStatus(
                is_online=False, device_code=self._device_code, detail="Timeout"
            )
        except requests.ConnectionError as exc:
            return DeviceStatus(
                is_online=False,
                device_code=self._device_code,
                detail=f"Ulanib bo'lmadi: {exc}",
            )

        if response.status_code in (401, 403):
            raise DeviceAuthError(
                "Health-check: login/parol noto'g'ri", device_code=self._device_code
            )
        if not response.ok:
            return DeviceStatus(
                is_online=False,
                device_code=self._device_code,
                detail=f"Kutilmagan status kod: {response.status_code}",
            )

        return DeviceStatus(
            is_online=True, device_code=self._device_code, detail=response.text.strip()
        )

    def get_device_info(self) -> DeviceInfo:
        """
        Qurilmaning seriya raqami va modelini oladi.
        Endpoint'lar: getSerialNo va getDeviceType.

        Health-check'dan farqli o'laroq, bu yerda tarmoq xatosi
        exception sifatida qaytariladi — chunki bu odatda ilova
        ishga tushishida bir marta chaqiriladi va muvaffaqiyatsizlik
        darhol ma'lum bo'lishi kerak (jim qolib ketmasligi uchun).
        """
        try:
            serial_resp = requests.get(
                f"{self._base_url}/cgi-bin/magicBox.cgi",
                params={"action": "getSerialNo"},
                auth=self._auth,
                timeout=self._timeout,
            )
            model_resp = requests.get(
                f"{self._base_url}/cgi-bin/magicBox.cgi",
                params={"action": "getDeviceType"},
                auth=self._auth,
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise DeviceTimeoutError(
                "get_device_info: qurilma javob bermadi", device_code=self._device_code
            ) from exc
        except requests.ConnectionError as exc:
            raise DeviceConnectionError(
                f"get_device_info: ulanib bo'lmadi ({exc})", device_code=self._device_code
            ) from exc

        for resp in (serial_resp, model_resp):
            if resp.status_code in (401, 403):
                raise DeviceAuthError(
                    "get_device_info: login/parol noto'g'ri", device_code=self._device_code
                )
            if not resp.ok:
                raise DeviceResponseError(
                    f"get_device_info: kutilmagan status kod {resp.status_code}",
                    device_code=self._device_code,
                    status_code=resp.status_code,
                )

        serial = self._extract_cgi_value(serial_resp.text, key="sn")
        model = self._extract_cgi_value(model_resp.text, key="type")

        return DeviceInfo(device_code=self._device_code, serial_number=serial, model=model)

    @staticmethod
    def _extract_cgi_value(raw_text: str, *, key: str) -> str:
        """
        Dahua CGI javobi 'key=value' formatida keladi (masalan 'sn=1234ABCD').
        Format kutilganidan farq qilsa, DeviceParseError qaytariladi —
        bu odatda Dahua firmware o'zgarishi yoki noto'g'ri endpoint
        chaqirilgani belgisi.
        """
        raw_text = raw_text.strip()
        if "=" not in raw_text:
            raise DeviceParseError(
                f"CGI javobini parse qilib bo'lmadi: {raw_text!r}",
                raw_payload={"raw_text": raw_text, "expected_key": key},
            )
        _, _, value = raw_text.partition("=")
        return value.strip()
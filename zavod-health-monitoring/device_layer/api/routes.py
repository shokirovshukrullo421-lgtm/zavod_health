"""
Dahua qurilmalaridan webhook orqali keladigan hodisalarni qabul
qiluvchi endpoint.

URL: POST /webhook/dahua/{device_code}

Har bir fizik qurilma o'zining "Alarm Server" sozlamalarida shu
URL'ga (o'ziga tegishli device_code bilan) so'rov yuborishi kerak,
masalan:
    Qurilma DEV-001 -> POST http://server/webhook/dahua/DEV-001
    Qurilma DEV-002 -> POST http://server/webhook/dahua/DEV-002

Oqim:
    1. device_code bo'yicha DeviceRegistry'dan ulanish ma'lumoti topiladi
    2. DahuaConnector orqali so'rov haqiqatan shu qurilmadan kelganini
       tasdiqlaymiz (Basic Auth)
    3. parsers.parse_dahua_event orqali xom JSON DeviceEvent'ga aylantiriladi
    4. (keyingi bosqich) DeviceEvent services/event_service.py'ga uzatiladi
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from config.devices import DeviceConfigError, get_device_registry
from connectors.dahua import DahuaConnector
from exceptions.device import DeviceParseError
from parsers.dahua_parser import parse_dahua_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["dahua-webhook"])


@router.post("/dahua/{device_code}", status_code=status.HTTP_202_ACCEPTED)
async def receive_dahua_event(device_code: str, request: Request) -> dict:
    """
    Dahua qurilmasidan kelgan bitta hodisani qabul qiladi.

    202 Accepted qaytaradi: "qabul qilindi" degani — event navbatga
    qo'yiladi, backend'ga yuborilishi kutilmaydi. Qurilmaga TEZ javob
    qaytarish muhim — ba'zi Dahua qurilmalari javob kechiksa keyingi
    hodisani yubormay kutib turadi.

    app.state.event_service — app.py'da ilova ishga tushganda
    yaratiladi va shu yerga FastAPI orqali uzatiladi (dependency
    sifatida emas, oddiy app.state orqali, chunki bitta global
    instance yetarli).
    """
    # 1. Qurilma ma'lumotini topish
    try:
        registry = get_device_registry()
    except DeviceConfigError as exc:
        # devices.json o'qib bo'lmadi — bu server sozlash xatosi,
        # qurilmaning aybi emas.
        logger.error("devices.json yuklanmadi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server sozlamasi xato",
        )

    try:
        credentials = registry.get(device_code)
    except KeyError:
        logger.warning("Noma'lum device_code bilan so'rov keldi: %s", device_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Noma'lum qurilma"
        )

    connector = DahuaConnector(credentials=credentials)

    # 2. So'rovni autentifikatsiya qilish
    client_ip = request.client.host if request.client else "unknown"
    is_authentic = connector.authenticate_incoming_request(
        headers=dict(request.headers), remote_addr=client_ip
    )
    if not is_authentic:
        logger.warning(
            "device=%s: autentifikatsiya muvaffaqiyatsiz (remote=%s)",
            device_code, client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autentifikatsiya xato"
        )

    # 3. Body'ni JSON sifatida o'qish
    try:
        raw_body = await request.json()
    except Exception as exc:
        logger.warning("device=%s: body JSON emas (%s)", device_code, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Body JSON emas")

    # 4. Parse qilish
    try:
        event = parse_dahua_event(raw_body=raw_body, device_code=device_code)
    except DeviceParseError as exc:
        # ERROR darajasida log qilinadi — bu Dahua firmware o'zgarishi
        # yoki kutilmagan format belgisi bo'lishi mumkin, e'tibor talab qiladi.
        logger.error("device=%s: parse xatosi: %s", device_code, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.info("device=%s: event qabul qilindi (%s)", device_code, event.event_type.value)

    event_service = request.app.state.event_service
    event_service.handle_event(event)

    return {"status": "accepted", "event_type": event.event_type.value}
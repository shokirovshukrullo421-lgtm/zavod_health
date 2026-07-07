"""
Device Layer ilovasining kirish nuqtasi (entrypoint).

Ishga tushirish:
    uvicorn app:app --host 0.0.0.0 --port 8001

Vazifasi: barcha qismlarni (config, connector, parser, queue, service)
bir joyga yig'ib, FastAPI ilovasini yaratadi. Boshqa hech bir modul
(routes.py, event_service.py va h.k.) global holatni o'zi yaratmaydi —
hammasi shu yerda, ishga tushishda, bir marta quriladi.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as dahua_webhook_router
from config.devices import get_device_registry
from config.settings import get_settings
from eventqueue.event_client import build_event_queue
from health.healthcheck import HealthMonitor
from log_setup.logger import setup_logging
from services.event_service import EventService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ilova ishga tushganda (startup) va to'xtaganda (shutdown)
    bajariladigan amallar — fon oqimlarini (queue worker, health
    monitor) to'g'ri boshlash/to'xtatish uchun muhim.
    """
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir)

    registry = get_device_registry()
    logger.info("Ro'yxatdagi qurilmalar: %s", registry.all_device_codes())

    event_queue = build_event_queue(settings)
    event_queue.start()

    health_monitor = HealthMonitor(settings=settings, registry=registry)
    health_monitor.start()

    # api/routes.py shu yerdan o'qiydi: request.app.state.event_service
    app.state.event_service = EventService(event_queue=event_queue)
    app.state.health_monitor = health_monitor
    app.state.device_registry = registry

    logger.info("Device Layer ishga tushdi")
    yield

    logger.info("Device Layer to'xtatilmoqda...")
    health_monitor.stop()
    event_queue.stop()
    logger.info("Device Layer to'xtatildi")


app = FastAPI(title="Zavod Health Monitoring - Device Layer", lifespan=lifespan)
app.include_router(dahua_webhook_router)


@app.get("/health")
async def health() -> dict:
    """Umumiy ilova va barcha qurilmalar holatini qaytaradi."""
    monitor: HealthMonitor = app.state.health_monitor
    results = monitor.get_last_results()
    return {
        "service": "ok",
        "devices": [
            {"device_code": r.device_code, "is_online": r.is_online, "detail": r.detail}
            for r in results
        ],
    }
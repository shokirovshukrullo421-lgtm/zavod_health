"""
Ro'yxatdagi barcha Dahua qurilmalarining onlayn holatini tekshiradi.

Ikki xil foydalanish rejimi:
    1. Bir martalik tekshiruv: check_all_devices() — masalan /health
       endpoint chaqirilganda.
    2. Davriy fon tekshiruvi: HealthMonitor — ilova ishga tushganda
       start() qilinadi, settings.healthcheck_interval_seconds
       oralig'ida barcha qurilmalarni tekshirib, natijani log qiladi
       va oxirgi natijani xotirada saqlaydi (get_last_results()).
"""

from __future__ import annotations

import logging
import threading

from config.devices import DeviceRegistry
from config.settings import Settings
from connectors.base import DeviceStatus
from connectors.dahua import DahuaConnector
from exceptions.device import DeviceError

logger = logging.getLogger(__name__)


def check_all_devices(registry: DeviceRegistry) -> list[DeviceStatus]:
    """
    Ro'yxatdagi har bir qurilmani ketma-ket tekshiradi.

    MUHIM: bitta qurilma xato bersa ham (masalan tarmoq nosozligi),
    qolgan qurilmalar tekshiruvi davom etadi — bitta qurilmaning
    muammosi butun health-check'ni to'xtatib qo'ymasligi kerak.
    """
    results: list[DeviceStatus] = []
    for device_code in registry.all_device_codes():
        credentials = registry.get(device_code)
        connector = DahuaConnector(credentials=credentials)
        try:
            device_status = connector.get_device_status()
        except DeviceError as exc:
            logger.warning("device=%s: health-check xatosi: %s", device_code, exc)
            device_status = DeviceStatus(
                is_online=False, device_code=device_code, detail=str(exc)
            )
        results.append(device_status)
    return results


class HealthMonitor:
    """
    Fon oqimida (thread) davriy ravishda barcha qurilmalarni tekshiradi.

    Foydalanish:
        monitor = HealthMonitor(settings=settings, registry=registry)
        monitor.start()
        ...
        monitor.get_last_results()   # /health endpoint shu yerdan o'qiydi
        ...
        monitor.stop()
    """

    def __init__(self, *, settings: Settings, registry: DeviceRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_results: list[DeviceStatus] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(
            "Health monitor ishga tushdi (interval=%ss)",
            self._settings.healthcheck_interval_seconds,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Health monitor to'xtatildi")

    def get_last_results(self) -> list[DeviceStatus]:
        with self._lock:
            return list(self._last_results)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            results = check_all_devices(self._registry)
            with self._lock:
                self._last_results = results
            for r in results:
                if not r.is_online:
                    logger.warning("device=%s OFFLINE: %s", r.device_code, r.detail)
            self._stop_event.wait(timeout=self._settings.healthcheck_interval_seconds)
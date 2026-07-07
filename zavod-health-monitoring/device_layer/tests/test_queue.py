"""
eventqueue/event_client.py uchun testlar.

BackendClient haqiqiy tarmoq so'rovi yubormasligi uchun soxta
(fake) backend_client obyekti bilan almashtiriladi.
"""

from __future__ import annotations

import time
from datetime import datetime

from config.settings import Settings
from eventqueue.event_client import InMemoryEventQueue
from exceptions.backend import BackendAuthError, BackendValidationError
from models.event import AuthMethod, RecognizedEvent


def make_settings(**overrides) -> Settings:
    defaults = dict(
        dahua_host="192.168.1.50",
        dahua_username="admin",
        dahua_password="pass",
        backend_base_url="http://localhost:8000",
        backend_api_key="test-key",
        queue_max_size=3,
        retry_backoff_base_seconds=0.01,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def make_event(external_id: str = "1024") -> RecognizedEvent:
    return RecognizedEvent(
        device_code="DEV-001",
        scanned_at=datetime.utcnow(),
        employee_external_id=external_id,
        auth_method=AuthMethod.FACE,
        temperature=36.6,
    )


class FakeBackendClient:
    """BackendClient o'rnini bosadi - haqiqiy tarmoqqa chiqmaydi."""

    def __init__(self, *, fail_with: Exception | None = None, fail_times: int = 0):
        self.sent_events: list = []
        self._fail_with = fail_with
        self._fail_times = fail_times
        self._call_count = 0

    def send_event(self, event) -> None:
        self._call_count += 1
        if self._fail_with is not None and self._call_count <= self._fail_times:
            raise self._fail_with
        self.sent_events.append(event)


def _wait_until(condition, timeout: float = 2.0, interval: float = 0.02) -> None:
    """Fon oqimida ishlaydigan worker natijasini kutish uchun kichik yordamchi."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return
        time.sleep(interval)
    raise AssertionError("Shart berilgan vaqt ichida bajarilmadi")


class TestInMemoryEventQueueHappyPath:
    def test_enqueued_event_gets_sent(self):
        fake_client = FakeBackendClient()
        q = InMemoryEventQueue(settings=make_settings(), backend_client=fake_client)
        q.start()
        try:
            q.enqueue(make_event())
            _wait_until(lambda: len(fake_client.sent_events) == 1)
            assert len(fake_client.sent_events) == 1
        finally:
            q.stop()

    def test_multiple_events_processed_in_order(self):
        fake_client = FakeBackendClient()
        q = InMemoryEventQueue(settings=make_settings(), backend_client=fake_client)
        q.start()
        try:
            for i in range(3):
                q.enqueue(make_event(external_id=str(i)))
            _wait_until(lambda: len(fake_client.sent_events) == 3)
            ids = [e.employee_external_id for e in fake_client.sent_events]
            assert ids == ["0", "1", "2"]
        finally:
            q.stop()


class TestInMemoryEventQueueErrorHandling:
    def test_validation_error_drops_event_no_infinite_retry(self):
        """BackendValidationError - qayta urinilmasligi va navbatda qolib ketmasligi kerak."""
        fake_client = FakeBackendClient(
            fail_with=BackendValidationError("bad data"), fail_times=999
        )
        q = InMemoryEventQueue(settings=make_settings(), backend_client=fake_client)
        q.start()
        try:
            q.enqueue(make_event())
            time.sleep(0.2)  # workerga ishlash uchun vaqt beramiz
            assert len(fake_client.sent_events) == 0  # yuborilmadi (rad etildi)
            assert len(q._queue) == 0  # lekin navbatda ham qolib ketmadi (dead letter)
        finally:
            q.stop()

    def test_auth_error_drops_event(self):
        fake_client = FakeBackendClient(
            fail_with=BackendAuthError("bad api key"), fail_times=999
        )
        q = InMemoryEventQueue(settings=make_settings(), backend_client=fake_client)
        q.start()
        try:
            q.enqueue(make_event())
            time.sleep(0.2)
            assert len(fake_client.sent_events) == 0
            assert len(q._queue) == 0
        finally:
            q.stop()

    def test_transient_error_is_retried_and_eventually_succeeds(self):
        """Oddiy Exception (masalan tarmoq xatosi) - navbatga qaytariladi va oxir-oqibat yuboriladi."""
        fake_client = FakeBackendClient(fail_with=ConnectionError("temp network issue"), fail_times=2)
        q = InMemoryEventQueue(
            settings=make_settings(retry_backoff_base_seconds=0.01), backend_client=fake_client
        )
        q.start()
        try:
            q.enqueue(make_event())
            _wait_until(lambda: len(fake_client.sent_events) == 1, timeout=3)
            assert len(fake_client.sent_events) == 1
        finally:
            q.stop()


class TestQueueCapacity:
    def test_full_queue_drops_oldest(self):
        """maxsize=3 bo'lsa, 4-element qo'yilganda eng eskisi tashlanadi."""
        # Worker'ni ishga tushirmaymiz - shunda navbat qo'lda to'ldirilishi kuzatiladi
        q = InMemoryEventQueue(settings=make_settings(queue_max_size=3), backend_client=FakeBackendClient())

        for i in range(4):
            q.enqueue(make_event(external_id=str(i)))

        assert len(q._queue) == 3
        remaining_ids = [e.employee_external_id for e in q._queue._items]
        assert remaining_ids == ["1", "2", "3"]  # "0" tashlab yuborilgan
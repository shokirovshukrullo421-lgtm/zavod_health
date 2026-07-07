"""
services/backend_client.py uchun testlar.

Haqiqiy tarmoq so'rovi yubormaslik uchun `requests.post` monkeypatch
qilinadi (soxta javob bilan almashtiriladi).
"""

from __future__ import annotations

import requests
import pytest

from config.settings import Settings
from exceptions.backend import (
    BackendAuthError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendUnavailableError,
    BackendValidationError,
)
from models.event import AuthMethod, RecognizedEvent
from services.backend_client import BackendClient


def make_settings(**overrides) -> Settings:
    defaults = dict(
        dahua_host="192.168.1.50",
        dahua_username="admin",
        dahua_password="pass",
        backend_base_url="http://localhost:8000",
        backend_api_key="test-key",
        retry_max_attempts=3,
        retry_backoff_base_seconds=0.01,   # testlar tez o'tishi uchun juda kichik
        retry_backoff_max_seconds=0.05,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def make_event() -> RecognizedEvent:
    from datetime import datetime

    return RecognizedEvent(
        device_code="DEV-001",
        scanned_at=datetime.utcnow(),
        employee_external_id="1024",
        auth_method=AuthMethod.FACE,
        temperature=36.6,
        mask_on=True,
    )


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, headers: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_data


class TestSuccessfulSend:
    def test_send_event_success(self, monkeypatch):
        calls = []

        def fake_post(url, data=None, headers=None, timeout=None):
            calls.append((url, data, headers, timeout))
            return FakeResponse(200)

        monkeypatch.setattr(requests, "post", fake_post)

        client = BackendClient(settings=make_settings())
        client.send_event(make_event())

        assert len(calls) == 1
        url, _, headers, _ = calls[0]
        assert url == "http://localhost:8000/api/v1/device-events"
        assert headers["Authorization"] == "Bearer test-key"


class TestNonRetryableErrors:
    """Bu xatoliklarda qayta urinilmasligi kerak - bitta so'rovdan keyin darhol raise."""

    def test_auth_error_no_retry(self, monkeypatch):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append(1)
            return FakeResponse(401)

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings())

        with pytest.raises(BackendAuthError):
            client.send_event(make_event())
        assert len(calls) == 1  # qayta urinilmadi

    def test_validation_error_no_retry(self, monkeypatch):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append(1)
            return FakeResponse(422, json_data={"detail": [{"msg": "employee not found"}]})

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings())

        with pytest.raises(BackendValidationError) as exc_info:
            client.send_event(make_event())
        assert len(calls) == 1
        assert exc_info.value.validation_errors == [{"msg": "employee not found"}]


class TestRetryableErrors:
    """Bu xatoliklarda retry_max_attempts marta urinilishi kerak."""

    def test_timeout_retries_and_fails(self, monkeypatch):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append(1)
            raise requests.Timeout("simulated timeout")

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings(retry_max_attempts=3))

        with pytest.raises(BackendTimeoutError):
            client.send_event(make_event())
        assert len(calls) == 3  # aynan max_attempts marta urinildi

    def test_connection_error_retries_and_fails(self, monkeypatch):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append(1)
            raise requests.ConnectionError("simulated connection error")

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings(retry_max_attempts=2))

        with pytest.raises(BackendConnectionError):
            client.send_event(make_event())
        assert len(calls) == 2

    def test_service_unavailable_then_success(self, monkeypatch):
        """Birinchi urinish 503, ikkinchisi muvaffaqiyatli - qayta urinish ishlaganini isbotlaydi."""
        responses = [FakeResponse(503, headers={"Retry-After": "1"}), FakeResponse(200)]

        def fake_post(*args, **kwargs):
            return responses.pop(0)

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings(retry_max_attempts=3))

        client.send_event(make_event())  # xato ko'tarmasligi kerak
        assert responses == []  # ikkala javob ham ishlatildi

    def test_unavailable_exhausts_retries(self, monkeypatch):
        def fake_post(*args, **kwargs):
            return FakeResponse(503)

        monkeypatch.setattr(requests, "post", fake_post)
        client = BackendClient(settings=make_settings(retry_max_attempts=2))

        with pytest.raises(BackendUnavailableError):
            client.send_event(make_event()) 
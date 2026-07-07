"""
parsers/dahua_parser.py uchun testlar.

Diqqat: bu testlar Dahua'ning TAXMINIY JSON formatiga asoslangan
(parsers/dahua_parser.py faylining boshidagi izohga qarang). Agar
haqiqiy qurilmangiz boshqacha format yuborsa, avval parser
moslashtiriladi, keyin shu testlar ham yangilanadi.
"""

from __future__ import annotations

import pytest

from exceptions.device import DeviceParseError
from models.event import AuthMethod, RecognizedEvent, UnrecognizedEvent
from parsers.dahua_parser import parse_dahua_event


class TestRecognizedEvent:
    def test_successful_face_recognition(self):
        payload = {
            "Code": "AccessControl",
            "Data": {
                "UserID": "1024",
                "Status": "Success",
                "Method": "Face",
                "Temperature": 36.6,
                "IsWearingMask": True,
                "Time": "2026-07-05 12:34:56",
            },
        }
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")

        assert isinstance(event, RecognizedEvent)
        assert event.employee_external_id == "1024"
        assert event.auth_method == AuthMethod.FACE
        assert event.mask_on is True
        assert str(event.temperature) == "36.6"
        assert event.device_code == "DEV-001"

    def test_fingerprint_method(self):
        payload = {
            "Data": {
                "UserID": "42",
                "Status": "Success",
                "Method": "Fingerprint",
                "Time": "2026-07-05 09:00:00",
            }
        }
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert event.auth_method == AuthMethod.FINGERPRINT

    def test_temperature_with_comma_decimal(self):
        """Ba'zi qurilmalar '36,6' kabi vergul bilan yuborishi mumkin."""
        payload = {
            "Data": {
                "UserID": "1",
                "Status": "Success",
                "Method": "Face",
                "Temperature": "36,6",
                "Time": "2026-07-05 12:00:00",
            }
        }
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert str(event.temperature) == "36.6"

    def test_missing_temperature_is_optional(self):
        payload = {
            "Data": {
                "UserID": "1",
                "Status": "Success",
                "Method": "Face",
                "Time": "2026-07-05 12:00:00",
            }
        }
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert event.temperature is None


class TestUnrecognizedEvent:
    def test_no_match_status(self):
        payload = {"Data": {"Status": "NoMatch", "Time": "2026-07-05 12:35:00"}}
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert isinstance(event, UnrecognizedEvent)

    def test_missing_user_id_treated_as_unrecognized(self):
        payload = {"Data": {"Status": "Success", "Time": "2026-07-05 12:35:00"}}
        event = parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert isinstance(event, UnrecognizedEvent)


class TestParseErrors:
    def test_missing_data_field(self):
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body={"Code": "Something"}, device_code="DEV-001")

    def test_data_not_a_dict(self):
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body={"Data": "not-a-dict"}, device_code="DEV-001")

    def test_missing_time_field(self):
        payload = {"Data": {"UserID": "1", "Status": "Success", "Method": "Face"}}
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body=payload, device_code="DEV-001")

    def test_unparseable_time_format(self):
        payload = {
            "Data": {
                "UserID": "1", "Status": "Success", "Method": "Face", "Time": "notatime",
            }
        }
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body=payload, device_code="DEV-001")

    def test_unknown_auth_method(self):
        payload = {
            "Data": {
                "UserID": "1", "Status": "Success", "Method": "Iris",
                "Time": "2026-07-05 12:00:00",
            }
        }
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body=payload, device_code="DEV-001")

    def test_temperature_out_of_physical_range(self):
        """Harorat 90 gradus bo'lishi mumkin emas — sensor xatosi deb hisoblanadi."""
        payload = {
            "Data": {
                "UserID": "1", "Status": "Success", "Method": "Face",
                "Temperature": 90, "Time": "2026-07-05 12:00:00",
            }
        }
        with pytest.raises(DeviceParseError):
            parse_dahua_event(raw_body=payload, device_code="DEV-001")

    def test_parse_error_preserves_raw_payload(self):
        """DeviceParseError.raw_payload debug uchun asl ma'lumotni saqlashi kerak."""
        payload = {"Code": "Something"}
        with pytest.raises(DeviceParseError) as exc_info:
            parse_dahua_event(raw_body=payload, device_code="DEV-001")
        assert exc_info.value.raw_payload == payload
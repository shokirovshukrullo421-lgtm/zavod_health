"""
Logging tizimini sozlash.

log_setup/logging.yaml faylini o'qib, Python'ning standart
logging.config.dictConfig orqali barcha logger/handler/formatter'larni
sozlaydi. app.py ishga tushganda BIR MARTA setup_logging() chaqiriladi.

MUHIM: bu papka avval "logging" deb nomlangan edi. Bu Python
STANDART kutubxonasidagi modul nomi bilan bir xil edi va deyarli
har bir faylimiz `import logging` ishlatgani uchun butun loyihani
buzishi mumkin edi. Shu sabab "log_setup" deb qayta nomlandi — bu
faylning o'zi ham xavfsizlik uchun oddiy `import logging`
(standart kutubxona) ishlatadi, bu endi to'g'ri ishlaydi.
"""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "logging.yaml"


def setup_logging(config_path: str | Path | None = None, *, log_dir: str = "logs") -> None:
    """
    Logging'ni sozlaydi.

    log_dir avtomatik yaratiladi (mavjud bo'lmasa) — RotatingFileHandler
    papka mavjud bo'lmasa xatolik beradi, shu sabab oldindan yaratamiz.

    Agar logging.yaml topilmasa (masalan hali yaratilmagan bo'lsa),
    ilova butunlay to'xtab qolmasligi uchun oddiy basicConfig'ga
    tushadi va ogohlantirish log qiladi.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )
        logging.getLogger(__name__).warning(
            "logging.yaml topilmadi (%s), standart sozlama ishlatildi", config_path
        )
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)
    logging.getLogger(__name__).info("Logging sozlandi: %s", config_path)


def get_logger(name: str) -> logging.Logger:
    """Qulaylik uchun kichik wrapper — logging.getLogger(name)ning o'rnini bosadi."""
    return logging.getLogger(name)
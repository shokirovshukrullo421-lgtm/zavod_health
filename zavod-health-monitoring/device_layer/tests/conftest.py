"""
Pytest umumiy sozlamalari.

device_layer ildizini sys.path'ga qo'shadi — shunda testlar
`from models.event import ...` kabi bare importlarni ishlata oladi,
xuddi ilovaning o'zi ishlaganidek (chunki app.py ham device_layer
papkasi ichidan ishga tushiriladi).
"""

from __future__ import annotations

import sys
from pathlib import Path

DEVICE_LAYER_ROOT = Path(__file__).resolve().parent.parent
if str(DEVICE_LAYER_ROOT) not in sys.path:
    sys.path.insert(0, str(DEVICE_LAYER_ROOT))
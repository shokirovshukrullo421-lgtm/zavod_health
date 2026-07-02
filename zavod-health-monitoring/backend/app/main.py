"""
Zavod Sog'liq Monitoring Portali — Backend kirish nuqtasi.
"""
from fastapi import FastAPI

from app.routers import auth, device, doctor, manager, admin

app = FastAPI(
    title="Zavod Sog'liq Monitoring Portali",
    description="Korxonaga kirish jarayonida xodimlar sog'lig'ini nazorat qilish tizimi",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(device.router)
app.include_router(doctor.router)
app.include_router(manager.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    """Tizim ishlab turganini tekshirish uchun oddiy endpoint."""
    return {"status": "ok"}

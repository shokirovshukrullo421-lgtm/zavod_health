"""
Login uchun so'rov/javob shakllari (Pydantic).
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str

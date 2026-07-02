"""
Backend bilan muloqot — barcha HTTP so'rovlar shu yerdan o'tadi.
"""
import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"


def get_headers() -> dict:
    """Session'dagi JWT tokenni header sifatida qaytaradi."""
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def login(login: str, password: str) -> dict | None:
    """Login qilish. Muvaffaqiyatli bo'lsa token va rol qaytaradi."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"login": login, "password": password},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi. Server ishlab turganini tekshiring.")
        return None


def get_pending_events() -> list:
    """Shifokor: pending hodisalar ro'yxati."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/doctor/pending",
            headers=get_headers(),
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return []


def review_event(event_id: int, decision: str, note: str = None) -> bool:
    """Shifokor: hodisani tasdiqlash."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/doctor/review/{event_id}",
            headers=get_headers(),
            json={"decision": decision, "doctor_note": note},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return False


def get_employees() -> list:
    """Bo'lim mas'uli: xodimlar ro'yxati."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/manager/employees",
            headers=get_headers(),
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return []


def create_employee(data: dict) -> bool:
    """Bo'lim mas'uli: yangi xodim qo'shish."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/manager/employees",
            headers=get_headers(),
            json=data,
            timeout=5,
        )
        return resp.status_code == 201
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return False


def update_employee(employee_id: int, data: dict) -> bool:
    """Bo'lim mas'uli: xodim ma'lumotlarini tahrirlash."""
    try:
        resp = requests.put(
            f"{BACKEND_URL}/manager/employees/{employee_id}",
            headers=get_headers(),
            json=data,
            timeout=5,
        )
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return False


def delete_employee(employee_id: int) -> bool:
    """Bo'lim mas'uli: xodimni o'chirish (soft delete)."""
    try:
        resp = requests.delete(
            f"{BACKEND_URL}/manager/employees/{employee_id}",
            headers=get_headers(),
            timeout=5,
        )
        return resp.status_code == 204
    except requests.exceptions.ConnectionError:
        st.error("Backend bilan ulanib bo'lmadi.")
        return False

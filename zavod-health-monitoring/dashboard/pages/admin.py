"""
Admin paneli — foydalanuvchilarni boshqarish va me'yor sozlash.
"""
import streamlit as st
from utils.api import get_headers
import requests

BACKEND_URL = "http://localhost:8000"


def api_get(path: str):
    """GET so'rov, xatolarni ushlab turadi."""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", headers=get_headers(), timeout=5)
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.json().get("detail", "Xatolik yuz berdi")
    except requests.exceptions.ConnectionError:
        return None, "Backend bilan ulanib bo'lmadi"


def api_post(path: str, data: dict):
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", headers=get_headers(), json=data, timeout=5)
        if resp.status_code in (200, 201):
            return resp.json(), None
        return None, resp.json().get("detail", "Xatolik yuz berdi")
    except requests.exceptions.ConnectionError:
        return None, "Backend bilan ulanib bo'lmadi"


def api_put(path: str, data: dict):
    try:
        resp = requests.put(f"{BACKEND_URL}{path}", headers=get_headers(), json=data, timeout=5)
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.json().get("detail", "Xatolik yuz berdi")
    except requests.exceptions.ConnectionError:
        return None, "Backend bilan ulanib bo'lmadi"


def api_delete(path: str):
    try:
        resp = requests.delete(f"{BACKEND_URL}{path}", headers=get_headers(), timeout=5)
        if resp.status_code == 204:
            return True, None
        return False, resp.json().get("detail", "Xatolik yuz berdi")
    except requests.exceptions.ConnectionError:
        return False, "Backend bilan ulanib bo'lmadi"


def show():
    st.title("⚙️ Admin paneli")

    tab1, tab2 = st.tabs(["👥 Foydalanuvchilar", "🌡️ Me'yor sozlamalari"])

    # ── 1. Foydalanuvchilar ─────────────────────────────────────
    with tab1:
        users, err = api_get("/admin/users")

        if err:
            st.error(f"Xatolik: {err}")
            return

        role_labels = {
            "doctor": "👨‍⚕️ Shifokor",
            "manager": "👔 Bo'lim mas'uli",
            "admin": "⚙️ Admin",
        }

        st.markdown(f"**Jami: {len(users)} foydalanuvchi**")

        for user in users:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    status_icon = "🟢" if user["is_active"] else "🔴"
                    st.markdown(f"{status_icon} **{user['full_name']}**")
                    st.caption(f"Login: `{user['login']}`")

                with col2:
                    st.markdown(role_labels.get(user["role"], user["role"]))
                    st.caption(user["created_at"][:10])

                with col3:
                    if st.button("✏️", key=f"edit_u_{user['id']}", help="Tahrirlash"):
                        st.session_state[f"edit_user_{user['id']}"] = True
                    if st.button("🗑️", key=f"del_u_{user['id']}", help="O'chirish"):
                        st.session_state[f"confirm_del_user_{user['id']}"] = True

                # Tahrirlash formasi
                if st.session_state.get(f"edit_user_{user['id']}"):
                    with st.form(key=f"edit_user_form_{user['id']}"):
                        st.markdown("**Ma'lumotlarni tahrirlash:**")
                        new_name = st.text_input("Ism", value=user["full_name"])
                        new_role = st.selectbox(
                            "Rol",
                            ["doctor", "manager", "admin"],
                            index=["doctor", "manager", "admin"].index(user["role"]),
                            format_func=lambda x: role_labels.get(x, x),
                        )
                        new_pass = st.text_input("Yangi parol (bo'sh qoldirsangiz o'zgarmaydi)", type="password")
                        new_active = st.checkbox("Faol", value=user["is_active"])

                        save = st.form_submit_button("💾 Saqlash", type="primary")
                        cancel = st.form_submit_button("Bekor qilish")

                        if save:
                            update_data = {
                                "full_name": new_name,
                                "role": new_role,
                                "is_active": new_active,
                            }
                            if new_pass:
                                update_data["password"] = new_pass

                            result, err = api_put(f"/admin/users/{user['id']}", update_data)
                            if err:
                                st.error(f"Xatolik: {err}")
                            else:
                                st.session_state.pop(f"edit_user_{user['id']}", None)
                                st.success("Saqlandi!")
                                st.rerun()
                        if cancel:
                            st.session_state.pop(f"edit_user_{user['id']}", None)
                            st.rerun()

                # O'chirish tasdiqi
                if st.session_state.get(f"confirm_del_user_{user['id']}"):
                    st.warning(f"**{user['full_name']}** ni o'chirishni tasdiqlaysizmi?")
                    yes_col, no_col = st.columns(2)
                    with yes_col:
                        if st.button("Ha, o'chirish", key=f"yes_del_u_{user['id']}", type="primary"):
                            ok, err = api_delete(f"/admin/users/{user['id']}")
                            if err:
                                st.error(f"Xatolik: {err}")
                            else:
                                st.session_state.pop(f"confirm_del_user_{user['id']}", None)
                                st.success("O'chirildi.")
                                st.rerun()
                    with no_col:
                        if st.button("Bekor qilish", key=f"no_del_u_{user['id']}"):
                            st.session_state.pop(f"confirm_del_user_{user['id']}", None)
                            st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Yangi foydalanuvchi")

        with st.form("create_user_form"):
            full_name = st.text_input("To'liq ism *")
            login = st.text_input("Login *")
            password = st.text_input("Parol * (kamida 6 belgi)", type="password")
            role = st.selectbox(
                "Rol *",
                ["doctor", "manager", "admin"],
                format_func=lambda x: role_labels.get(x, x),
            )
            submit = st.form_submit_button("➕ Qo'shish", type="primary")

            if submit:
                if not full_name or not login or not password:
                    st.error("Barcha majburiy maydonlarni to'ldiring.")
                elif len(password) < 6:
                    st.error("Parol kamida 6 ta belgidan iborat bo'lishi kerak.")
                else:
                    result, err = api_post("/admin/users", {
                        "full_name": full_name,
                        "login": login,
                        "password": password,
                        "role": role,
                    })
                    if err:
                        st.error(f"Xatolik: {err}")
                    else:
                        st.success(f"'{full_name}' muvaffaqiyatli qo'shildi!")
                        st.rerun()

    # ── 2. Me'yor sozlamalari ───────────────────────────────────
    with tab2:
        st.markdown("### 🌡️ Sog'liq ko'rsatkichlari me'yori")
        st.caption("Bu yerda shifokorga ogohlantirish ko'rsatiladigan chegara qiymatlari sozlanadi.")

        thresholds, err = api_get("/admin/thresholds")

        if err:
            st.error(f"Xatolik: {err}")
            return

        metric_labels = {
            "temperature": "🌡️ Harorat (°C)",
        }

        for threshold in thresholds:
            label = metric_labels.get(threshold["metric_name"], threshold["metric_name"])
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{label}**")
                    st.caption(f"Oxirgi yangilangan: {threshold['updated_at'][:16].replace('T', ' ')}")
                with col2:
                    if st.button("✏️ Tahrirlash", key=f"edit_t_{threshold['metric_name']}"):
                        st.session_state[f"edit_threshold_{threshold['metric_name']}"] = True

                # Joriy qiymat
                st.metric(
                    label="Joriy chegara",
                    value=f"{threshold['max_value']}°C" if threshold["metric_name"] == "temperature" else threshold["max_value"],
                )

                # Tahrirlash
                if st.session_state.get(f"edit_threshold_{threshold['metric_name']}"):
                    with st.form(key=f"threshold_form_{threshold['metric_name']}"):
                        new_val = st.number_input(
                            "Yangi qiymat",
                            value=float(threshold["max_value"]),
                            min_value=35.0,
                            max_value=42.0,
                            step=0.1,
                            format="%.1f",
                        )
                        save = st.form_submit_button("💾 Saqlash", type="primary")
                        cancel = st.form_submit_button("Bekor qilish")

                        if save:
                            result, err = api_put(
                                f"/admin/thresholds/{threshold['metric_name']}",
                                {"max_value": new_val},
                            )
                            if err:
                                st.error(f"Xatolik: {err}")
                            else:
                                st.session_state.pop(f"edit_threshold_{threshold['metric_name']}", None)
                                st.success(f"Me'yor {new_val}°C ga yangilandi!")
                                st.rerun()
                        if cancel:
                            st.session_state.pop(f"edit_threshold_{threshold['metric_name']}", None)
                            st.rerun()

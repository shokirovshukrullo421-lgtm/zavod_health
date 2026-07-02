"""
Zavod Sog'liq Monitoring — Streamlit kirish nuqtasi.
Login sahifasi va rolga qarab yo'naltirish.
"""
import streamlit as st

from utils.api import login
from components.sidebar import show_sidebar
from pages import doctor, manager, admin

st.set_page_config(
    page_title="Zavod Sog'liq Monitoring",
    page_icon="🏥",
    layout="wide",
)


def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🏭 Zavod Sog'liq Monitoring")
        st.markdown("### Tizimga kirish")
        st.markdown("---")

        with st.form("login_form"):
            user_login = st.text_input("Login", placeholder="login")
            password = st.text_input("Parol", type="password", placeholder="••••••")
            submit = st.form_submit_button("Kirish", type="primary", use_container_width=True)

            if submit:
                if not user_login or not password:
                    st.error("Login va parolni kiriting.")
                else:
                    result = login(user_login, password)
                    if result:
                        st.session_state["token"] = result["access_token"]
                        st.session_state["role"] = result["role"]
                        st.session_state["full_name"] = result["full_name"]
                        st.rerun()
                    else:
                        st.error("Login yoki parol noto'g'ri.")


def main():
    if "token" not in st.session_state:
        show_login()
        return

    show_sidebar()
    role = st.session_state.get("role")

    if role == "doctor":
        doctor.show()
    elif role == "manager":
        manager.show()
    elif role == "admin":
        admin.show()
    else:
        st.error("Noma'lum rol. Iltimos, tizim administratoriga murojaat qiling.")
        if st.button("Chiqish"):
            st.session_state.clear()
            st.rerun()


if __name__ == "__main__":
    main()

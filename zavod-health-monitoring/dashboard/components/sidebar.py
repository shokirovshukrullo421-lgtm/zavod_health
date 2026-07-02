"""
Umumiy yon panel — barcha sahifalarda ko'rinadi.
"""
import streamlit as st


def show_sidebar():
    """Yon panelda foydalanuvchi ma'lumotlari va chiqish tugmasi."""
    with st.sidebar:
        st.markdown("## 🏭 Zavod Monitoring")
        st.markdown("---")

        full_name = st.session_state.get("full_name", "")
        role = st.session_state.get("role", "")

        role_labels = {
            "doctor": "👨‍⚕️ Shifokor",
            "manager": "👔 Bo'lim mas'uli",
            "admin": "⚙️ Admin",
        }

        st.markdown(f"**{full_name}**")
        st.markdown(f"{role_labels.get(role, role)}")
        st.markdown("---")

        if st.button("🚪 Chiqish", use_container_width=True):
            st.session_state.clear()
            st.rerun()

"""
Shifokor paneli — pending hodisalarni ko'rish va tasdiqlash.
"""
import streamlit as st
import pandas as pd
from utils.api import get_pending_events, review_event


def show():
    st.title("👨‍⚕️ Shifokor paneli")

    events = get_pending_events()

    if not events:
        st.success("✅ Hozircha barcha hodisalar ko'rib chiqilgan.")
        return

    st.markdown(f"### Kutayotgan hodisalar: **{len(events)}** ta")
    st.markdown("---")

    for event in events:
        # Harorat ogohlantirish rangi
        temp = event.get("temperature")
        temp_warning = event.get("temperature_warning", False)
        threshold = event.get("temperature_threshold", 37.0)

        if temp_warning:
            temp_str = f"🔴 {temp}°C (me'yor: {threshold}°C)"
        else:
            temp_str = f"🟢 {temp}°C" if temp else "—"

        mask_str = "✅ Bor" if event.get("mask_on") else "❌ Yo'q"

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**{event['employee_full_name']}**")
                st.caption(f"{event['career_name']} → {event['department_name']}")
                st.caption(f"🕐 {event['scanned_at'][:16].replace('T', ' ')}")

            with col2:
                st.markdown(f"🌡️ Harorat: {temp_str}")
                st.markdown(f"😷 Niqob: {mask_str}")
                st.caption(f"Identifikatsiya: {event['auth_method']}")

            with col3:
                event_id = event["id"]

                if st.button("✅ Ruxsat", key=f"allow_{event_id}", use_container_width=True):
                    if review_event(event_id, "allowed"):
                        st.success("Ruxsat berildi!")
                        st.rerun()
                    else:
                        st.error("Xatolik yuz berdi.")

                if st.button("🏥 Tekshiruv", key=f"medical_{event_id}", use_container_width=True, type="secondary"):
                    st.session_state[f"note_open_{event_id}"] = True

            # Izoh yozish (ixtiyoriy)
            if st.session_state.get(f"note_open_{event_id}"):
                note = st.text_area("Izoh (ixtiyoriy):", key=f"note_{event_id}")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Tasdiqlash", key=f"confirm_{event_id}", type="primary"):
                        if review_event(event_id, "medical_check", note):
                            st.session_state.pop(f"note_open_{event_id}", None)
                            st.warning("Qo'shimcha tekshiruv tayinlandi.")
                            st.rerun()
                        else:
                            st.error("Xatolik yuz berdi.")
                with cancel_col:
                    if st.button("Bekor qilish", key=f"cancel_{event_id}"):
                        st.session_state.pop(f"note_open_{event_id}", None)
                        st.rerun()

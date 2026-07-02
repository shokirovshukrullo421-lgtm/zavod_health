"""
Bo'lim mas'uli paneli — xodimlarni boshqarish.
"""
import streamlit as st
from utils.api import get_employees, create_employee, update_employee, delete_employee


def show():
    st.title("👔 Bo'lim mas'uli paneli")

    tab1, tab2 = st.tabs(["📋 Xodimlar ro'yxati", "➕ Yangi xodim"])

    # ── 1. Ro'yxat ──────────────────────────────────────────────
    with tab1:
        employees = get_employees()

        if not employees:
            st.info("Bo'limingizda xodimlar yo'q yoki hali qo'shilmagan.")
        else:
            st.markdown(f"**Jami: {len(employees)} xodim**")

            for emp in employees:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"**{emp['last_name']} {emp['first_name']}**")
                        st.caption(emp.get("position") or "Lavozim ko'rsatilmagan")

                    with col2:
                        depts = ", ".join(emp.get("departments", []))
                        st.caption(f"Bo'lim(lar): {depts or '—'}")

                    with col3:
                        if st.button("✏️", key=f"edit_{emp['id']}", help="Tahrirlash"):
                            st.session_state[f"editing_{emp['id']}"] = True
                        if st.button("🗑️", key=f"del_{emp['id']}", help="O'chirish"):
                            st.session_state[f"confirm_delete_{emp['id']}"] = True

                    # Tahrirlash formasi
                    if st.session_state.get(f"editing_{emp['id']}"):
                        with st.form(key=f"edit_form_{emp['id']}"):
                            st.markdown("**Ma'lumotlarni tahrirlash:**")
                            new_first = st.text_input("Ism", value=emp["first_name"])
                            new_last = st.text_input("Familiya", value=emp["last_name"])
                            new_pos = st.text_input("Lavozim", value=emp.get("position") or "")
                            save = st.form_submit_button("💾 Saqlash", type="primary")
                            cancel = st.form_submit_button("Bekor qilish")

                            if save:
                                ok = update_employee(emp["id"], {
                                    "first_name": new_first,
                                    "last_name": new_last,
                                    "position": new_pos or None,
                                })
                                if ok:
                                    st.session_state.pop(f"editing_{emp['id']}", None)
                                    st.success("Saqlandi!")
                                    st.rerun()
                                else:
                                    st.error("Xatolik yuz berdi.")
                            if cancel:
                                st.session_state.pop(f"editing_{emp['id']}", None)
                                st.rerun()

                    # O'chirish tasdiqi
                    if st.session_state.get(f"confirm_delete_{emp['id']}"):
                        st.warning(f"**{emp['last_name']} {emp['first_name']}** ni o'chirishni tasdiqlaysizmi?")
                        yes_col, no_col = st.columns(2)
                        with yes_col:
                            if st.button("Ha, o'chirish", key=f"yes_del_{emp['id']}", type="primary"):
                                if delete_employee(emp["id"]):
                                    st.session_state.pop(f"confirm_delete_{emp['id']}", None)
                                    st.success("Xodim o'chirildi.")
                                    st.rerun()
                        with no_col:
                            if st.button("Bekor qilish", key=f"no_del_{emp['id']}"):
                                st.session_state.pop(f"confirm_delete_{emp['id']}", None)
                                st.rerun()

    # ── 2. Yangi xodim qo'shish ─────────────────────────────────
    with tab2:
        with st.form("create_employee_form"):
            st.markdown("**Yangi xodim ma'lumotlari:**")
            first_name = st.text_input("Ism *")
            last_name = st.text_input("Familiya *")
            position = st.text_input("Lavozim")
            dept_ids_str = st.text_input(
                "Bo'lim ID(lar) *",
                help="Bir nechta bo'lim uchun vergul bilan yozing: 1, 2"
            )
            submit = st.form_submit_button("➕ Qo'shish", type="primary")

            if submit:
                if not first_name or not last_name or not dept_ids_str:
                    st.error("Ism, familiya va bo'lim ID(lar)i majburiy.")
                else:
                    try:
                        dept_ids = [int(x.strip()) for x in dept_ids_str.split(",")]
                        ok = create_employee({
                            "first_name": first_name,
                            "last_name": last_name,
                            "position": position or None,
                            "department_ids": dept_ids,
                        })
                        if ok:
                            st.success(f"{last_name} {first_name} muvaffaqiyatli qo'shildi!")
                        else:
                            st.error("Xatolik yuz berdi. Bo'lim ID'larini tekshiring.")
                    except ValueError:
                        st.error("Bo'lim ID'lari faqat raqam bo'lishi kerak.")

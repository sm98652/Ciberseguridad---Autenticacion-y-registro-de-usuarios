import streamlit as st

from web_app import style
from web_app.session import current_user, is_admin

st.set_page_config(page_title="Nuu", layout="centered")
style.apply()

all_pages = [
    st.Page("all_pages/1_landing_page.py", title="Inicio"),
    st.Page("all_pages/2_auth_page.py", title="Acceso"),
    st.Page("all_pages/3_A_page.py", title="Equipo A"),
    st.Page("all_pages/4_B_page.py", title="Equipo B"),
    st.Page("all_pages/5_C_page.py", title="Equipo Chat"),
]

if current_user():
    all_pages.insert(2, st.Page("all_pages/7_account_page.py", title="Mi cuenta"))

# La página solo se muestra en el menú a los administradores. Esto es comodidad,
# no seguridad: la página y el servicio vuelven a verificar el permiso.
if is_admin(current_user()):
    all_pages.append(st.Page("all_pages/6_admin_page.py", title="Administración"))


def main() -> None:
    pg = st.navigation(all_pages)
    pg.run()


if __name__ == "__main__":
    main()

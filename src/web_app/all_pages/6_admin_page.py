from datetime import date

import streamlit as st

from web_app import style
from web_app.session import get_service, require_admin

user = require_admin()
service = get_service()

st.markdown("<p class='brand'>Nuu · administración</p>", unsafe_allow_html=True)

with st.container(key="admin-card"):
    style.section(
        "Exportar usuarios",
        "Descarga en CSV los datos de todas las cuentas con la verificación en dos pasos activa.",
    )
    st.markdown(
        "<p class='section-note'>El archivo contiene datos personales, de salud y financieros "
        "sin cifrar. Guárdalo en un lugar seguro y bórralo cuando ya no lo necesites.</p>",
        unsafe_allow_html=True,
    )
    st.download_button(
        "Descargar CSV",
        # Se genera solo al hacer clic, no cada vez que se carga la página.
        data=lambda: service.export_users_csv(user["email"]),
        file_name=f"usuarios_nuu_{date.today():%Y%m%d}.csv",
        mime="text/csv",
        width="stretch",
        on_click="ignore",
    )

style.footer()

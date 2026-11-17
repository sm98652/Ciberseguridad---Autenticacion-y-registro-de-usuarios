import streamlit as st

from web_app import style
from web_app.session import require_login

require_login()

st.markdown("<p class='brand'>Nuu · área privada</p>", unsafe_allow_html=True)

with st.container(key="page-card"):
    style.section("Equipo Chat", "Solo visible con sesión iniciada.")

style.footer()

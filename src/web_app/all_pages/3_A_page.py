import streamlit as st

from web_app.session import require_login

require_login()

st.title("Equipo A")

import streamlit as st

from web_app import style
from web_app.session import current_user

st.markdown("<p class='brand'>Nuu</p>", unsafe_allow_html=True)
st.markdown(
    "<h1 class='hero-title'>Tus datos, bajo llave.</h1>"
    "<p class='hero-lead'>Una cuenta protegida con contraseña y un código que solo genera tu "
    "celular. Lo que nos confías se guarda cifrado.</p>",
    unsafe_allow_html=True,
)

with st.container(key="features"):
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        style.section("Dos pasos", "Además de la contraseña, se pide un código que cambia cada 30 segundos.")
    with c2:
        style.section("Cifrado", "Datos personales, de salud y financieros se guardan cifrados.")
    with c3:
        style.section("Bloqueo", "Cinco intentos fallidos bloquean el acceso durante 15 minutos.")

user = current_user()
label = "Ir a mi cuenta" if user else "Ingresar o crear cuenta"
if st.button(label, key="cta", width="stretch"):
    st.switch_page("all_pages/2_auth_page.py")

style.footer()

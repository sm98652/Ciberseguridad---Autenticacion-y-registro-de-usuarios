import html

import streamlit as st

from web_app import style
from web_app.session import get_service, require_login

user = require_login()
account = get_service().get_account(user["user_id"])

st.markdown("<p class='brand'>Nuu · mi cuenta</p>", unsafe_allow_html=True)

if account is None:
    st.error("No se encontraron los datos de esta cuenta.")
    st.stop()


def mask(value: object) -> str:
    text = str(value)
    return "•" * max(len(text) - 4, 4) + text[-4:] if len(text) > 4 else "••••"


def money(value: object) -> str:
    return f"$ {float(value):,.0f}".replace(",", ".")


def rows(items: list[tuple[str, object]], hidden: bool) -> None:
    # Todo lo que escribió el usuario se escapa: se muestra como HTML y un nombre
    # como "<script>" no debe ejecutarse.
    body = "".join(
        f"<div class='kv'><span>{label}</span>"
        f"<span>{html.escape(mask(value) if hidden and sensitive else str(value) or '—')}</span></div>"
        for label, value, sensitive in items
    )
    st.markdown(body, unsafe_allow_html=True)


with st.container(key="account-card"):
    show = st.toggle("Mostrar datos completos", value=False)
    hidden = not show

    style.section("Cuenta", "Tu contraseña no se muestra porque solo guardamos su hash.")
    rows([("Correo", account["email"], False), ("Registrada (UTC)", account["created_at"], False)], hidden)

    style.section("Datos personales · PII", "Guardados cifrados. Solo tú los ves al iniciar sesión.")
    rows([
        ("Nombre", account["full_name"], False),
        ("Documento", account["document_id"], True),
        ("Nacimiento", account["birth_date"], True),
        ("Teléfono", account["phone"], True),
        ("Dirección", account["address"], True),
    ], hidden)

    style.section("Datos de salud · PHI", "Guardados cifrados.")
    rows([
        ("Tipo de sangre", account["blood_type"], True),
        ("Condiciones médicas", account["medical_conditions"], True),
    ], hidden)

    style.section("Información financiera", "Guardada cifrada.")
    rows([
        ("Ingresos mensuales", money(account["monthly_income"]), True),
        ("Deuda declarada", money(account["declared_debt"]), True),
        ("Puntaje crediticio", account["credit_score"], True),
    ], hidden)

style.footer()

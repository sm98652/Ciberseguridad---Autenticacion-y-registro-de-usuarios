import io
from datetime import date

import qrcode
import streamlit as st

from web_app.auth_service import (
    BLOOD_TYPES,
    AuthStatus,
    RegistrationForm,
    ValidationError,
)
from web_app.session import current_user, get_service, login_user, logout

st.set_page_config(page_title="Acceso • sitio", page_icon="🔐", layout="centered")
st.title("Acceso")

service = get_service()


def qr_png(uri: str) -> bytes:
    qr = qrcode.QRCode(
        version=1, box_size=10, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M
    )
    qr.add_data(uri)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue()


def lock_message(seconds: int) -> str:
    minutes = max(1, -(-seconds // 60))
    return f"Demasiados intentos fallidos. Intenta de nuevo en {minutes} min."


user = current_user()
if user:
    st.success(f"Sesión iniciada como {user['email']}")
    if st.button("Cerrar sesión"):
        logout()
        st.rerun()
    st.stop()

tab_login, tab_register = st.tabs(["Iniciar sesión", "Registro"])

# ------------------------------------------------------------------ login
with tab_login:
    with st.form("login"):
        email = st.text_input("Correo")
        password = st.text_input("Contraseña", type="password")
        code = st.text_input("Código OTP (6 dígitos)", max_chars=7)
        submitted = st.form_submit_button("Entrar")

    if submitted:
        result = service.authenticate(email, password, code)
        if result.status is AuthStatus.OK:
            login_user(result.user_id, result.email)
            st.rerun()
        elif result.status is AuthStatus.LOCKED:
            st.error(lock_message(result.retry_after))
        else:
            # Mismo mensaje sin importar qué factor falló (anti-enumeración).
            st.error("Correo, contraseña o código OTP incorrectos.")

# --------------------------------------------------------------- registro
with tab_register:
    pending = st.session_state.get("pending_enrollment")

    if pending:
        st.subheader("Configura tu autenticador (2FA)")
        st.write(
            "Escanea el QR con Google Authenticator, Authy o similar y escribe el código "
            "de 6 dígitos para activar tu cuenta."
        )
        st.image(qr_png(pending["uri"]), caption="Escanea este QR con tu app de autenticación")
        st.caption(f"¿No puedes escanear? Clave manual: `{pending['secret']}`")

        with st.form("confirm-otp"):
            otp_code = st.text_input("Código OTP", max_chars=7)
            confirm = st.form_submit_button("Confirmar")

        if confirm:
            result = service.confirm_enrollment(pending["email"], otp_code)
            if result.status is AuthStatus.OK:
                st.session_state.pop("pending_enrollment")
                st.success("Cuenta activada. Ya puedes iniciar sesión en la pestaña anterior.")
            elif result.status is AuthStatus.LOCKED:
                st.error(lock_message(result.retry_after))
            else:
                st.error("Código incorrecto. Intenta de nuevo.")
    else:
        with st.form("register"):
            st.subheader("Cuenta")
            r_email = st.text_input("Correo", key="r_email")
            r_pass = st.text_input(
                "Contraseña",
                type="password",
                help="Mínimo 12 caracteres, con mayúscula, minúscula, número y símbolo.",
            )
            r_pass2 = st.text_input("Confirmar contraseña", type="password")

            st.subheader("Datos personales (PII)")
            full_name = st.text_input("Nombre completo")
            document_id = st.text_input("Documento de identidad")
            birth_date = st.date_input(
                "Fecha de nacimiento",
                value=date(1995, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today(),
            )
            phone = st.text_input("Teléfono")
            address = st.text_input("Dirección")

            st.subheader("Datos de salud (PHI)")
            blood_type = st.selectbox("Tipo de sangre", BLOOD_TYPES)
            medical_conditions = st.text_area("Condiciones médicas / alergias (opcional)")

            st.subheader("Datos crediticios")
            monthly_income = st.number_input("Ingresos mensuales", min_value=0.0, step=100000.0)
            declared_debt = st.number_input("Deuda total declarada", min_value=0.0, step=100000.0)
            credit_score = st.number_input("Puntaje crediticio (0–1000)", 0, 1000, 500)

            consent = st.checkbox(
                "Autorizo el tratamiento de mis datos personales y sensibles "
                "(Ley 1581 de 2012) para los fines de este servicio."
            )
            register = st.form_submit_button("Crear cuenta")

        if register:
            try:
                result = service.register(
                    RegistrationForm(
                        email=r_email,
                        password=r_pass,
                        password_confirm=r_pass2,
                        full_name=full_name,
                        document_id=document_id,
                        birth_date=birth_date,
                        phone=phone,
                        address=address,
                        blood_type=blood_type,
                        medical_conditions=medical_conditions,
                        monthly_income=float(monthly_income),
                        declared_debt=float(declared_debt),
                        credit_score=int(credit_score),
                        consent=consent,
                    )
                )
            except ValidationError as exc:
                for message in exc.errors:
                    st.error(message)
            else:
                st.session_state["pending_enrollment"] = {
                    "email": result.email,
                    "uri": result.provisioning_uri,
                    "secret": result.otp_secret,
                }
                st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center;'>© 2025 Nuu | All rights reserved.</p>",
    unsafe_allow_html=True,
)

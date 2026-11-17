import html
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
from web_app import style
from web_app.session import current_user, get_service, login_user, logout

service = get_service()


def qr_png(uri: str) -> bytes:
    qr = qrcode.QRCode(
        version=1, box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M
    )
    qr.add_data(uri)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="#1C2329", back_color="white").save(buf, format="PNG")
    return buf.getvalue()


def lock_message(seconds: int) -> str:
    minutes = max(1, -(-seconds // 60))
    return f"Demasiados intentos fallidos. Intenta de nuevo en {minutes} min."


st.markdown("<p class='brand'>Nuu · acceso seguro</p>", unsafe_allow_html=True)

user = current_user()
if user:
    with st.container(key="session-card"):
        style.avatar()
        with st.form("session"):
            st.markdown(
                f"<p class='session-label'>Sesión activa</p>"
                f"<p class='session-email'>{html.escape(user['email'])}</p>"
                f"<p class='section-note'>Se cierra sola tras 30 minutos sin actividad.</p>",
                unsafe_allow_html=True,
            )
            if st.form_submit_button("Cerrar sesión", width="stretch"):
                logout()
                st.rerun()
    style.footer()
    st.stop()

tab_login, tab_register = st.tabs(["Iniciar sesión", "Crear cuenta"])

with tab_login:
    with st.container(key="login-card"):
        style.avatar()
        with st.form("login"):
            email = st.text_input(
                "Correo", placeholder="Correo electrónico",
                icon=":material/mail:", label_visibility="collapsed",
            )
            password = st.text_input(
                "Contraseña", type="password", placeholder="Contraseña",
                icon=":material/lock:", label_visibility="collapsed",
            )
            code = st.text_input(
                "Código", max_chars=7, placeholder="Código de verificación",
                icon=":material/pin:", label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Entrar", width="stretch")

    if submitted:
        result = service.authenticate(email, password, code)
        if result.status is AuthStatus.OK:
            login_user(result.user_id, result.email)
            st.rerun()
        elif result.status is AuthStatus.LOCKED:
            st.error(lock_message(result.retry_after))
        else:
            # Mismo mensaje sin importar qué factor falló (anti-enumeración).
            st.error("Correo, contraseña o código incorrectos.")

with tab_register:
    pending = st.session_state.get("pending_enrollment")

    if pending:
        style.section(
            "Activa la verificación en dos pasos",
            "Tu cuenta queda pendiente hasta que confirmes el primer código.",
        )
        with st.container(key="enroll-card"):
            col_qr, col_steps = st.columns([1, 1.3], gap="large", vertical_alignment="center")
            with col_qr:
                st.image(qr_png(pending["uri"]), width="stretch")
            with col_steps:
                st.markdown(
                    "1. Abre Google Authenticator, Authy o una app similar.\n"
                    "2. Agrega una cuenta y escanea el código.\n"
                    "3. Escribe abajo los 6 dígitos que aparecen."
                )
                st.caption("Si no puedes escanear, ingresa esta clave manualmente:")
                st.code(pending["secret"], language=None)

        with st.form("confirm-otp"):
            otp_code = st.text_input("Código de verificación", max_chars=7, placeholder="000000")
            confirm = st.form_submit_button("Activar cuenta", width="stretch")

        if confirm:
            result = service.confirm_enrollment(pending["email"], otp_code)
            if result.status is AuthStatus.OK:
                st.session_state.pop("pending_enrollment")
                st.success("Cuenta activada. Ya puedes iniciar sesión.")
            elif result.status is AuthStatus.LOCKED:
                st.error(lock_message(result.retry_after))
            else:
                st.error("Código incorrecto. Intenta de nuevo.")
    else:
        with st.form("register"):
            style.section(
                "Cuenta",
                "Se guarda solo como hash Argon2id, nadie puede leerla.",
            )
            r_email = st.text_input("Correo electrónico", key="r_email", placeholder="nombre@correo.com")
            c1, c2 = st.columns(2)
            r_pass = c1.text_input(
                "Contraseña",
                type="password",
                help="Entre 12 y 128 caracteres, con mayúscula, minúscula, número y símbolo. No puede contener tu correo.",
            )
            r_pass2 = c2.text_input("Confirmar contraseña", type="password")

            style.section("Datos personales · PII", "Se almacenan cifrados.")
            full_name = st.text_input("Nombre completo")
            c1, c2 = st.columns(2)
            document_id = c1.text_input("Documento de identidad")
            birth_date = c2.date_input(
                "Fecha de nacimiento",
                value=date(1995, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                format="DD/MM/YYYY",
            )
            c1, c2 = st.columns(2)
            phone = c1.text_input("Teléfono")
            address = c2.text_input("Dirección")

            style.section("Datos de salud · PHI", "Se almacenan cifrados.")
            blood_type = st.selectbox("Tipo de sangre", BLOOD_TYPES)
            medical_conditions = st.text_area(
                "Condiciones médicas o alergias", placeholder="Opcional", height=90
            )

            style.section("Información financiera", "Se almacena cifrada. No pedimos números de tarjeta.")
            c1, c2, c3 = st.columns(3)
            monthly_income = c1.number_input(
                "Ingresos mensuales (COP)", min_value=0.0, step=100000.0, format="%.0f"
            )
            declared_debt = c2.number_input(
                "Deuda total (COP)", min_value=0.0, step=100000.0, format="%.0f"
            )
            credit_score = c3.number_input("Puntaje crediticio", 0, 1000, 500, help="Escala de 0 a 1000.")

            consent = st.checkbox(
                "Autorizo el tratamiento de mis datos personales y sensibles "
                "conforme a la Ley 1581 de 2012."
            )
            register = st.form_submit_button("Crear cuenta", width="stretch")

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
                st.error("\n".join(f"- {message}" for message in exc.errors))
            else:
                st.session_state["pending_enrollment"] = {
                    "email": result.email,
                    "uri": result.provisioning_uri,
                    "secret": result.otp_secret,
                }
                st.rerun()

style.footer()

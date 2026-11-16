"""Utilidades de Streamlit: servicio compartido y manejo de la sesión del usuario."""

from __future__ import annotations

import time

import streamlit as st

from .auth_service import AuthService
from .config import get_settings
from .db import PostgresUserRepository
from .security import FieldCipher

SESSION_TTL_SECONDS = 30 * 60  # cierre de sesión por inactividad
_KEY = "auth"


@st.cache_resource
def get_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        repo=PostgresUserRepository(settings.database_url),
        cipher=FieldCipher(settings.encryption_keys),
        settings=settings,
    )


def login_user(user_id: int, email: str) -> None:
    st.session_state[_KEY] = {"user_id": user_id, "email": email, "last_seen": time.time()}


def current_user() -> dict | None:
    """Usuario autenticado o None. Renueva la inactividad o cierra la sesión si expiró."""
    data = st.session_state.get(_KEY)
    if not data:
        return None
    if time.time() - data["last_seen"] > SESSION_TTL_SECONDS:
        st.session_state.pop(_KEY, None)
        return None
    data["last_seen"] = time.time()
    return data


def logout() -> None:
    st.session_state.pop(_KEY, None)


def require_login() -> dict:
    """Llamar al inicio de cada página protegida."""
    user = current_user()
    if user is None:
        st.warning("Debes iniciar sesión para ver esta página.")
        st.page_link("all_pages/2_auth_page.py", label="Ir a iniciar sesión", icon="🔐")
        st.stop()
    return user

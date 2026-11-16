# today

App en **Streamlit** con registro de usuarios, autenticación con **contraseña + OTP (2FA)** y almacenamiento cifrado de datos sensibles en PostgreSQL. Proyecto final del curso de ciberseguridad.

## Qué incluye

| Requisito | Dónde está |
|---|---|
| Formulario de registro (correo, contraseña, PII, PHI, datos crediticios) | `src/web_app/all_pages/2_auth_page.py` (pestaña *Registro*) |
| Política de contraseña + hash Argon2id | `src/web_app/security.py` |
| PII/PHI/crédito y secreto OTP cifrados en la base | `src/web_app/security.py` (`FieldCipher`), `src/web_app/db.py` |
| OTP con `pyotp`, anti-replay | `src/web_app/otp.py` |
| Rate limiting y bloqueo | `src/web_app/auth_service.py` + tabla `login_attempts` |
| Formulario de login (correo + contraseña + OTP) | `src/web_app/all_pages/2_auth_page.py` (pestaña *Iniciar sesión*) |
| Páginas protegidas | `3_A_page.py`, `4_B_page.py`, `5_C_page.py` (`require_login()`) |
| Dependencias con **uv** | `pyproject.toml` + `uv.lock` |

Detalle de decisiones y de los casos de login: [docs/SECURITY.md](docs/SECURITY.md).

## Estructura

```
src/web_app/
├── main.py            # navegación de Streamlit
├── config.py          # variables de entorno
├── security.py        # política de contraseña, Argon2id, cifrado Fernet
├── otp.py             # TOTP (pyotp)
├── repository.py      # contrato de acceso a datos
├── db.py              # PostgreSQL + esquema SQL
├── auth_service.py    # registro, login, rate limiting (sin Streamlit)
├── session.py         # sesión de Streamlit y require_login()
└── all_pages/         # páginas de la app
tests/                 # pruebas con repositorio en memoria
```

## Puesta en marcha

Requisitos: [uv](https://docs.astral.sh/uv/), Python 3.14 y un PostgreSQL accesible.

```bash
# 1. Dependencias
uv sync

# 2. Configuración
cp .env.example .env
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# pega la clave en APP_ENCRYPTION_KEY y ajusta DATABASE_URL

# 3. Crear las tablas
uv run --env-file .env python -m web_app.db

# 4. Ejecutar
uv run --env-file .env streamlit run src/web_app/main.py
```

> Guarda `APP_ENCRYPTION_KEY` fuera del repositorio y haz copia de ella: **sin la clave no se pueden descifrar los datos**.

### Usuario de base de datos con mínimo privilegio

```sql
CREATE ROLE today_app LOGIN PASSWORD 'CAMBIAR';
GRANT CONNECT ON DATABASE today TO today_app;
GRANT SELECT, INSERT, UPDATE ON users, login_attempts TO today_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO today_app;
```

## Pruebas

```bash
uv run pytest
```

Cubren la política de contraseña, el cifrado, las 8 combinaciones de login, la reutilización de OTP, la deriva de reloj y el bloqueo por intentos.

## Flujo de uso

1. **Registro** → se validan los datos, se guarda la contraseña con Argon2id y el resto cifrado.
2. La app muestra un **QR**; se escanea con Google Authenticator/Authy y se confirma con un código. Hasta entonces la cuenta no puede iniciar sesión.
3. **Login** → correo + contraseña + código OTP. Ante cualquier fallo se muestra el mismo mensaje; tras 5 fallos en 15 min el correo se bloquea temporalmente.
4. La sesión se cierra tras 30 min de inactividad.

## Subir al repositorio público

```bash
git add .
git commit -m "Registro, login con OTP y datos cifrados"
git push
```

Antes del push verifica que `.env` **no** aparezca en `git status` (ya está en `.gitignore`).

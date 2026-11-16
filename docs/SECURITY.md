# Decisiones de seguridad

## Contraseñas
- **Política**: 12–128 caracteres, con minúscula, mayúscula, número y símbolo; no puede contener la parte local del correo ni estar en una lista corta de contraseñas comunes. El límite máximo evita que alguien envíe textos enormes para gastar CPU al hashear.
- **Almacenamiento**: Argon2id (`argon2-cffi`, parámetros por defecto) con sal propia. Si los parámetros se endurecen en el futuro, el hash se actualiza solo en el siguiente login correcto.
- **Mejora pendiente**: comparar contra una lista de contraseñas filtradas (p. ej. Have I Been Pwned).

## Datos sensibles (PII, PHI, crédito)
- Se guardan en tres columnas cifradas con **Fernet** (AES-128-CBC + HMAC-SHA256): `pii_enc`, `phi_enc`, `credit_enc`. El correo queda en claro porque es el identificador de login.
- No se almacenan números de tarjeta: el apartado crediticio es ingreso, deuda y puntaje.
- La clave vive en `APP_ENCRYPTION_KEY` (variable de entorno, nunca en git). Admite varias claves separadas por coma para **rotación**.
- La base de datos puede filtrarse sin que los datos sean legibles, pero quien tenga la base **y** la clave sí los lee. Mantén la clave en un sitio distinto a la base (p. ej. AWS Secrets Manager).

## OTP (recomendaciones de la documentación de pyotp aplicadas)
| Recomendación | Implementación |
|---|---|
| Ventana de tolerancia pequeña | ±1 paso de 30 s (`otp.WINDOW`) |
| No reutilizar un código | `otp_last_step` se actualiza con `UPDATE ... WHERE otp_last_step < paso` (atómico); un código ya usado se rechaza |
| Comparación segura | `hmac.compare_digest`, recorriendo todos los pasos sin salida anticipada |
| Limitar intentos (fuerza bruta) | Ver *Rate limiting* |
| Secreto protegido | Se guarda cifrado; solo se muestra una vez, durante el registro |
| Verificar antes de activar | La cuenta no puede iniciar sesión hasta confirmar un primer código |

## Rate limiting
- Se cuentan los **fallos por correo** (existan o no) en una ventana de `LOCKOUT_MINUTES` (15). Al llegar a `MAX_FAILED_ATTEMPTS` (5) el login responde *bloqueado* aunque las credenciales sean correctas.
- El bloqueo termina cuando el fallo más antiguo sale de la ventana; los intentos hechos estando bloqueado no lo extienden.
- Un login correcto reinicia el contador.
- Los intentos se guardan en `login_attempts` (correo, éxito, motivo, fecha) como bitácora de auditoría.
- Limitación: el contador es por correo, no por IP. Un atacante que pruebe pocos intentos contra muchas cuentas no se bloquea; complementa con Security Groups/nginx/fail2ban.

## Casos de login (usuario, contraseña, OTP)

La respuesta al usuario es **siempre la misma** salvo en el bloqueo. El motivo real solo queda en la bitácora.

| # | Usuario | Contraseña | OTP | Resultado | Motivo registrado |
|---|---|---|---|---|---|
| 1 | ✔ | ✔ | ✔ | Acceso | `ok` |
| 2 | ✔ | ✔ | ✘ | Rechazado | `bad_otp` (o `otp_replay` si ya se usó) |
| 3 | ✔ | ✘ | ✔ | Rechazado | `bad_password` |
| 4 | ✔ | ✘ | ✘ | Rechazado | `bad_password+bad_otp` |
| 5–8 | ✘ | cualquiera | cualquiera | Rechazado | `unknown_user` |
| — | cuenta sin OTP confirmado | — | — | Rechazado | `otp_not_confirmed` |
| — | ≥ 5 fallos en 15 min | — | — | Bloqueado temporalmente | (no se registra) |

Medidas contra enumeración de usuarios: mismo mensaje, y se verifica siempre una contraseña y un OTP (con valores señuelo si el correo no existe) para que el tiempo de respuesta sea parecido. Excepción conocida: el registro sí dice si un correo ya está registrado.

## Registro
- Si un correo se registró pero nunca confirmó su OTP, volver a registrarlo reemplaza esos datos (evita dejar el correo "secuestrado" por un registro abandonado). Una cuenta confirmada nunca se sobrescribe.
- Se exige autorización de tratamiento de datos (Ley 1581 de 2012, que clasifica los datos de salud como sensibles).

## Pendiente / siguientes pasos
- Servir tras nginx con HTTPS (las credenciales viajan por la red).
- Límite de registros por IP/tiempo y verificación de correo.
- Códigos de recuperación si se pierde el autenticador.

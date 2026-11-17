import csv
import io
from collections.abc import Iterable, Mapping

COLUMNS = [
    ("email", "Correo"),
    ("created_at", "Fecha de registro (UTC)"),
    ("full_name", "Nombre completo"),
    ("document_id", "Documento"),
    ("birth_date", "Fecha de nacimiento"),
    ("phone", "Teléfono"),
    ("address", "Dirección"),
    ("blood_type", "Tipo de sangre"),
    ("medical_conditions", "Condiciones médicas"),
    ("monthly_income", "Ingresos mensuales"),
    ("declared_debt", "Deuda declarada"),
    ("credit_score", "Puntaje crediticio"),
]

# Excel y LibreOffice ejecutan como fórmula una celda que empieza por estos
# caracteres (CSV injection). Se antepone una comilla simple para neutralizarla.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def users_to_csv(rows: Iterable[Mapping[str, object]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([header for _, header in COLUMNS])
    for row in rows:
        writer.writerow([_safe_cell(row.get(key)) for key, _ in COLUMNS])
    # utf-8-sig para que Excel muestre bien tildes y eñes.
    return buf.getvalue().encode("utf-8-sig")
    return buf.getvalue().encode("utf-8-sig")

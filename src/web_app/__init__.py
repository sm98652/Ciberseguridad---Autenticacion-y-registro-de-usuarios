import sys
from pathlib import Path


def main() -> None:
    """Punto de entrada de `uv run web-app`: lanza la app con Streamlit."""
    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", str(Path(__file__).parent / "main.py")]
    sys.exit(stcli.main())

"""Sistema de Gestión de Biblioteca (SGB)."""
try:  # carga variables desde .env si python-dotenv está instalado
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

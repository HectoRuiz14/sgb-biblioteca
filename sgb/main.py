from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from sgb.api import auth, datos_abiertos, ia, libros

app = FastAPI(
    title="Library Management API (SGB)",
    description="REST API for the Library Management System: JWT authentication, book catalog CRUD, an LLM-powered assistant (RAG), and Open Data Analytics (DuckDB).",
    version="1.0.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and login (JWT)."},
        {"name": "Books", "description": "CRUD operations for the library catalog. Requires a token."},
        {"name": "AI Assistant", "description": "Natural-language questions about the catalog (LLM + RAG). Requires a token."},
        {"name": "Datos Abiertos y Analítica", "description": "Consultas analíticas de APIs públicas colombianas con DuckDB y resiliencia."},
    ],
)
app.include_router(auth.router)
app.include_router(libros.router)
app.include_router(ia.router)
app.include_router(datos_abiertos.router)


@app.get("/health", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")

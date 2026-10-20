# sgb-biblioteca

Sistema de Gestión de Biblioteca (Taller de Programación, UMB). Python + SQLAlchemy 2.0 + Alembic + FastAPI.

- **Guía 4 (ORM):** modelos `Autor`, `Categoria`, `Libro`, `Usuario`, `Prestamo`, repositorios y migraciones.
- **Guía 5 (API + LLM):** API REST con login JWT, CRUD de libros, OpenAPI 3.0 en inglés, asistente con Gemini (RAG) y página web.

## Puesta en marcha
```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # completa GEMINI_API_KEY, SECRET_KEY y DEMO_PASSWORD
alembic upgrade head                                   # crea/actualiza tablas (incluye email y password_hash)
python -m scripts.seed                                 # usuario demo + libros de ejemplo
uvicorn sgb.main:app --reload
```
- Página web: http://localhost:8000/  (usuario demo: `demo@sgb.local` con la clave de `DEMO_PASSWORD`, o regístrate)
- Swagger UI: http://localhost:8000/docs  (botón **Authorize** → pega el token del login)

> Si ya tenías un `biblioteca.db` de la Guía 4, `alembic upgrade head` solo agrega la migración nueva; no pierdes datos.

## Endpoints
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | /api/v1/auth/register | no | Registrar usuario (409 si email/ID duplicado) |
| POST | /api/v1/auth/login | no | Devuelve JWT (60 min) |
| GET | /api/v1/auth/me | sí | Perfil del usuario |
| POST | /api/v1/libros | sí | Crear libro (crea autor/categoría si no existen) |
| GET | /api/v1/libros | sí | Listar (`q`, `categoria`, `skip`, `limit`) |
| GET | /api/v1/libros/{id} | sí | Obtener libro |
| PUT | /api/v1/libros/{id} | sí | Actualizar libro |
| DELETE | /api/v1/libros/{id} | sí | Eliminar (409 si tiene préstamos) |
| POST | /api/v1/ai/ask | sí | Pregunta al asistente (RAG; zero-shot / few-shot / cot) |

Errores del LLM: timeout → 504, rate limit → 429, otro fallo → 502.

## Seguridad
Contraseñas con PBKDF2-SHA256 (600 000 iteraciones, sal aleatoria) y tokens JWT HS256, implementados con la librería estándar (`sgb/security.py`). Define un `SECRET_KEY` propio en `.env`.

## Pruebas
```bash
pytest tests/ -v
```
`test_integration.py` (Guía 4, repositorios), `test_api.py` (API: registro/login, CRUD protegido, errores HTTP, IA con LLM simulado) y `test_security.py`.

## Evidencias para el informe de la Guía 5
1. Swagger UI (`/docs`) con todos los endpoints.
2. `python -m scripts.compare_prompts` → `results/prompt_comparison.md` (12 llamadas reales + tokens + latencia).
3. `python -m scripts.cost_estimate` (actualiza antes los precios vigentes).
4. Captura de `pytest` en verde y del pipeline de GitHub Actions.

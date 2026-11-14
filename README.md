# sgb-biblioteca

Sistema de Gestión de Biblioteca (Taller de Programación, UMB). Python + SQLAlchemy 2.0 + Alembic + FastAPI.

- **Guía 4 (ORM):** modelos `Autor`, `Categoria`, `Libro`, `Usuario`, `Prestamo`, repositorios y migraciones.
- **Guía 5 (API + LLM):** API REST con login JWT, CRUD de libros, OpenAPI 3.0 en inglés, asistente con Gemini (RAG) y página web.

## Puesta en marcha
```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # completa GEMINI_API_KEY, SECRET_KEY y DEMO_PASSWORD
alembic upgrade head                                   # crea/actualiza tablas (incluye email, password_hash y rol)
python -m scripts.seed                                 # usuario demo + libros de ejemplo
uvicorn sgb.main:app --reload
```
- Página web: http://localhost:8000/  (usuario demo: `demo@sgb.local` con la clave de `DEMO_PASSWORD`, o regístrate)
- Swagger UI: http://localhost:8000/docs  (botón **Authorize** → pega el token del login)

> Si ya tenías un `biblioteca.db`, `alembic upgrade head` agrega las migraciones pendientes; no pierdes datos y los usuarios existentes reciben el rol `USER`.

## Docker Compose
Requiere Docker Compose v2. Copia `.env.example` a `.env` y define `SECRET_KEY` con un valor aleatorio (por ejemplo, `python -c "import secrets; print(secrets.token_hex(32))"`). Luego ejecuta:
```bash
docker compose up --build
```
Compose espera a que PostgreSQL pase su healthcheck, aplica las migraciones y después inicia FastAPI. La API queda disponible en `http://localhost:8000`; las variables `POSTGRES_*` y `APP_PORT` permiten cambiar las credenciales de desarrollo y los puertos.

El pipeline de GitHub Actions ejecuta las pruebas, construye la imagen y, al hacer push a `main`, la publica en Docker Hub y llama el webhook de Render. Configura los secretos `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` y `RENDER_DEPLOY_HOOK_URL` en el repositorio de GitHub.

## Render + Supabase
En Render configura `DATABASE_URL` como variable de entorno con la URL del **Session Pooler** de Supabase y el esquema `postgresql+psycopg://`. No guardes credenciales en el repositorio. Configura `alembic upgrade head` como comando de pre-despliegue para aplicar las migraciones antes de iniciar la API. Si falta `DATABASE_URL`, la aplicación falla al arrancar en lugar de conectarse accidentalmente a una base SQLite local.

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
Contraseñas con PBKDF2-SHA256 (600 000 iteraciones, sal aleatoria) y tokens JWT HS256, implementados con la librería estándar (`sgb/infrastructure/security.py`). Define un `SECRET_KEY` aleatorio y propio en `.env`; la autenticación rechaza claves ausentes o los valores de ejemplo.

## Pruebas
```bash
pytest tests/ -v
```
`test_integration.py` (Guía 4, repositorios), `test_api.py` (API: registro/login, CRUD protegido, errores HTTP, IA con LLM simulado) y `test_security.py`.

## Roles de acceso (RBAC)
El registro público asigna siempre el rol `USER`; el campo de rol no se acepta desde la solicitud de registro. El login incluye los roles en el JWT (`roles`) y en su respuesta. Los usuarios `USER` y `ADMIN` pueden consultar libros; crear, actualizar o eliminar libros requiere `ADMIN`. Los usuarios existentes reciben `USER` al aplicar la migración.

Para promover manualmente una cuenta de confianza a administrador, actualiza el rol directamente en la base de datos (no existe un endpoint público para elevar privilegios) y vuelve a iniciar sesión para obtener un token actualizado:
```sql
UPDATE usuarios SET rol = 'ADMIN' WHERE email = 'admin@example.com';
```

## Evidencias para el informe de la Guía 5
1. Swagger UI (`/docs`) con todos los endpoints.
2. `python -m scripts.compare_prompts` → `results/prompt_comparison.md` (12 llamadas reales + tokens + latencia).
3. `python -m scripts.cost_estimate` (actualiza antes los precios vigentes).
4. Captura de `pytest` en verde y del pipeline de GitHub Actions.

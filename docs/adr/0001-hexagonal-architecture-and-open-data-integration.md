# 1. Hexagonal Architecture and Open Data Integration with DuckDB and Resilience

Date: 2026-10-27  
Status: Accepted  

## Context

The `sgb-biblioteca` system is a library management platform built with FastAPI and SQLAlchemy. Originally implemented with a flat structure, the project required a transition to Hexagonal Architecture (Ports and Adapters) combined with Domain-Driven Design (DDD) to support evolving requirements while isolating business rules from frameworks and external services.

As part of the external integration requirements, the system must ingest and analyze two public Colombian open datasets:
1. **Public Libraries Directory (Santander)** from the Colombian Open Data portal (`datos.gov.co` via SODA API: `pkhg-bvje.json`).
2. **DIVIPOLA Municipalities Dataset** published by DANE (`gdxc-w37w.json`).

Public APIs are inherently prone to transient failures, rate limits (HTTP 429), intermittent HTTP 5xx responses, or prolonged service outages. Furthermore, calculating cross-dataset analytical metrics (such as coverage rankings, distribution statistics including median and mean, and unserved municipalities) requires analytical processing that must not contaminate or overload the primary transactional database (SQLite/PostgreSQL).

## Decision

### 1. Hexagonal Architecture and Bounded Contexts

The codebase is organized into four distinct architectural layers within `sgb/`:
- **`domain/`**: Pure entities and abstract ports (interfaces), entirely free of dependencies on SQLAlchemy, FastAPI, HTTP clients, or DuckDB. Grouped into five bounded contexts:
  - `catalogo`: entities (`Libro`, `Autor`, `Categoria`) and ports (`LibroRepositoryPort`, `AutorRepositoryPort`, `CategoriaRepositoryPort`).
  - `prestamos`: entities (`Prestamo` with loan deadline and penalty fee calculation logic) and ports (`PrestamoRepositoryPort`, `UnitOfWorkPort`).
  - `usuarios`: entities (`Usuario`) and ports (`UsuarioRepositoryPort`, `PasswordHasherPort`, `TokenPort`).
  - `asistente`: entities (`LLMResult`) and ports (`LLMPort`, `RetrieverPort`).
  - `datos_abiertos`: entities (`BibliotecaPublica`, `MunicipioDivipola`, `EstadisticasBibliotecas`, `CruceDivipolaResultado`, `MunicipioConteo`, `DepartamentoConteo`, `EstadisticasDescriptivas`) and ports (`BibliotecasPort`, `DivipolaPort`, `AnalisisPort`).
- **`application/`**: Use-case orchestration services (`CatalogoService`, `PrestamosService`, `UsuariosService`, `AsistenteService`, `DatosAbiertosService`, `AnalisisService`). Every service receives its ports strictly via constructor dependency injection.
- **`infrastructure/`**: Concrete adapters implementing ports:
  - Database & Repositories: SQLAlchemy ORM models, repository implementations, unit of work.
  - Security & External AI: Password hasher, JWT token service, Gemini REST client, RAG retriever.
  - Resilience: Thread-safe `CircuitBreaker` and `retry_con_backoff`.
  - Open Data & Analytics: `_SocrataJsonAdapter`, `BibliotecasDatosGovAdapter`, `DaneDivipolaAdapter`, and `DuckDBAnalisisAdapter`.
- **`api/`**: Thin FastAPI routers (`auth`, `libros`, `ia`, `datos_abiertos`), dependency assembly (`deps.py`), and Pydantic schemas.

### 2. External APIs Behind Ports with Resilience (Circuit Breaker & Retry with Backoff)

External HTTP APIs must never be called directly from routers or application services. Instead:
- Abstract ports (`BibliotecasPort`, `DivipolaPort`) define the domain contract.
- Adapters in `sgb/infrastructure/datos_abiertos/adapters.py` inherit from a private base class `_SocrataJsonAdapter` to eliminate duplicate HTTP and resilience logic.
- Execution is composed as:
  ```python
  breaker.call(lambda: retry_con_backoff(_llamada_http, ...))
  ```
- **Error classification**:
  - Transient issues (HTTP 429, HTTP 5xx, connection timeouts, transport errors) are retried with exponential backoff (`min(base_delay * factor**(n-1), max_delay)`) without sleep after the final attempt.
  - Client errors (HTTP 4xx except 429) and malformed payloads fail immediately without retrying.
  - Exhausted retries trip the `CircuitBreaker`. Once `failure_threshold` is reached, the breaker enters `OPEN`, immediately rejecting further calls with domain `CircuitoAbiertoError` without hitting the network.
  - After `recovery_timeout`, the circuit transitions to `HALF_OPEN`, allowing a single trial request to verify remote recovery.

### 3. Embedded DuckDB as the OLAP Analytical Adapter

To cross-reference public libraries with official DANE DIVIPOLA data, records must be matched through normalized municipality names (stripping diacritics and converting to uppercase) and aggregated through analytical SQL (top rankings, percentage calculations, median, mean, min, max, and outer joins).

Rather than writing manual procedural loops in Python or creating migrations and temporary tables in the transactional SQLite database:
- We defined an abstract port `AnalisisPort` in the domain.
- We implemented `DuckDBAnalisisAdapter` in infrastructure, backed by an embedded, in-memory DuckDB connection (`:memory:`).
- DuckDB provides sub-millisecond vectorized execution, native analytical functions (`MEDIAN()`, `AVG()`, `COUNT()`, `LEFT JOIN`), and completely ephemeral tables (`CREATE OR REPLACE TEMP TABLE`), ensuring zero persistence overhead and zero cross-test interference.
- The domain and application layers remain completely unaware of DuckDB.

### 4. Thin API & Observable State

FastAPI endpoints delegate exclusively to `AnalisisService` and adapters injected via `Depends()`. The API exposes:
- `/api/v1/datos-abiertos/estadisticas`: Descriptive metrics and top municipality ranking.
- `/api/v1/datos-abiertos/cruce-divipola`: Departmental distribution, unserved municipalities, and distribution statistics.
- `/api/v1/datos-abiertos/estado-circuitos`: Real-time circuit breaker status (`CLOSED`, `OPEN`, `HALF_OPEN`) for runtime observability and live demonstrations.

## Consequences

### Positive
- **High Testability**: 100% of the application and domain logic can be tested deterministically with mocks or in-memory fakes (`FakeHttpClient`, `FakeClock`, `FakeSleep`) in under 8 seconds without real network access.
- **Fail-Fast & Cascading Failure Protection**: If external government APIs degrade, the circuit breaker trips, protecting threads and returning clear HTTP 503 responses rather than hanging.
- **Analytical Power**: DuckDB provides expressive, robust SQL analytical queries for OLAP workloads without adding external database server dependencies.
- **Clean Architecture & Low Duplication**: SonarQube duplication remains under 3% due to template method inheritance in adapters and parameterized tests.

### Negative
- **Mapping Boilerplate**: Additional code is required to map from external JSON dictionaries to domain entities, from domain entities to DuckDB temporary tables, and from DuckDB result tuples back to domain dataclasses and API Pydantic schemas.
- **Memory Overhead**: Large analytical datasets loaded into memory could consume additional RAM, though mitigated by query limits (`$limit` parameter).

## Alternatives Considered

1. **In-Memory Python Iteration / Dicts**: Performing grouping, median calculations, and joins purely with Python dictionaries. Rejected due to higher code complexity, lack of built-in statistical SQL functions, and risk of duplicating database logic in code.
2. **Transactional SQLite Database for Analytics**: Creating tables in SQLite alongside application tables. Rejected because external open data is ephemeral and analytical in nature (OLAP), which would pollute transactional models, require Alembic migrations, and introduce locking contention.
3. **Direct HTTP Calls in API Routers**: Invoking `httpx` directly inside router endpoints. Rejected because it violates hexagonal architecture, prevents unit testing without mocking HTTP, and couples presentation directly to external network stability.

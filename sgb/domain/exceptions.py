"""Excepciones de dominio y de aplicación (puras, sin dependencias de frameworks)."""


class DomainError(Exception):
    """Excepción base del dominio."""
    pass


class EntityNotFoundError(DomainError):
    pass


class LibroNotFoundError(EntityNotFoundError):
    pass


class UsuarioNotFoundError(EntityNotFoundError):
    pass


class PrestamoNotFoundError(EntityNotFoundError):
    pass


class ConflictError(DomainError):
    pass


class UserAlreadyExistsError(ConflictError):
    pass


class EmailAlreadyRegisteredError(UserAlreadyExistsError):
    pass


class IdentificacionAlreadyRegisteredError(UserAlreadyExistsError):
    pass


class LibroConPrestamosError(ConflictError):
    pass


class InvalidEjemplaresError(ConflictError):
    pass


class SinEjemplaresError(ConflictError):
    """No copies available for loan."""
    pass


class PrestamoYaDevueltoError(ConflictError):
    """Loan has already been returned."""
    pass


class AuthError(DomainError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InactiveUserError(AuthError):
    pass


# ---------- Excepciones LLM / Asistente ----------
class LLMError(DomainError):
    """Error base para fallos del proveedor LLM."""
    pass


class LLMTimeout(LLMError):
    """Timeout esperando respuesta del LLM."""
    pass


class LLMRateLimit(LLMError):
    """Límite de tasa de peticiones alcanzado en el LLM."""
    pass


class LLMUnavailable(LLMError):
    """LLM no disponible o error de red / configuración."""
    pass


# ---------- Excepciones de Resiliencia / Integraciones ----------
class CircuitoAbiertoError(DomainError):
    """Lanzada cuando una llamada es rechazada porque el circuito está abierto o en prueba."""
    pass


class FuenteExternaError(DomainError):
    """Lanzada cuando una fuente externa no responde o devuelve una respuesta errónea."""
    pass

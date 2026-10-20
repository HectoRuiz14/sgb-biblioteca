"""RAG básico: recupera los libros más relacionados con la pregunta (palabras clave) usando el
LibroRepository.listar_con_autor (una sola consulta con JOIN) y arma el contexto para el LLM."""
import re
import unicodedata

from sqlalchemy.orm import Session

from sgb.models import Libro
from sgb.repositories import LibroRepository

_STOP = {
    "the", "and", "you", "have", "about", "which", "what", "are", "for", "any", "some", "books", "book", "does", "with",
    "los", "las", "una", "del", "que", "qué", "cual", "cuál", "libros", "libro", "hay", "tienen", "tiene", "sobre", "con", "por", "para",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


_STOP_N = {_norm(w) for w in _STOP}


def tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", _norm(text)) if len(w) > 2 and w not in _STOP_N}


def retrieve(session: Session, question: str, k: int = 5) -> list[Libro]:
    q = tokenize(question)
    scored = []
    for libro in LibroRepository(session).listar_con_autor():
        doc = tokenize(f"{libro.titulo} {libro.autor.nombre} {libro.categoria.nombre} {libro.editorial or ''}")
        score = len(q & doc)
        if score:
            scored.append((score, libro))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [libro for _, libro in scored[:k]]


def format_context(libros: list[Libro]) -> str:
    if not libros:
        return "(no matching books found in the catalog)"
    return "\n".join(
        f"- ID {l.id}: \"{l.titulo}\" by {l.autor.nombre} | category: {l.categoria.nombre} | year: {l.anio or 'n/a'} "
        f"| available copies: {l.ejemplares_disponibles} of {l.ejemplares_totales}"
        for l in libros
    )

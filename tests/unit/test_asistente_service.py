"""Pruebas unitarias para AsistenteService usando unittest.mock (sin base de datos real)."""
from unittest.mock import MagicMock

from sgb.application.asistente_service import AsistenteService
from sgb.domain.asistente.entities import LLMResult
from sgb.domain.asistente.ports import LLMPort, RetrieverPort
from sgb.domain.catalogo.entities import Libro


def test_preguntar_usa_retriever_y_llm():
    llm_port = MagicMock(spec=LLMPort)
    retriever_port = MagicMock(spec=RetrieverPort)
    prompt_builder = MagicMock(return_value="Prompt construido")

    service = AsistenteService(llm_port, retriever_port, prompt_builder=prompt_builder)

    libros_mock = [Libro(id=42, titulo="Cien años de soledad")]
    retriever_port.retrieve.return_value = libros_mock
    retriever_port.format_context.return_value = "Contexto formateado"
    llm_port.generate.return_value = LLMResult(
        text="Respuesta simulada",
        prompt_tokens=15,
        completion_tokens=5,
        latency_ms=25,
        model="test-model",
    )

    respuesta = service.preguntar("¿Tienen libros de Gabo?", "few-shot")

    retriever_port.retrieve.assert_called_once_with(None, "¿Tienen libros de Gabo?")
    retriever_port.format_context.assert_called_once_with(libros_mock)
    prompt_builder.assert_called_once_with("few-shot", "¿Tienen libros de Gabo?", "Contexto formateado")
    llm_port.generate.assert_called_once_with("Prompt construido")

    assert respuesta.answer == "Respuesta simulada"
    assert respuesta.sources == [42]
    assert respuesta.technique == "few-shot"
    assert respuesta.model == "test-model"

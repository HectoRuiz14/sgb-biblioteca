"""Servicio de aplicación para el Asistente IA (RAG + LLM)."""
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from sgb.domain.asistente.ports import LLMPort, RetrieverPort
from sgb.prompts import build_prompt


@dataclass
class AsistenteRespuesta:
    answer: str
    technique: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    sources: List[int]


class AsistenteService:
    def __init__(
        self,
        llm_port: LLMPort,
        retriever_port: RetrieverPort,
        prompt_builder: Optional[Callable[[str, str, str], str]] = None,
    ):
        self.llm_port = llm_port
        self.retriever_port = retriever_port
        self.prompt_builder = prompt_builder or build_prompt

    def preguntar(
        self,
        question: str,
        technique: str,
        context_source: Any = None,
    ) -> AsistenteRespuesta:
        libros = self.retriever_port.retrieve(context_source, question)
        context = self.retriever_port.format_context(libros)
        prompt = self.prompt_builder(technique, question, context)
        result = self.llm_port.generate(prompt)

        sources = [getattr(l, "id", None) for l in libros if getattr(l, "id", None) is not None]
        return AsistenteRespuesta(
            answer=result.text,
            technique=technique,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            sources=sources,
        )

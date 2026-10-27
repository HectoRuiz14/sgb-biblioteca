"""Entidades / Value Objects para el Bounded Context Asistente IA."""
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    model: str

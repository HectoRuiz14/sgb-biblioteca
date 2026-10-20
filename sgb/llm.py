"""Cliente de Gemini vía REST (httpx). Traduce fallos a excepciones propias."""
import os
import time
from dataclasses import dataclass

import httpx


class LLMError(Exception):
    pass


class LLMTimeout(LLMError):
    pass


class LLMRateLimit(LLMError):
    pass


class LLMUnavailable(LLMError):
    pass


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    model: str


def generate(prompt: str) -> LLMResult:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "pon_tu_key_aqui":
        raise LLMUnavailable("GEMINI_API_KEY is not configured")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}

    start = time.perf_counter()
    try:
        r = httpx.post(url, json=body, headers={"x-goog-api-key": api_key}, timeout=timeout)
    except httpx.TimeoutException as e:
        raise LLMTimeout(f"LLM did not respond within {timeout}s") from e
    except httpx.HTTPError as e:
        raise LLMUnavailable(f"Network error calling LLM: {e}") from e
    latency = int((time.perf_counter() - start) * 1000)

    if r.status_code == 429:
        raise LLMRateLimit("LLM rate limit reached, retry later")
    if r.status_code >= 400:
        raise LLMUnavailable(f"LLM returned HTTP {r.status_code}")
    data = r.json()
    try:
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise LLMUnavailable("Unexpected LLM response format")
    usage = data.get("usageMetadata", {})
    return LLMResult(text.strip(), usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0), latency, model)

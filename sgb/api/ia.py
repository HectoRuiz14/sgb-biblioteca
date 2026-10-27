from fastapi import APIRouter, Depends, HTTPException

from sgb.api.deps import get_asistente_service, get_current_user
from sgb.api.schemas import AskRequest, AskResponse, ErrorOut
from sgb.application.asistente_service import AsistenteService
from sgb.domain.exceptions import LLMError, LLMRateLimit, LLMTimeout

router = APIRouter(prefix="/api/v1/ai", tags=["AI Assistant"], dependencies=[Depends(get_current_user)])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask the library assistant",
    description="RAG endpoint: retrieves the most relevant books from the catalog and sends them as context to the LLM "
                "using the selected prompting technique (zero-shot, few-shot or chain-of-thought). Requires authentication.",
    responses={
        401: {"model": ErrorOut, "description": "Missing or invalid token"},
        429: {"model": ErrorOut, "description": "LLM rate limit reached"},
        502: {"model": ErrorOut, "description": "LLM unavailable or bad response"},
        504: {"model": ErrorOut, "description": "LLM timeout"},
    },
)
def ask(
    data: AskRequest,
    service: AsistenteService = Depends(get_asistente_service),
):
    try:
        result = service.preguntar(data.question, data.technique)
        return AskResponse(
            answer=result.answer,
            technique=result.technique,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_ms=result.latency_ms,
            sources=result.sources,
        )
    except LLMTimeout as e:
        raise HTTPException(504, str(e))
    except LLMRateLimit as e:
        raise HTTPException(429, str(e))
    except LLMError as e:
        raise HTTPException(502, str(e))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sgb import llm, rag
from sgb.api.deps import get_current_user
from sgb.database import get_session
from sgb.prompts import build_prompt
from sgb.schemas import AskRequest, AskResponse, ErrorOut

router = APIRouter(prefix="/api/v1/ai", tags=["AI Assistant"], dependencies=[Depends(get_current_user)])


@router.post("/ask", response_model=AskResponse, summary="Ask the library assistant",
             description="RAG endpoint: retrieves the most relevant books from the catalog and sends them as context to the LLM "
                         "using the selected prompting technique (zero-shot, few-shot or chain-of-thought). Requires authentication.",
             responses={401: {"model": ErrorOut, "description": "Missing or invalid token"},
                        429: {"model": ErrorOut, "description": "LLM rate limit reached"},
                        502: {"model": ErrorOut, "description": "LLM unavailable or bad response"},
                        504: {"model": ErrorOut, "description": "LLM timeout"}})
def ask(data: AskRequest, session: Session = Depends(get_session)):
    libros = rag.retrieve(session, data.question)
    prompt = build_prompt(data.technique, data.question, rag.format_context(libros))
    try:
        result = llm.generate(prompt)
    except llm.LLMTimeout as e:
        raise HTTPException(504, str(e))
    except llm.LLMRateLimit as e:
        raise HTTPException(429, str(e))
    except llm.LLMError as e:
        raise HTTPException(502, str(e))
    return AskResponse(answer=result.text, technique=data.technique, model=result.model,
                       prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens,
                       latency_ms=result.latency_ms, sources=[l.id for l in libros])

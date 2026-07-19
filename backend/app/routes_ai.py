from fastapi import APIRouter, Depends, HTTPException

from app.ai_engine import ai_status, get_provider
from app.ai_engine.base import AIEngineError
from app.ai_engine.prompts import (
    build_chat_prompt,
    build_generate_prompt,
    build_review_prompt,
    strip_code_fences,
)
from app.auth import require_auth
from app.models import AIChatRequest, AIGenerateRequest, AIReviewRequest

router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_auth)])


@router.get("/status")
def status():
    return ai_status()


@router.post("/generate")
def generate(payload: AIGenerateRequest):
    try:
        provider = get_provider()
        raw = provider.complete(build_generate_prompt(payload.description))
    except AIEngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"content": strip_code_fences(raw), "provider": provider.name}


@router.post("/review")
def review(payload: AIReviewRequest):
    try:
        provider = get_provider()
        text = provider.complete(build_review_prompt(payload.name, payload.content))
    except AIEngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"review": text, "provider": provider.name}


@router.post("/chat")
def chat(payload: AIChatRequest):
    """Stateless follow-up chat about a script (e.g. discussing an AI
    review result) -- see build_chat_prompt for why this re-sends the
    whole transcript each call instead of relying on CLI session state."""
    try:
        provider = get_provider()
        messages = [m.model_dump() for m in payload.messages]
        reply = provider.complete(build_chat_prompt(payload.name, payload.content, messages))
    except AIEngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"reply": reply, "provider": provider.name}

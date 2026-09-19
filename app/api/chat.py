from fastapi import APIRouter

from app.conversation import manager
from app.conversation.memory import memory
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    return manager.respond(req.session_id, req.message)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    memory.delete(session_id)

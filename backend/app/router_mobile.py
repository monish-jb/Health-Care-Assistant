"""
Mobile API Router for Healthcare Knowledge Navigator & LLM RAG Assistant.
Provides lightweight REST endpoints optimized for mobile apps (React Native, Capacitor, iOS, Android).
"""

import time
import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Conversation, Message, PatientContext, KBDocument
from app.schemas import PatientContextResponse, CitationItem
from app.auth import get_current_user
from app.intent import classify_intent
from app.rag import rag_engine, rewrite_query_for_rag
from app.llm import get_llm_provider
from app.triage import evaluate_medical_triage, URGENT_RESPONSE_HEADER
from app.patient_context import (
    get_or_create_patient_context,
    update_patient_context_from_message,
    format_patient_context_for_prompt,
    format_patient_context_summary
)
from app.followup_agent import evaluate_missing_clinical_context
from app.confidence import calculate_evidence_confidence

router = APIRouter(prefix="/mobile/api", tags=["Mobile API"])

# Mobile Request / Response Schemas
class MobileTriageRequest(BaseModel):
    symptoms: str

class MobileTriageResponse(BaseModel):
    triage_level: str  # EMERGENCY | URGENT_EVALUATION | ROUTINE_CONSULTATION | GENERAL_INFO
    is_emergency: bool
    recommended_action: str
    message: str

class MobileChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str

class MobileChatResponse(BaseModel):
    conversation_id: int
    role: str = "assistant"
    reply: str
    intent: str
    triage_level: str
    confidence_level: Optional[str] = None
    is_emergency: bool = False
    followup_options: Optional[List[str]] = None
    citations_count: int = 0
    response_time_ms: int

class MobileConfigResponse(BaseModel):
    app_name: str = "Health-Care-Assistant LLM RAG Service"
    version: str = "1.0.0"
    llm_provider: str
    rag_active: bool
    total_kb_documents: int
    emergency_triage_enabled: bool = True

@router.get("/config", response_model=MobileConfigResponse)
def get_mobile_config(db: Session = Depends(get_db)):
    """Handshake endpoint for mobile apps to verify backend LLM RAG status."""
    from app.config import settings
    kb_count = db.query(KBDocument).count()
    return MobileConfigResponse(
        llm_provider=settings.LLM_PROVIDER,
        rag_active=kb_count > 0,
        total_kb_documents=kb_count
    )

@router.post("/triage", response_model=MobileTriageResponse)
def mobile_quick_triage(req: MobileTriageRequest):
    """
    Rapid standalone symptom triage evaluation for mobile apps before initiating a consultation.
    """
    triage_level, override_msg = evaluate_medical_triage(req.symptoms)
    
    if triage_level == "EMERGENCY":
        return MobileTriageResponse(
            triage_level="EMERGENCY",
            is_emergency=True,
            recommended_action="Call emergency services (911/112) or go to nearest Emergency Room immediately.",
            message=override_msg
        )
    elif triage_level == "URGENT_EVALUATION":
        return MobileTriageResponse(
            triage_level="URGENT_EVALUATION",
            is_emergency=False,
            recommended_action="Schedule an urgent doctor visit within 24-48 hours.",
            message="Your symptoms require prompt clinical evaluation. Please consult a healthcare provider."
        )
    elif triage_level == "ROUTINE_CONSULTATION":
        return MobileTriageResponse(
            triage_level="ROUTINE_CONSULTATION",
            is_emergency=False,
            recommended_action="Schedule a routine clinic appointment.",
            message="Your symptoms appear stable. Discuss these with your doctor during your next visit."
        )
    else:
        return MobileTriageResponse(
            triage_level="GENERAL_INFO",
            is_emergency=False,
            recommended_action="General health inquiry.",
            message="No emergency symptoms detected. Ask any medical questions."
        )

@router.post("/chat", response_model=MobileChatResponse)
async def mobile_chat_message(
    req: MobileChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mobile-optimized chat endpoint returning a structured, lightweight payload for mobile view controllers.
    """
    start_time = time.time()
    
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id, Conversation.user_id == current_user.id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(
            user_id=current_user.id,
            title=req.content[:30] + "..." if len(req.content) > 30 else req.content,
            status="open"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    patient_ctx = get_or_create_patient_context(db, conv.id, current_user.id)
    patient_ctx = update_patient_context_from_message(db, patient_ctx, req.content)
    context_summary_str = format_patient_context_for_prompt(patient_ctx)

    triage_level, emergency_override = evaluate_medical_triage(req.content)
    if triage_level == "EMERGENCY":
        elapsed_ms = int((time.time() - start_time) * 1000)
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=emergency_override,
            intent="emergency_symptoms",
            intent_confidence=0.99,
            triage_level="EMERGENCY",
            escalated=True,
            escalation_reason="Critical emergency red-flag symptoms detected.",
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.status = "escalated"
        db.commit()

        return MobileChatResponse(
            conversation_id=conv.id,
            reply=emergency_override,
            intent="emergency_symptoms",
            triage_level="EMERGENCY",
            confidence_level="HIGH",
            is_emergency=True,
            citations_count=0,
            response_time_ms=elapsed_ms
        )

    intent, intent_confidence = classify_intent(req.content)
    should_followup, followup_question, option_chips = evaluate_missing_clinical_context(intent, patient_ctx)

    if should_followup:
        elapsed_ms = int((time.time() - start_time) * 1000)
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=followup_question,
            intent=intent,
            intent_confidence=intent_confidence,
            triage_level=triage_level,
            followup_options=json.dumps(option_chips) if option_chips else None,
            confidence_level="MEDIUM",
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        db.commit()

        return MobileChatResponse(
            conversation_id=conv.id,
            reply=followup_question,
            intent=intent,
            triage_level=triage_level,
            confidence_level="MEDIUM",
            is_emergency=False,
            followup_options=option_chips,
            citations_count=0,
            response_time_ms=elapsed_ms
        )

    kb_doc_count = db.query(KBDocument).count()
    rewritten_query = rewrite_query_for_rag(req.content, context_summary_str)
    rag_results, top_rag_score = rag_engine.search(db, rewritten_query, top_k=3) if kb_doc_count > 0 else ([], 0.0)

    context_str = "\n\n".join([f"[{i+1}] {r['document_name']}: {r['content']}" for i, r in enumerate(rag_results)]) if rag_results else None
    conf_level, conf_details = calculate_evidence_confidence(rag_results, req.content, kb_doc_count)

    provider = get_llm_provider()
    bot_reply_content = await provider.generate_response(
        messages=[{"role": "user", "content": f"{req.content}\n\nPatient Context:\n{context_summary_str}"}],
        context=context_str,
        intent=intent
    )

    if triage_level == "URGENT_EVALUATION":
        bot_reply_content = URGENT_RESPONSE_HEADER + bot_reply_content

    elapsed_ms = int((time.time() - start_time) * 1000)
    bot_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=bot_reply_content,
        intent=intent,
        intent_confidence=intent_confidence,
        rag_grounded=bool(rag_results),
        retrieval_score=top_rag_score if kb_doc_count > 0 else None,
        triage_level=triage_level,
        confidence_level=conf_level,
        response_time_ms=elapsed_ms
    )
    db.add(bot_msg)
    db.commit()

    return MobileChatResponse(
        conversation_id=conv.id,
        reply=bot_reply_content,
        intent=intent,
        triage_level=triage_level,
        confidence_level=conf_level,
        is_emergency=False,
        citations_count=len(rag_results),
        response_time_ms=elapsed_ms
    )

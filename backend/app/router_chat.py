import time
import datetime
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Conversation, Message, Ticket, KBDocument, KBChunk, PatientContext
from app.schemas import (
    ConversationResponse,
    MessageCreateRequest,
    ChatMessageResult,
    MessageResponse,
    FeedbackRequest,
    PatientContextResponse,
    CitationItem
)
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

def parse_message_json(val: Optional[str]):
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None

def build_message_response(msg: Message) -> MessageResponse:
    parsed_followup = parse_message_json(msg.followup_options)
    parsed_conf_details = parse_message_json(msg.confidence_details)
    raw_citations = parse_message_json(msg.citations)
    parsed_citations = [CitationItem(**c) for c in raw_citations] if raw_citations else None

    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        intent=msg.intent,
        intent_confidence=msg.intent_confidence,
        rag_grounded=msg.rag_grounded or False,
        retrieval_score=msg.retrieval_score,
        escalated=msg.escalated or False,
        escalation_reason=msg.escalation_reason,
        response_time_ms=msg.response_time_ms,
        triage_level=msg.triage_level or "GENERAL_INFO",
        followup_options=parsed_followup,
        confidence_level=msg.confidence_level,
        confidence_details=parsed_conf_details,
        citations=parsed_citations,
        feedback=msg.feedback,
        created_at=msg.created_at
    )

def build_conversation_response(conv: Conversation) -> ConversationResponse:
    messages_formatted = [build_message_response(m) for m in conv.messages]
    ctx_formatted = None
    if conv.patient_context:
        ctx_dict = format_patient_context_summary(conv.patient_context)
        ctx_formatted = PatientContextResponse(**ctx_dict)
        
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        status=conv.status,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages_formatted,
        patient_context=ctx_formatted
    )

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [build_conversation_response(c) for c in conversations]

@router.get("/conversations/{id}", response_model=ConversationResponse)
def get_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return build_conversation_response(conv)

@router.delete("/conversations/{id}")
def delete_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully"}

@router.post("/message", response_model=ChatMessageResult)
async def send_message(
    req: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    # 1. Conversation Setup
    if req.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == req.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title_summary = req.content[:35] + "..." if len(req.content) > 35 else req.content
        conv = Conversation(
            user_id=current_user.id,
            title=title_summary,
            status="open"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Patient Context Retrieval & Update
    patient_ctx = get_or_create_patient_context(db, conv.id, current_user.id)
    patient_ctx = update_patient_context_from_message(db, patient_ctx, req.content)
    context_summary_str = format_patient_context_for_prompt(patient_ctx)

    # 3. Medical Safety & Emergency Triage Evaluation
    triage_level, emergency_override = evaluate_medical_triage(req.content)

    if triage_level == "EMERGENCY":
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=req.content,
            intent="emergency_symptoms",
            intent_confidence=0.99
        )
        db.add(user_msg)

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
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(user_msg)
        db.refresh(bot_msg)

        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )

    # 4. Healthcare Intent Classification
    intent, intent_confidence = classify_intent(req.content)

    # 5. Follow-Up Question Agent Evaluation
    should_followup, followup_question, option_chips = evaluate_missing_clinical_context(intent, patient_ctx)

    if should_followup:
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=req.content,
            intent=intent,
            intent_confidence=intent_confidence
        )
        db.add(user_msg)

        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=followup_question,
            intent=intent,
            intent_confidence=intent_confidence,
            triage_level=triage_level,
            followup_options=json.dumps(option_chips) if option_chips else None,
            confidence_level="MEDIUM",
            confidence_details=json.dumps({"explanation": "Gathering patient history details."}),
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(user_msg)
        db.refresh(bot_msg)

        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )

    # 6. RAG Retrieval & Query Rewriting
    kb_doc_count = db.query(KBDocument).count()
    rewritten_query = rewrite_query_for_rag(req.content, context_summary_str)
    rag_results, top_rag_score = rag_engine.search(db, rewritten_query, top_k=4) if kb_doc_count > 0 else ([], 0.0)

    # Build Citation List & Context String
    citations_list = []
    context_str = None
    if rag_results:
        formatted_chunks = []
        for idx, r in enumerate(rag_results, start=1):
            citations_list.append({
                "id": idx,
                "title": r["document_name"],
                "source_type": r["source_type"],
                "year": "2024",
                "section": r["section_name"],
                "passage": r["content"]
            })
            formatted_chunks.append(f"[{idx}] {r['document_name']} ({r['source_type']} - Section: {r['section_name']}):\n{r['content']}")
        context_str = "\n\n".join(formatted_chunks)

    # 7. Calculate Evidence Confidence
    conf_level, conf_details = calculate_evidence_confidence(rag_results, req.content, kb_doc_count)

    # 8. Retrieve Conversation History & Call LLM Evidence Synthesis
    past_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history_payload = [{"role": m.role, "content": m.content} for m in past_messages]
    history_payload.append({"role": "user", "content": f"User Prompt: {req.content}\n\nPatient Context:\n{context_summary_str}"})

    provider = get_llm_provider()
    bot_reply_content = await provider.generate_response(
        messages=history_payload,
        context=context_str,
        intent=intent
    )

    if triage_level == "URGENT_EVALUATION":
        bot_reply_content = URGENT_RESPONSE_HEADER + bot_reply_content

    # 7b. Complaint / High Priority Auto-Escalation Check
    is_complaint = intent in ["complaint", "billing_dispute"] or any(k in req.content.lower() for k in ["charged", "refund", "complaint", "dispute", "failed and charged"])
    escalated_flag = False
    escalation_reason_str = None
    if is_complaint:
        escalated_flag = True
        escalation_reason_str = "Customer complaint / billing dispute auto-escalated to support ticket."
        new_ticket = Ticket(
            conversation_id=conv.id,
            user_id=current_user.id,
            intent=intent,
            priority="high",
            reason=escalation_reason_str,
            status="open"
        )
        db.add(new_ticket)
        conv.status = "escalated"

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 9. Save Messages to DB
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content,
        intent=intent,
        intent_confidence=intent_confidence
    )
    db.add(user_msg)

    bot_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=bot_reply_content,
        intent=intent,
        intent_confidence=intent_confidence,
        rag_grounded=bool(rag_results),
        retrieval_score=top_rag_score if kb_doc_count > 0 else None,
        triage_level=triage_level,
        escalated=escalated_flag,
        escalation_reason=escalation_reason_str,
        confidence_level=conf_level,
        confidence_details=json.dumps(conf_details),
        citations=json.dumps(citations_list) if citations_list else None,
        response_time_ms=elapsed_ms
    )
    db.add(bot_msg)

    conv.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(bot_msg)

    return ChatMessageResult(
        conversation_id=conv.id,
        user_message=build_message_response(user_msg),
        bot_message=build_message_response(bot_msg),
        patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
    )

@router.post("/resolve/{id}")
def resolve_conversation(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.status = "resolved"
    conv.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Conversation marked as resolved"}

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.feedback not in [1, -1]:
        raise HTTPException(status_code=400, detail="Feedback must be 1 or -1")

    msg = (
        db.query(Message)
        .join(Conversation)
        .filter(Message.id == req.message_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")

    msg.feedback = req.feedback
    db.commit()
    return {"message": "Feedback submitted successfully", "message_id": msg.id, "feedback": msg.feedback}

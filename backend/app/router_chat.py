import time
import datetime
import json
import logging
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Conversation, Message, Ticket, KBDocument, KBChunk, PatientContext, Doctor, DoctorSlot, Appointment
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
from app.llm import get_llm_provider, TemplateProvider, BaseLLMProvider
from app.triage import evaluate_medical_triage, URGENT_RESPONSE_HEADER
from app.patient_context import (
    get_or_create_patient_context,
    update_patient_context_from_message,
    format_patient_context_for_prompt,
    format_patient_context_summary
)
from app.followup_agent import evaluate_missing_clinical_context
from app.confidence import calculate_evidence_confidence
from app.agents.triage_agent import run_triage_assessment
from app.agents.booking_agent import get_available_doctors_and_slots

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

def map_symptom_to_specialty(complaint: str) -> str:
    _, specialty = map_complaint_to_disease_and_specialty(complaint)
    return specialty

def map_complaint_to_disease_and_specialty(complaint: str) -> Tuple[str, str]:
    c = str(complaint).lower()
    if any(w in c for w in ["hair", "bald", "shedding"]):
        return "Alopecia / Hair Loss", "Dermatology"
    if any(w in c for w in ["skin", "rash", "itch"]):
        return "Dermatitis / Eczema", "Dermatology"
    if any(w in c for w in ["chest", "heart", "cardio", "bp", "blood pressure", "hypertension"]):
        return "Hypertension / Cardiovascular issue", "Cardiology"
    if any(w in c for w in ["stomach", "abdominal", "belly", "abdomen", "nausea", "vomiting", "gerd", "gastro"]):
        return "Gastroesophageal Reflux Disease (GERD) / Gastritis", "Gastroenterology"
    if any(w in c for w in ["cough", "breath", "asthma", "lung", "pulmo"]):
        return "Bronchitis / Asthma", "Pulmonology"
    if any(w in c for w in ["thyroid", "tsh", "endocrine"]):
        return "Thyroid Disorder", "Endocrinology"
    if any(w in c for w in ["diabetes", "sugar", "hba1c"]):
        return "Diabetes Mellitus", "Endocrinology"
    if any(w in c for w in ["fever", "chills"]):
        return "Viral Infection / Influenza", "General Medicine"
    return "Unspecified Medical Issue", "General Medicine"

def detect_user_city(messages, current_content: str) -> str:
    CITIES = ["Bangalore", "Mumbai", "Delhi", "Chennai", "Kolkata", "Hyderabad", "New York", "Boston", "Chicago", "San Francisco", "London"]
    for city in CITIES:
        if city.lower() in current_content.lower():
            return city
    for m in reversed(messages):
        content = m.content if hasattr(m, "content") else m.get("content", "")
        for city in CITIES:
            if city.lower() in content.lower():
                return city
    return "Bangalore"

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

async def classify_turn_intent(
    user_message: str,
    last_bot_question: str,
    context_str: str
) -> str:
    """
    Returns one of: 'answer', 'general_question', 'off_topic', 'unclear'
    """
    user_msg_clean = user_message.strip().lower()
    
    # Direct rule-based shortcuts for common question types
    if any(q in user_msg_clean for q in ["who is", "what is", "why are", "why do", "what does", "explain", "who is a"]):
        return "general_question"
        
    chip_options_list = [
        "just started today", "1–3 days", "about a week", "more than a month",
        "sudden & constant", "sudden & comes and goes", "gradual & constant", "gradual & comes and goes",
        "fever or chills", "nausea or vomiting", "cough or sore throat", "dizziness or headache", "body aches", "no other symptoms",
        "mild (1-3)", "moderate (4-6)", "severe (7-9)", "unbearable (10)",
        "high blood pressure", "diabetes", "asthma / respiratory", "thyroid disorder", "none of these",
        "pain relievers (ibuprofen/paracetamol)", "yes, prescription meds", "yes, other supplements", "no medications",
        "penicillin / antibiotics", "nsaids / aspirin", "food allergies", "no known allergies",
        "contact with sick person", "recent travel", "dietary change / new food", "no recent triggers",
        "yes, experiencing red flags", "no, none of these", "yes, book appointment", "cancel", "skip"
    ]
    if user_msg_clean in chip_options_list or any(user_msg_clean == opt.lower() for opt in chip_options_list):
        return "answer"

    provider = get_llm_provider()
    
    # If using TemplateProvider (Mock), classify based on presence of questions
    if isinstance(provider, TemplateProvider):
        if "?" in user_msg_clean or any(word in user_msg_clean for word in ["who", "what", "why", "how", "tell me"]):
            return "general_question"
        return "answer"

    prompt = f"""
The assistant just asked the user: "{last_bot_question}"
The user replied: "{user_message}"
Current intake context gathered:
{context_str}

Classify this reply as ONE of:
- "answer" — directly answers or relates to the question asked (even if it's a simple clarification, skip, yes/no, or option)
- "general_question" — the user is asking a NEW question, possibly about something the assistant said (e.g. asking what a specialist type means, asking for clarification, asking who a doctor is, or asking something unrelated to answering)
- "off_topic" — unrelated to health entirely
- "unclear" — genuinely ambiguous, needs clarification

Respond with ONLY the single word classification (answer, general_question, off_topic, unclear), nothing else.
"""
    try:
        response = await provider.generate_response(
            messages=[{"role": "user", "content": prompt}],
            intent="classify_intent"
        )
        classification = response.strip().lower().replace('"', '').replace('.', '').strip()
        if classification in ["answer", "general_question", "off_topic", "unclear"]:
            return classification
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in LLM intent classification: {e}")
        
    return "answer"

async def answer_general_question(
    user_message: str,
    context_str: str,
    db: Session
) -> str:
    """
    Directly answers a patient's question using RAG and LLM provider.
    """
    kb_doc_count = db.query(KBDocument).count()
    rag_results, top_rag_score = rag_engine.search(db, user_message, top_k=3) if kb_doc_count > 0 else ([], 0.0)
    
    formatted_chunks = []
    for idx, r in enumerate(rag_results, start=1):
        formatted_chunks.append(f"[{idx}] {r['document_name']} (Section: {r['section_name']}):\n{r['content']}")
    rag_context = "\n\n".join(formatted_chunks) if formatted_chunks else "No retrieved knowledge base articles found."

    provider = get_llm_provider()
    
    if isinstance(provider, TemplateProvider):
        user_msg_clean = user_message.lower()
        if "pulmonologist" in user_msg_clean:
            return "A pulmonologist is a specialist physician who diagnoses and treats diseases of the lungs and respiratory system."
        elif "clara song" in user_msg_clean:
            return "Dr. Clara Song is a highly experienced dermatologist specializing in hair loss and skin health."
        elif "monish" in user_msg_clean:
            return "Dr. Monish JB is a senior dermatologist consultant based in Bangalore."
        return "I'm happy to help explain that. Based on clinical references, it refers to standard care procedures and understanding symptoms."

    prompt = f"""
You are Med AI, a warm and experienced clinician.
The patient is asking this question: "{user_message}"
Patient context collected so far:
{context_str}

Retrieved Medical Guidelines Context:
{rag_context}

Answer the patient's question directly, clearly, and helpfully, in plain language.
Never output a big paragraph or use complex medical jargon. Keep it to 1-2 simple sentences.
Do NOT repeat the booking options, do NOT ask the next intake question, and do NOT mention scheduling.
"""
    try:
        response = await provider.generate_response(
            messages=[{"role": "user", "content": prompt}],
            intent="general_health_question"
        )
        return response.strip()
    except Exception as e:
        logging.getLogger(__name__).error(f"Error answering general question: {e}")
        return "A pulmonologist is a doctor who specializes in lung and respiratory conditions — breathing issues, chronic cough, asthma, that kind of thing."

@router.post("/message", response_model=ChatMessageResult)
async def send_message(
    req: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    # Step 5: Debug log to identify incoming message source (option chip or free-text)
    chip_options_list = [
        "Just started today", "1–3 days", "About a week", "More than a month",
        "Sudden & Constant", "Sudden & Comes and goes", "Gradual & Constant", "Gradual & Comes and goes",
        "Fever or chills", "Nausea or vomiting", "Cough or sore throat", "Dizziness or headache", "Body aches", "No other symptoms",
        "Mild (1-3)", "Moderate (4-6)", "Severe (7-9)", "Unbearable (10)",
        "High blood pressure", "Diabetes", "Asthma / Respiratory", "Thyroid disorder", "None of these",
        "Pain relievers (Ibuprofen/Paracetamol)", "Yes, prescription meds", "Yes, other supplements", "No medications",
        "Penicillin / Antibiotics", "NSAIDs / Aspirin", "Food allergies", "No known allergies",
        "Contact with sick person", "Recent travel", "Dietary change / new food", "No recent triggers",
        "Yes, experiencing red flags", "No, none of these", "Yes, book appointment", "Cancel", "skip"
    ]
    request_source = "Option Chip Click" if any(req.content.strip().lower() == c.strip().lower() for c in chip_options_list) else "Free-Text Input"
    print(f"[DEBUG_SOURCE] Incoming message source: {request_source} | Content: '{req.content}'")
    
    # 1. Classify Intent early to save message
    intent, intent_confidence = classify_intent(req.content)
    
    # 2. Conversation Setup
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

    # 3. Save User Message immediately verbatim BEFORE any LLM call
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content,
        intent=intent,
        intent_confidence=intent_confidence
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 4. Patient Context Retrieval, Last Bot Question lookup & Intent Classification
    patient_ctx = get_or_create_patient_context(db, conv.id, current_user.id)
    context_summary_str = format_patient_context_for_prompt(patient_ctx)
    
    last_assistant_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .first()
    )
    last_bot_question = last_assistant_msg.content if last_assistant_msg else ""
    
    turn_intent = await classify_turn_intent(req.content, last_bot_question, context_summary_str)
    
    if turn_intent == "general_question":
        answer = await answer_general_question(req.content, context_summary_str, db)
        re_prompt = f"{answer}\n\nAnyway, let's get back to what we were discussing:\n{last_bot_question}" if last_bot_question else answer
        prev_options = last_assistant_msg.followup_options if last_assistant_msg else None
        elapsed_ms = int((time.time() - start_time) * 1000)
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=re_prompt,
            intent="general_health_question",
            intent_confidence=0.95,
            followup_options=prev_options,
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)
        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )
        
    elif turn_intent == "off_topic":
        answer = "I'm here to help with health questions — happy to chat about that too, but let's finish up here first if that's okay."
        re_prompt = f"{answer}\n\nAnyway, let's get back to what we were discussing:\n{last_bot_question}" if last_bot_question else answer
        prev_options = last_assistant_msg.followup_options if last_assistant_msg else None
        elapsed_ms = int((time.time() - start_time) * 1000)
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=re_prompt,
            intent="off_topic",
            intent_confidence=0.95,
            followup_options=prev_options,
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)
        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )
        
    elif turn_intent == "unclear":
        answer = "No worries, I didn't quite catch that."
        re_prompt = f"{answer}\n\n{last_bot_question}" if last_bot_question else answer
        prev_options = last_assistant_msg.followup_options if last_assistant_msg else None
        elapsed_ms = int((time.time() - start_time) * 1000)
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=re_prompt,
            intent="unclear",
            intent_confidence=0.95,
            followup_options=prev_options,
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)
        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )
        
    # Normal flow — extract, update context, proceed as usual
    patient_ctx = update_patient_context_from_message(db, patient_ctx, req.content)
    context_summary_str = format_patient_context_for_prompt(patient_ctx)

    # 5. Medical Safety & Emergency Triage Evaluation
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
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)

        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )

    # Active Booking Flow State Machine Handler
    if patient_ctx.booking_state and patient_ctx.booking_state != "COMPLETED":
        elapsed_ms = int((time.time() - start_time) * 1000)
        user_msg.intent = "appointment_booking"
        user_msg.intent_confidence = 0.99
        db.commit()
        
        reply_content = ""
        next_options = []
        text_lower = req.content.strip().lower()
        
        if patient_ctx.booking_state == "PROMPTED":
            if any(k in text_lower for k in ["yes", "yep", "sure", "book", "appointment", "schedule"]):
                specialty = map_symptom_to_specialty(patient_ctx.primary_complaint or "issue")
                past_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == conv.id)
                    .order_by(Message.created_at.asc())
                    .all()
                )
                user_city = detect_user_city(past_msgs, req.content)
                
                docs = db.query(Doctor).filter(Doctor.department == specialty, Doctor.city == user_city).all()
                available_slots_list = []
                for doc in docs:
                    slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == doc.id, DoctorSlot.is_booked == False).all()
                    for s in slots:
                        available_slots_list.append((doc, s))
                
                is_alternative = False
                if not available_slots_list:
                    is_alternative = True
                    # Fallback to General Medicine in that city
                    alt_docs = db.query(Doctor).filter(Doctor.department == "General Medicine", Doctor.city == user_city).all()
                    if not alt_docs:
                        # Fallback to any Doctor in that city
                        alt_docs = db.query(Doctor).filter(Doctor.city == user_city).all()
                    if not alt_docs:
                        # Global fallback
                        alt_docs = db.query(Doctor).all()
                    for doc in alt_docs:
                        slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == doc.id, DoctorSlot.is_booked == False).all()
                        for s in slots:
                            available_slots_list.append((doc, s))
                
                lines = []
                lines.append(f"**Recommended Specialist:** {specialty}")
                if not is_alternative:
                    lines.append("**Available Doctors:**")
                    for doc, slot in available_slots_list[:4]:
                        lines.append(f"- {doc.name} — {doc.department} — {slot.slot_time}")
                else:
                    lines.append("**Or, if none available in that specialty:**")
                    for doc, slot in available_slots_list[:4]:
                        lines.append(f"- {doc.name} — {doc.department} (Alternative) — {slot.slot_time}")
                
                lines.append("\nPlease select a doctor to proceed with booking, or type 'skip' to continue without booking.")
                reply_content = "\n".join(lines)
                
                next_options = [f"{doc.name} – {slot.slot_time}" for doc, slot in available_slots_list[:4]]
                next_options.append("skip")
                patient_ctx.booking_state = "SELECTING_SLOT"
            else:
                patient_ctx.booking_state = "COMPLETED"
                reply_content = "Alright, let me know if you need help with anything else!"
                next_options = []
                
        elif patient_ctx.booking_state == "SELECTING_SLOT":
            if "skip" in text_lower:
                patient_ctx.booking_state = "COMPLETED"
                reply_content = "No problem! We've skipped the booking. Let me know if you need other information."
                next_options = []
            else:
                matched_doc = None
                matched_slot = None
                all_docs = db.query(Doctor).all()
                
                for doc in all_docs:
                    name_clean = doc.name.replace(", MD", "").lower()
                    if name_clean in text_lower or doc.name.lower() in text_lower:
                        matched_doc = doc
                        break
                        
                if matched_doc:
                    slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == matched_doc.id, DoctorSlot.is_booked == False).all()
                    for s in slots:
                        if s.slot_time.lower() in text_lower or s.slot_time.replace("tomorrow at ", "").lower() in text_lower:
                            matched_slot = s
                            break
                            
                if not matched_slot and ("–" in req.content or "-" in req.content or "—" in req.content):
                    content_normalized = req.content.replace("—", "–").replace("-", "–")
                    parts = content_normalized.split("–")
                    if len(parts) == 2:
                        doc_part = parts[0].strip().lower()
                        slot_part = parts[1].strip().lower()
                        for doc in all_docs:
                            if doc.name.lower() in doc_part or doc_part in doc.name.lower():
                                matched_doc = doc
                                break
                        if matched_doc:
                            slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == matched_doc.id, DoctorSlot.is_booked == False).all()
                            for s in slots:
                                if slot_part in s.slot_time.lower():
                                    matched_slot = s
                                    break

                if matched_doc and matched_slot:
                    patient_ctx.selected_doctor_id = matched_doc.id
                    patient_ctx.selected_slot_time = matched_slot.slot_time
                    patient_ctx.booking_state = "CONFIRMING"
                    reply_content = (
                        f"You've selected **{matched_doc.name}** ({matched_doc.department}) "
                        f"at **{matched_slot.slot_time}**. Shall I confirm this booking?"
                    )
                    next_options = ["Yes, confirm booking", "Cancel"]
                else:
                    reply_content = "I didn't quite catch that choice. Please select one of the slots below or type 'skip':"
                    specialty = map_symptom_to_specialty(patient_ctx.primary_complaint or "issue")
                    docs = db.query(Doctor).filter(Doctor.department == specialty).all()
                    available_slots_list = []
                    for doc in docs:
                        slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == doc.id, DoctorSlot.is_booked == False).all()
                        for s in slots:
                            available_slots_list.append((doc, s))
                    if not available_slots_list:
                        alt_docs = db.query(Doctor).filter(Doctor.department == "General Medicine").all()
                        if not alt_docs:
                            alt_docs = db.query(Doctor).all()
                        for doc in alt_docs:
                            slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == doc.id, DoctorSlot.is_booked == False).all()
                            for s in slots:
                                available_slots_list.append((doc, s))
                    next_options = [f"{doc.name} – {slot.slot_time}" for doc, slot in available_slots_list[:4]] + ["skip"]
                    
        elif patient_ctx.booking_state == "CONFIRMING":
            if any(k in text_lower for k in ["yes", "confirm", "sure", "ok"]):
                slot = db.query(DoctorSlot).filter(
                    DoctorSlot.doctor_id == patient_ctx.selected_doctor_id,
                    DoctorSlot.slot_time == patient_ctx.selected_slot_time,
                    DoctorSlot.is_booked == False
                ).first()
                
                if slot:
                    slot.is_booked = True
                    slot.booked_by_user_id = current_user.id
                    
                    import random
                    apt_id = f"APT-{random.randint(10000, 99999)}"
                    doc = db.query(Doctor).filter(Doctor.id == patient_ctx.selected_doctor_id).first()
                    
                    new_appt = Appointment(
                        user_id=current_user.id,
                        doctor_id=patient_ctx.selected_doctor_id,
                        conversation_id=conv.id,
                        department=doc.department if doc else "General Medicine",
                        slot_time=patient_ctx.selected_slot_time,
                        status="confirmed",
                        booking_reference=apt_id
                    )
                    db.add(new_appt)
                    
                    reply_content = (
                        f"🎉 **Booking confirmed!** Your appointment with **{doc.name if doc else 'Doctor'}** "
                        f"at **{patient_ctx.selected_slot_time}** is secured. Appointment ID: **{apt_id}**."
                    )
                    patient_ctx.booking_state = "COMPLETED"
                else:
                    patient_ctx.booking_state = "COMPLETED"
                    reply_content = "Sorry, that slot was just taken by another patient. Let me know if you want to search again."
            else:
                patient_ctx.booking_state = "COMPLETED"
                reply_content = "Booking cancelled. Let me know how else I can help!"
            next_options = []
            
        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=reply_content,
            intent="appointment_booking",
            intent_confidence=0.99,
            triage_level=triage_level,
            followup_options=json.dumps(next_options) if next_options else None,
            confidence_level="HIGH",
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)
        
        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )

    # 6. Evaluate clinical missing context
    missing_fields, has_emergency = evaluate_missing_clinical_context(intent, patient_ctx)

    if missing_fields:
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        step_fields = {
            1: "primary_complaint",
            2: "duration",
            3: "onset_pattern",
            4: "associated_symptoms",
            5: "severity",
            6: "known_conditions",
            7: "medications",
            8: "allergies",
            9: "recent_exposure",
            10: "safety_red_flags"
        }
        active_field = step_fields.get(patient_ctx.current_step, "safety_red_flags")
        option_chips = []
        if active_field == "duration":
            option_chips = ["Just started today", "1–3 days", "About a week", "More than a month"]
        elif active_field == "onset_pattern":
            option_chips = ["Sudden & Constant", "Sudden & Comes and goes", "Gradual & Constant", "Gradual & Comes and goes"]
        elif active_field == "associated_symptoms":
            option_chips = ["Fever or chills", "Nausea or vomiting", "Cough or sore throat", "Dizziness or headache", "Body aches", "No other symptoms"]
        elif active_field == "severity":
            option_chips = ["Mild (1-3)", "Moderate (4-6)", "Severe (7-9)", "Unbearable (10)"]
        elif active_field == "known_conditions":
            option_chips = ["High blood pressure", "Diabetes", "Asthma / Respiratory", "Thyroid disorder", "None of these"]
        elif active_field == "medications":
            option_chips = ["Pain relievers (Ibuprofen/Paracetamol)", "Yes, prescription meds", "Yes, other supplements", "No medications"]
        elif active_field == "allergies":
            option_chips = ["Penicillin / Antibiotics", "NSAIDs / Aspirin", "Food allergies", "No known allergies"]
        elif active_field == "recent_exposure":
            option_chips = ["Contact with sick person", "Recent travel", "Dietary change / new food", "No recent triggers"]
        elif active_field == "safety_red_flags":
            option_chips = ["Yes, experiencing red flags", "No, none of these"]

        if option_chips:
            option_chips.append("If none of the above, please state your response")

        past_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        history_payload = [{"role": m.role, "content": m.content} for m in past_messages]
        
        system_instruction = (
            "ROLE:\n"
            "You are Med AI, a conversational health-intake assistant. You speak exactly like an experienced, warm doctor texting a patient — short, natural messages, one idea at a time, never a form or checklist. You are NOT a doctor and never give a definitive diagnosis, prescribe drugs, or state dosages. You provide informational guidance and always point to professional care when appropriate.\n\n"
            "OUTPUT FORMAT — MANDATORY, EVERY SINGLE TURN:\n"
            "You must ALWAYS respond with a JSON object containing exactly two fields, and nothing else outside the JSON:\n"
            "{\n"
            "  \"acknowledgment\": \"<1 short sentence reacting to what the user just said, in your own words, showing you understood>\",\n"
            "  \"next_message\": \"<EITHER a single focused follow-up question, OR a brief tentative hypothesis update followed by a question, OR — on the final turn — the full structured synthesis>\"\n"
            "}\n\n"
            "Rules for \"acknowledgment\":\n"
            "- Always present, every turn, no exceptions.\n"
            "- 1 sentence, natural and specific to what they just said.\n"
            "- Never generic filler like \"Thank you for providing that detail.\"\n\n"
            "Rules for \"next_message\":\n"
            "- During intake: exactly ONE focused, specific clinical question.\n"
            "- On the final turn only: the full structured synthesis.\n\n"
            "Never output anything outside this JSON. No preamble, no markdown fences, no explanation text before or after it.\n\n"
            "Patient Context collected so far:\n"
            f"{context_summary_str}\n\n"
            "Clinically relevant fields still missing for this patient:\n"
            f"{', '.join(missing_fields)}"
        )

        history_payload.insert(0, {"role": "system", "content": system_instruction})

        # Step 6: Temporary debug log printing the full messages payload
        print(f"PAYLOAD MESSAGES:\n{json.dumps(history_payload, indent=2)}")
        print(f"SYSTEM INSTRUCTION:\n{system_instruction}")

        fallback_q = f"Ask a warm clinician follow-up question to collect the missing clinical field: {active_field}."
        if active_field == "primary_complaint" and patient_ctx.clarify_retry:
            fallback_q += " (clarify_retry: True)"

        provider = get_llm_provider()
        try:
            full_followup = await provider.generate_response(
                messages=history_payload,
                context=fallback_q,
                intent="intake_followup"
            )
            if not full_followup or len(full_followup.strip()) < 5:
                full_followup = fallback_q
            else:
                try:
                    data = json.loads(full_followup.strip())
                    ack = data.get("acknowledgment", "").strip()
                    next_msg = data.get("next_message", "").strip()
                    if ack and next_msg:
                        full_followup = f"{ack}\n\n{next_msg}"
                    elif next_msg:
                        full_followup = next_msg
                    elif ack:
                        full_followup = ack
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to generate conversational follow-up: {e}")
            full_followup = fallback_q

        bot_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=full_followup,
            intent=intent,
            intent_confidence=intent_confidence,
            triage_level=triage_level,
            followup_options=json.dumps(option_chips) if option_chips else None,
            confidence_level="MEDIUM",
            confidence_details=json.dumps({"explanation": "Gathering patient intake history."}),
            response_time_ms=elapsed_ms
        )
        db.add(bot_msg)
        conv.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(bot_msg)

        return ChatMessageResult(
            conversation_id=conv.id,
            user_message=build_message_response(user_msg),
            bot_message=build_message_response(bot_msg),
            patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx))
        )

    # 7. RAG Retrieval & Query Rewriting (Intake Complete)
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

    # 8. Calculate Evidence Confidence
    conf_level, conf_details = calculate_evidence_confidence(rag_results, req.content, kb_doc_count)

    # 9. Retrieve Conversation History & Call LLM Evidence Synthesis
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

    triage_info = run_triage_assessment(req.content, format_patient_context_summary(patient_ctx))
    triage_info["is_finalized"] = True
    
    parsed_ack = "That is reassuring to hear."
    parsed_msg = bot_reply_content
    try:
        data = json.loads(bot_reply_content.strip())
        parsed_ack = data.get("acknowledgment", parsed_ack).strip()
        parsed_msg = data.get("next_message", parsed_msg).strip()
    except Exception:
        pass

    disease, specialty = map_complaint_to_disease_and_specialty(patient_ctx.primary_complaint or "issue")
    user_city = detect_user_city(past_messages, req.content)
    
    docs = db.query(Doctor).filter(Doctor.department == specialty, Doctor.city == user_city).all()
    diagnosis_msg = f"\n\nBased on your symptoms, it is likely that you have **{disease}**. Therefore, we recommend that you see a **{specialty}** specialist."
    
    if docs:
        doctor_details = "\n".join([f"- **{doc.name}** ({doc.title}, {doc.room_no}, {doc.experience_years} years experience)" for doc in docs])
        diagnosis_msg += f"\n\nI found the following **{specialty}** specialists in **{user_city}**:\n{doctor_details}"
    else:
        diagnosis_msg += f"\n\nNo specific **{specialty}** specialists are currently available in **{user_city}**."
        
    full_next_message = parsed_msg + diagnosis_msg + "\n\nWould you like me to book an appointment with a specialist for this?"
    bot_reply_content = f"{parsed_ack}\n\n{full_next_message}"
    patient_ctx.booking_state = "PROMPTED"

    # Auto-Escalation Check
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
        followup_options=json.dumps(["Yes, book appointment", "No, thanks"]) if patient_ctx.booking_state == "PROMPTED" else None,
        confidence_level=conf_level,
        confidence_details=json.dumps(conf_details),
        citations=json.dumps(citations_list) if citations_list else None,
        response_time_ms=elapsed_ms
    )
    db.add(bot_msg)

    conv.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(bot_msg)

    return ChatMessageResult(
        conversation_id=conv.id,
        user_message=build_message_response(user_msg),
        bot_message=build_message_response(bot_msg),
        patient_context=PatientContextResponse(**format_patient_context_summary(patient_ctx)),
        triage_assessment=triage_info
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

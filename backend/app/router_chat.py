import time
import datetime
import json
import logging
from typing import List, Optional
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
from app.agents.triage_agent import run_triage_assessment
from app.agents.booking_agent import get_available_doctors_and_slots

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

def map_symptom_to_specialty(complaint: str) -> str:
    c = str(complaint).lower()
    if any(w in c for w in ["hair", "skin", "rash", "dermatology"]):
        return "Dermatology"
    if any(w in c for w in ["chest", "heart", "cardio", "bp", "blood pressure", "hypertension"]):
        return "Cardiology"
    if any(w in c for w in ["stomach", "abdominal", "belly", "abdomen", "nausea", "vomiting", "gerd", "gastro"]):
        return "Gastroenterology"
    if any(w in c for w in ["cough", "breath", "asthma", "lung", "pulmo"]):
        return "Pulmonology"
    if any(w in c for w in ["thyroid", "diabetes", "tsh", "hba1c", "endocrine"]):
        return "Endocrinology"
    return "General Medicine"

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

    # 4. Patient Context Retrieval & Update
    patient_ctx = get_or_create_patient_context(db, conv.id, current_user.id)
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
                docs = db.query(Doctor).filter(Doctor.department == specialty).all()
                available_slots_list = []
                for doc in docs:
                    slots = db.query(DoctorSlot).filter(DoctorSlot.doctor_id == doc.id, DoctorSlot.is_booked == False).all()
                    for s in slots:
                        available_slots_list.append((doc, s))
                
                is_alternative = False
                if not available_slots_list:
                    is_alternative = True
                    alt_docs = db.query(Doctor).filter(Doctor.department == "General Medicine").all()
                    if not alt_docs:
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
        
        active_field = missing_fields[0]
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

        past_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        history_payload = [{"role": m.role, "content": m.content} for m in past_messages]
        
        system_instruction = (
            "You are Med AI, an attentive clinician chatting with a patient. "
            "Your goal is to gather the patient's medical intake information naturally and conversationally. "
            "Never sound like a form, checklist, or survey bot. Ask ONE question at a time.\n\n"
            "Here is the structured Patient Context collected so far:\n"
            f"{context_summary_str}\n\n"
            "Here are the clinically relevant fields still missing for this patient:\n"
            f"{', '.join(missing_fields)}\n\n"
            "Rules:\n"
            "1. BEFORE asking your next question, you MUST first respond to the literal content of the user's previous message — even if it didn't cleanly match an expected category, option chip, or field type.\n"
            "2. If the user's message doesn't fit a structured field (e.g. they describe a trigger or detail instead of picking a clean category), acknowledge the specific detail they gave in your own words before moving on. For example, if they mention a trigger detail or specific circumstances, reference it warmly.\n"
            "3. Ask ONLY one question per turn to gather one of the missing fields. Do NOT ask about anything already present in the context.\n"
            "4. Keep the question short, simple, and in plain language (avoid medical jargon).\n"
            "5. Never label your question (e.g. 'Step N') or expose internal flow to the user.\n"
            "6. Output ONLY the response/question to the user. No headers, steps, labels, or additional explanations."
        )

        history_payload.insert(0, {"role": "system", "content": system_instruction})

        # Step 6: Temporary debug log printing the full messages payload
        print(f"PAYLOAD MESSAGES:\n{json.dumps(history_payload, indent=2)}")
        print(f"SYSTEM INSTRUCTION:\n{system_instruction}")

        fallback_questions = {
            "primary_complaint": (
                "No worries — could you describe what you're experiencing in your own words? For example: pain, itching, hair thinning, fatigue, etc."
                if patient_ctx.clarify_retry else
                "What's the main health issue or primary symptom you're experiencing today?"
            ),
            "duration": f"How many days or weeks has this {patient_ctx.primary_complaint or 'symptom'} been going on?",
            "onset_pattern": f"Did this start suddenly or gradually? Is it constant or does it come and go?",
            "associated_symptoms": f"Are you experiencing any other symptoms along with this — e.g. fever, fatigue, pain, nausea, cough?",
            "severity": f"On a scale of 1–10, how severe would you say this is?",
            "known_conditions": f"Do you have any pre-existing medical conditions (such as diabetes, BP, asthma, thyroid) that relate to this?",
            "medications": f"Are you currently taking any prescription medications or supplements to manage this?",
            "allergies": "Do you have any known allergies to drugs, food, or environmental triggers?",
            "recent_exposure": f"Have you had any recent travel, contact with a sick person, new foods, or environmental triggers related to this?",
            "safety_red_flags": f"Red Flag Safety Check: Along with the symptoms, are you experiencing difficulty breathing, chest pain, severe bleeding, confusion, or fainting?"
        }
        fallback_q = fallback_questions.get(active_field, "Could you tell me more about your symptoms?")

        provider = get_llm_provider()
        try:
            full_followup = await provider.generate_response(
                messages=history_payload,
                context=fallback_q,
                intent="intake_followup"
            )
            if not full_followup or len(full_followup.strip()) < 5:
                full_followup = fallback_q
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
    
    bot_reply_content += "\n\nWould you like me to book an appointment with a specialist for this?"
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

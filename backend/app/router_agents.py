"""
Multi-Agent REST API Router for Hospital Appointment & Patient Guidance System.
Exposes endpoints for:
1. Triage Agent (/api/agents/triage/assess)
2. Booking Agent (/api/agents/booking/slots, reserve, confirm)
3. Report Agent (/api/agents/reports/soap, approve)
4. Care Agent (/api/agents/care/reminders, toggle)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.agents.triage_agent import run_triage_assessment
from app.agents.booking_agent import (
    get_available_doctors_and_slots,
    reserve_slot_draft,
    confirm_appointment_lock
)
from app.agents.report_agent import generate_soap_draft_report, doctor_review_and_approve_soap
from app.agents.care_agent import (
    generate_care_reminders_from_consultation,
    get_user_care_reminders,
    toggle_care_reminder_status
)

router = APIRouter(prefix="/api/agents", tags=["Multi-Agent System"])

# Schemas
class TriageAssessmentRequest(BaseModel):
    symptoms: str
    patient_context: Optional[Dict[str, Any]] = None

class SlotReserveRequest(BaseModel):
    doctor_id: int
    slot_id: int
    conversation_id: Optional[int] = None

class SlotConfirmRequest(BaseModel):
    appointment_id: int
    slot_id: int

class DoctorSOAPApproveRequest(BaseModel):
    doctor_notes: Optional[str] = None

class CareReminderGenerateRequest(BaseModel):
    medications: Optional[List[Dict[str, str]]] = None

# 1. Triage Agent Endpoint
@router.post("/triage/assess")
def assess_symptoms_triage(req: TriageAssessmentRequest):
    """Executes the 4-step triage assessment protocol."""
    return run_triage_assessment(req.symptoms, req.patient_context or {})

# 2. Booking Agent Endpoints
@router.get("/booking/slots")
def get_slots(department: str = "General Medicine", db: Session = Depends(get_db)):
    """Retrieves live doctors and conflict-free open appointment slots."""
    return get_available_doctors_and_slots(db, department)

@router.post("/booking/reserve")
def reserve_slot(
    req: SlotReserveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Step 1: Holds a provisional draft appointment."""
    try:
        return reserve_slot_draft(db, current_user.id, req.doctor_id, req.slot_id, req.conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/booking/confirm")
def confirm_slot(
    req: SlotConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Step 2: Patient explicitly confirms slot lock."""
    try:
        return confirm_appointment_lock(db, req.appointment_id, current_user.id, req.slot_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. Report Agent Endpoints
@router.get("/reports/soap/{conversation_id}")
def get_soap_note(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates or retrieves structured SOAP note draft for physician review."""
    try:
        return generate_soap_draft_report(db, conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/reports/soap/{report_id}/approve")
def approve_soap_note(
    report_id: int,
    req: DoctorSOAPApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Attending physician reviews and approves the SOAP draft note."""
    try:
        return doctor_review_and_approve_soap(db, report_id, req.doctor_notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 4. Care Agent Endpoints
@router.get("/care/reminders")
def list_care_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists active post-discharge pill and care reminders for the patient."""
    return get_user_care_reminders(db, current_user.id)

@router.post("/care/reminders/generate")
def create_care_reminders(
    req: CareReminderGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates post-consultation medication reminders."""
    return generate_care_reminders_from_consultation(db, current_user.id, req.medications)

@router.post("/care/reminders/{reminder_id}/toggle")
def toggle_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows patient to pause or resume a medication reminder."""
    try:
        return toggle_care_reminder_status(db, reminder_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

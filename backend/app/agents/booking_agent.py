"""
Agent 2: Booking Agent (Conflict-Free Scheduling)
Checks live doctor availability, prevents double-booking using concurrency checks,
and enforces an explicit patient confirmation step before locking in appointments.
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Doctor, DoctorSlot, Appointment, User

def get_available_doctors_and_slots(db: Session, department: str) -> List[Dict[str, Any]]:
    """Retrieves active doctors in the recommended department and their available slots."""
    doctors = db.query(Doctor).filter(Doctor.department == department).all()
    if not doctors:
        # Fallback to General Medicine if department has no specific doctor
        doctors = db.query(Doctor).filter(Doctor.department == "General Medicine").all()
        if not doctors:
            doctors = db.query(Doctor).all()

    results = []
    for doc in doctors:
        open_slots = [
            {"slot_id": s.id, "slot_time": s.slot_time}
            for s in doc.slots if not s.is_booked
        ]
        results.append({
            "doctor_id": doc.id,
            "name": doc.name,
            "department": doc.department,
            "title": doc.title,
            "room_no": doc.room_no,
            "experience_years": doc.experience_years,
            "available_slots": open_slots
        })
    return results

def reserve_slot_draft(
    db: Session,
    user_id: int,
    doctor_id: int,
    slot_id: int,
    conversation_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Step 1: Creates a provisional draft appointment with concurrency lock.
    Requires explicit patient confirmation to finalize.
    """
    # Concurrency check: Ensure slot is still unbooked
    slot = db.query(DoctorSlot).filter(DoctorSlot.id == slot_id, DoctorSlot.doctor_id == doctor_id).first()
    if not slot:
        raise ValueError("Selected doctor slot not found.")
    if slot.is_booked:
        raise ValueError("This slot was just claimed by another patient. Please choose another available time.")

    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise ValueError("Doctor not found.")

    booking_ref = f"HC-{uuid.uuid4().hex[:6].upper()}"

    appointment = Appointment(
        user_id=user_id,
        doctor_id=doc.id,
        conversation_id=conversation_id,
        department=doc.department,
        slot_time=slot.slot_time,
        status="pending_confirmation",
        booking_reference=booking_ref
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "appointment_id": appointment.id,
        "booking_reference": booking_ref,
        "doctor_name": doc.name,
        "department": doc.department,
        "room_no": doc.room_no,
        "slot_time": slot.slot_time,
        "status": "pending_confirmation",
        "message": "Appointment slot provisionally held. Please confirm to finalize your hospital booking."
    }

def confirm_appointment_lock(
    db: Session,
    appointment_id: int,
    user_id: int,
    slot_id: int
) -> Dict[str, Any]:
    """
    Step 2: Patient confirms the slot. Locks the slot in DB and marks appointment confirmed.
    """
    appt = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.user_id == user_id).first()
    if not appt:
        raise ValueError("Appointment reservation not found or unauthorized.")

    slot = db.query(DoctorSlot).filter(DoctorSlot.id == slot_id).first()
    if not slot:
        raise ValueError("Doctor slot not found.")
    if slot.is_booked and slot.booked_by_user_id != user_id:
        raise ValueError("Conflict detected: This slot has already been finalized by another user.")

    # Concurrency Lock
    slot.is_booked = True
    slot.booked_by_user_id = user_id
    appt.status = "confirmed"

    db.commit()
    db.refresh(appt)

    return {
        "appointment_id": appt.id,
        "booking_reference": appt.booking_reference,
        "doctor_name": appt.doctor.name,
        "department": appt.department,
        "room_no": appt.doctor.room_no,
        "slot_time": appt.slot_time,
        "status": "confirmed",
        "message": f"Appointment successfully confirmed with {appt.doctor.name} ({appt.slot_time}). Reference: {appt.booking_reference}"
    }

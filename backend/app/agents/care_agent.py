"""
Agent 4: Care Agent (Discharge-Time Reminders & Follow-up)
Schedules post-consultation medication pill reminders and follow-up alerts,
allowing the patient full control to adjust timing or opt out at any time.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import CareReminder, User

DEFAULT_CARE_PROTOCOLS = [
    {"medication_name": "Levothyroxine", "dosage": "50 mcg", "frequency": "Every morning before breakfast", "reminder_time": "07:30 AM"},
    {"medication_name": "Metformin", "dosage": "500 mg", "frequency": "Twice daily with meals", "reminder_time": "08:30 AM & 08:30 PM"},
    {"medication_name": "Paracetamol", "dosage": "650 mg", "frequency": "As needed every 6 hours for fever", "reminder_time": "12:00 PM"}
]

def generate_care_reminders_from_consultation(
    db: Session,
    user_id: int,
    medications: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, Any]]:
    """Generates initial care and pill reminders after medical consultation."""
    med_list = medications or [DEFAULT_CARE_PROTOCOLS[0]]
    created = []

    for med in med_list:
        reminder = CareReminder(
            user_id=user_id,
            medication_name=med.get("medication_name", "Prescription Med"),
            dosage=med.get("dosage", "1 tablet"),
            frequency=med.get("frequency", "Daily"),
            reminder_time=med.get("reminder_time", "08:00 AM"),
            status="active"
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        created.append({
            "id": reminder.id,
            "medication_name": reminder.medication_name,
            "dosage": reminder.dosage,
            "frequency": reminder.frequency,
            "reminder_time": reminder.reminder_time,
            "status": reminder.status
        })

    return created

def get_user_care_reminders(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Lists all active care reminders for the patient."""
    reminders = db.query(CareReminder).filter(CareReminder.user_id == user_id).all()
    return [
        {
            "id": r.id,
            "medication_name": r.medication_name,
            "dosage": r.dosage,
            "frequency": r.frequency,
            "reminder_time": r.reminder_time,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in reminders
    ]

def toggle_care_reminder_status(db: Session, reminder_id: int, user_id: int) -> Dict[str, Any]:
    """Allows patient to pause, resume, or opt out of a specific reminder."""
    r = db.query(CareReminder).filter(CareReminder.id == reminder_id, CareReminder.user_id == user_id).first()
    if not r:
        raise ValueError("Care reminder not found or unauthorized.")

    r.status = "paused" if r.status == "active" else "active"
    db.commit()
    db.refresh(r)

    return {
        "id": r.id,
        "medication_name": r.medication_name,
        "status": r.status,
        "message": f"Reminder for {r.medication_name} is now {r.status}."
    }

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Conversation, Message, Ticket
from app.schemas import MetricsSummaryResponse, TicketResponse, TicketStatusUpdate
from app.auth import get_admin_user

router = APIRouter(tags=["Admin & Metrics"])

@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    total_convs = db.query(Conversation).count()
    total_msgs = db.query(Message).count()
    
    resolved_convs = db.query(Conversation).filter(Conversation.status == "resolved").count()
    escalated_convs = db.query(Conversation).filter(Conversation.status == "escalated").count()
    open_convs = db.query(Conversation).filter(Conversation.status == "open").count()

    resolution_rate = round((resolved_convs / total_convs * 100.0), 2) if total_convs > 0 else 0.0
    escalation_rate = round((escalated_convs / total_convs * 100.0), 2) if total_convs > 0 else 0.0

    avg_rt = (
        db.query(func.avg(Message.response_time_ms))
        .filter(Message.role == "assistant", Message.response_time_ms.isnot(None))
        .scalar()
    )
    avg_response_time_ms = round(float(avg_rt), 1) if avg_rt is not None else 0.0

    total_rated = db.query(Message).filter(Message.feedback.isnot(None)).count()
    positive_rated = db.query(Message).filter(Message.feedback == 1).count()
    satisfaction_score = round((positive_rated / total_rated * 100.0), 2) if total_rated > 0 else 100.0

    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()

    return MetricsSummaryResponse(
        total_conversations=total_convs,
        total_messages=total_msgs,
        resolved_conversations=resolved_convs,
        escalated_conversations=escalated_convs,
        open_conversations=open_convs,
        resolution_rate=resolution_rate,
        escalation_rate=escalation_rate,
        avg_response_time_ms=avg_response_time_ms,
        satisfaction_score=satisfaction_score,
        open_tickets_count=open_tickets
    )

@router.get("/tickets", response_model=List[TicketResponse])
def get_tickets(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    results = []
    for t in tickets:
        t_dict = TicketResponse.model_validate(t)
        t_dict.user_email = t.user.email if t.user else "Unknown"
        results.append(t_dict)
    return results

@router.patch("/tickets/{id}/status", response_model=TicketResponse)
def update_ticket_status(
    id: int,
    body: TicketStatusUpdate,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    if body.status not in ["open", "in_progress", "closed"]:
        raise HTTPException(status_code=400, detail="Invalid status value. Must be 'open', 'in_progress', or 'closed'")

    ticket = db.query(Ticket).filter(Ticket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = body.status
    db.commit()
    db.refresh(ticket)

    res = TicketResponse.model_validate(ticket)
    res.user_email = ticket.user.email if ticket.user else "Unknown"
    return res

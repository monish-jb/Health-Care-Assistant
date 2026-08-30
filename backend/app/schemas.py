import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# Auth Schemas
class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Patient Context Schemas
class PatientContextResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    age: Optional[int] = None
    sex: Optional[str] = None
    primary_complaint: Optional[str] = None
    symptoms: List[str] = []
    duration: Optional[str] = None
    onset_pattern: Optional[str] = None
    severity: Optional[str] = None
    medications: List[str] = []
    known_conditions: List[str] = []
    allergies: Optional[str] = None
    recent_exposure: Optional[str] = None
    lab_results: dict = {}
    raw_notes: List[str] = []
    intake_completed: bool = False
    current_step: int = 1
    clarify_retry: bool = False
    booking_state: Optional[str] = None
    selected_doctor_id: Optional[int] = None
    selected_slot_time: Optional[str] = None
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# Chat Schemas
class MessageCreateRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str

class CitationItem(BaseModel):
    id: int
    title: str
    source_type: str  # "Clinical Guideline", "Research Paper", "Health Authority", "Clinical Reference"
    year: Optional[str] = None
    section: Optional[str] = None
    passage: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    rag_grounded: bool = False
    retrieval_score: Optional[float] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    response_time_ms: Optional[int] = None
    
    # Health Companion Specific
    triage_level: Optional[str] = "GENERAL_INFO"
    followup_options: Optional[List[str]] = None
    confidence_level: Optional[str] = None
    confidence_details: Optional[dict] = None
    citations: Optional[List[CitationItem]] = None

    feedback: Optional[int] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageResponse] = []
    patient_context: Optional[PatientContextResponse] = None

    class Config:
        from_attributes = True

class ChatMessageResult(BaseModel):
    conversation_id: int
    user_message: MessageResponse
    bot_message: MessageResponse
    patient_context: Optional[PatientContextResponse] = None
    triage_assessment: Optional[dict] = None

class FeedbackRequest(BaseModel):
    message_id: int
    feedback: int  # 1 or -1

# KB Schemas
class KBDocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    chunk_count: int
    source_type: Optional[str] = "Clinical Reference"
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Ticket Schemas
class TicketResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    user_email: Optional[str] = None
    intent: str
    priority: str
    reason: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class TicketStatusUpdate(BaseModel):
    status: str  # "open" | "in_progress" | "closed"

# Metrics Schema
class MetricsSummaryResponse(BaseModel):
    total_conversations: int
    total_messages: int
    resolved_conversations: int
    escalated_conversations: int
    open_conversations: int
    resolution_rate: float
    escalation_rate: float
    avg_response_time_ms: float
    satisfaction_score: float
    open_tickets_count: int

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for Google Auth users
    role = Column(String, default="customer", nullable=False)  # "admin" | "customer"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("KBDocument", back_populates="uploaded_by")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="Healthcare Consultation")
    status = Column(String, default="open", nullable=False)  # "open" | "resolved" | "escalated"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    tickets = relationship("Ticket", back_populates="conversation", cascade="all, delete-orphan")
    patient_context = relationship("PatientContext", uselist=False, back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    
    # Routing & reasoning metrics
    intent = Column(String, nullable=True)
    intent_confidence = Column(Float, nullable=True)
    rag_grounded = Column(Boolean, default=False)
    retrieval_score = Column(Float, nullable=True)
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(String, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Health Companion specific fields
    triage_level = Column(String, default="GENERAL_INFO")  # "EMERGENCY" | "URGENT_EVALUATION" | "ROUTINE_CONSULTATION" | "GENERAL_INFO"
    followup_options = Column(Text, nullable=True)  # JSON list string of quick-answer option chips
    confidence_level = Column(String, nullable=True)  # "HIGH" | "MEDIUM" | "LOW"
    confidence_details = Column(Text, nullable=True)  # JSON details object
    citations = Column(Text, nullable=True)  # JSON list string of citations

    # Feedback (-1 = thumbs down, 1 = thumbs up, None = unrated)
    feedback = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

class PatientContext(Base):
    __tablename__ = "patient_contexts"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    primary_complaint = Column(String, nullable=True)
    symptoms = Column(Text, default="[]")  # JSON string array
    duration = Column(String, nullable=True)
    onset_pattern = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    medications = Column(Text, default="[]")  # JSON string array
    known_conditions = Column(Text, default="[]")  # JSON string array
    allergies = Column(String, nullable=True)
    recent_exposure = Column(String, nullable=True)
    lab_results = Column(Text, default="{}")  # JSON string object
    raw_notes = Column(Text, default="[]")  # JSON string array for unextracted context notes
    
    intake_completed = Column(Boolean, default=False)
    current_step = Column(Integer, default=1)
    clarify_retry = Column(Boolean, default=False)
    booking_state = Column(String, nullable=True)  # "PROMPTED" | "SELECTING_SLOT" | "CONFIRMING" | "COMPLETED"
    selected_doctor_id = Column(Integer, nullable=True)
    selected_slot_time = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="patient_context")

class KBDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    source_type = Column(String, default="Clinical Reference")  # "Clinical Guideline", "Research Paper", "Health Authority", "Clinical Reference"
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    uploaded_by = relationship("User", back_populates="documents")
    chunks = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")

class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_name = Column(String, nullable=True)
    content = Column(Text, nullable=False)

    document = relationship("KBDocument", back_populates="chunks")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intent = Column(String, nullable=False)
    priority = Column(String, default="medium")  # "low" | "medium" | "high" | "urgent"
    reason = Column(String, nullable=False)
    status = Column(String, default="open")  # "open" | "in_progress" | "closed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="tickets")
    user = relationship("User", back_populates="tickets")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)  # "Cardiology", "Endocrinology", "Pulmonology", "Gastroenterology", "General Medicine"
    title = Column(String, default="Senior Consultant")
    room_no = Column(String, default="Room 204")
    experience_years = Column(Integer, default=10)
    avatar_url = Column(String, nullable=True)

    slots = relationship("DoctorSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")

class DoctorSlot(Base):
    __tablename__ = "doctor_slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_time = Column(String, nullable=False)  # e.g., "Tomorrow at 10:00 AM", "Tomorrow at 02:30 PM"
    is_booked = Column(Boolean, default=False)
    booked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    doctor = relationship("Doctor", back_populates="slots")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    department = Column(String, nullable=False)
    slot_time = Column(String, nullable=False)
    status = Column(String, default="pending_confirmation")  # "pending_confirmation" | "confirmed" | "completed" | "cancelled"
    booking_reference = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    doctor = relationship("Doctor", back_populates="appointments")
    user = relationship("User")

class SOAPReport(Base):
    __tablename__ = "soap_reports"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    department = Column(String, nullable=False)
    subjective = Column(Text, nullable=False)  # Patient symptoms, history, timeline
    objective = Column(Text, nullable=False)   # Vital signs, lab values, observed metrics
    assessment = Column(Text, nullable=False)  # Differential diagnoses, preliminary rankings
    plan = Column(Text, nullable=False)        # Treatment options, referral, follow-up
    suggested_tests = Column(Text, default="[]")  # JSON list string of recommended preliminary tests
    doctor_reviewed = Column(Boolean, default=False)
    doctor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CareReminder(Base):
    __tablename__ = "care_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, default="Daily")
    reminder_time = Column(String, default="09:00 AM")
    status = Column(String, default="active")  # "active" | "paused" | "completed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

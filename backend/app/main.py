from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import User, Doctor, DoctorSlot
from app.auth import hash_password
from app.router_auth import router as auth_router
from app.router_chat import router as chat_router
from app.router_kb import router as kb_router
from app.router_admin import router as admin_router
from app.router_mobile import router as mobile_router
from app.router_agents import router as agents_router

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

def seed_doctors(db):
    INITIAL_DOCTORS = [
        {"name": "Dr. Sarah Jenkins, MD", "department": "Cardiology", "title": "Senior Cardiologist", "room_no": "Room 302", "experience_years": 14, "city": "New York"},
        {"name": "Dr. Marcus Vance, MD", "department": "Endocrinology", "title": "Endocrine Specialist", "room_no": "Room 214", "experience_years": 12, "city": "Boston"},
        {"name": "Dr. Elena Rostova, MD", "department": "Pulmonology", "title": "Pulmonology Consultant", "room_no": "Room 108", "experience_years": 15, "city": "Bangalore"},
        {"name": "Dr. David Patel, MD", "department": "Gastroenterology", "title": "Gastroenterologist", "room_no": "Room 405", "experience_years": 11, "city": "Bangalore"},
        {"name": "Dr. Emily Hayes, MD", "department": "General Medicine", "title": "Chief Medical Officer", "room_no": "Room 101", "experience_years": 18, "city": "New York"},
        {"name": "Dr. Clara Song, MD", "department": "Dermatology", "title": "Dermatologist Consultant", "room_no": "Room 303", "experience_years": 10, "city": "New York"},
        {"name": "Dr. Monish JB, MD", "department": "Dermatology", "title": "Senior Dermatologist", "room_no": "Room 304", "experience_years": 12, "city": "Bangalore"},
        {"name": "Dr. Arjun Prasad, MD", "department": "Cardiology", "title": "Chief Cardiologist", "room_no": "Room 305", "experience_years": 15, "city": "Bangalore"},
        {"name": "Dr. Priya Nair, MD", "department": "Endocrinology", "title": "Endocrinologist", "room_no": "Room 306", "experience_years": 11, "city": "Chennai"}
    ]

    SLOT_TIMES = [
        "Tomorrow at 09:30 AM",
        "Tomorrow at 11:00 AM",
        "Tomorrow at 02:30 PM",
        "Tomorrow at 04:00 PM"
    ]

    for doc_data in INITIAL_DOCTORS:
        existing = db.query(Doctor).filter(Doctor.name == doc_data["name"]).first()
        if not existing:
            new_doc = Doctor(**doc_data)
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)

            for s_time in SLOT_TIMES:
                slot = DoctorSlot(
                    doctor_id=new_doc.id,
                    slot_time=s_time,
                    is_booked=False
                )
                db.add(slot)
            db.commit()

def seed_admin():
    db = SessionLocal()
    try:
        admin_email = "admin@healthnavigator.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            hashed_pwd = hash_password("AdminPassword123!")
            new_admin = User(
                email=admin_email,
                hashed_password=hashed_pwd,
                role="admin"
            )
            db.add(new_admin)

        patient_email = "patient@healthnavigator.com"
        patient = db.query(User).filter(User.email == patient_email).first()
        if not patient:
            hashed_pwd_pat = hash_password("PatientPassword123!")
            new_patient = User(
                email=patient_email,
                hashed_password=hashed_pwd_pat,
                role="user"
            )
            db.add(new_patient)

        seed_doctors(db)
        db.commit()
        print("Successfully seeded default admin, patient, and department doctors.")
    except Exception as e:
        print(f"Error seeding users: {e}")
    finally:
        db.close()

seed_admin()

try:
    from seed_medical_kb import seed_medical_knowledge_base
    seed_medical_knowledge_base()
except Exception as e:
        print(f"Medical KB auto-seed notice: {e}")

app = FastAPI(
    title="Healthcare Knowledge Navigator API",
    description="Conversational Health Companion with Multi-Agent Triage, Patient Context, Evidence RAG, Citations, and Confidence Scoring",
    version="2.0.0"
)

# Configure CORS for local dev frontend & production hosts
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(kb_router)
app.include_router(admin_router)
app.include_router(mobile_router)
app.include_router(agents_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Healthcare Knowledge Navigator Backend Engine",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8008, reload=True)

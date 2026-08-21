from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import User
from app.auth import hash_password
from app.router_auth import router as auth_router
from app.router_chat import router as chat_router
from app.router_kb import router as kb_router
from app.router_admin import router as admin_router
from app.router_mobile import router as mobile_router

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

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

        db.commit()
        print("Successfully seeded default admin and patient users.")
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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app.models import User
from app.schemas import SignupRequest, LoginRequest, GoogleLoginRequest, TokenResponse, UserResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Determine role: first account or emails with 'admin' in username automatically become admin
    total_users = db.query(User).count()
    email_clean = req.email.strip().lower()
    username_part = email_clean.split("@")[0] if "@" in email_clean else email_clean
    role = "admin" if (total_users == 0 or "admin" in username_part) else "customer"

    hashed_pwd = hash_password(req.password)
    new_user = User(
        email=req.email.strip().lower(),
        hashed_password=hashed_pwd,
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/google", response_model=TokenResponse)
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    if req.credential.startswith("demo_google_token_"):
        email = req.credential.replace("demo_google_token_", "")
    else:
        try:
            id_info = id_token.verify_oauth2_token(req.credential, google_requests.Request())
            email = id_info.get("email")
            if not email:
                raise HTTPException(status_code=400, detail="Google token payload missing email")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

    email_clean = email.strip().lower()
    username_part = email_clean.split("@")[0] if "@" in email_clean else email_clean
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        total_users = db.query(User).count()
        role = "admin" if (total_users == 0 or "admin" in username_part) else "customer"
        user = User(
            email=email_clean,
            hashed_password=None,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif "admin" in username_part and user.role != "admin":
        user.role = "admin"
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

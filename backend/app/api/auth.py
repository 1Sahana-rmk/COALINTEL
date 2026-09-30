from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.rbac import get_current_user
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse


router = APIRouter(tags=["Authentication"])


@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    OAuth2 Username & Password Authentication Endpoint.
    Verifies bcrypt password hash against PostgreSQL users table, issues JWT bearer token,
    and writes event to immutable audit log.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        # Log failed login attempt
        failed_audit = AuditLog(
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            details=f"Failed login attempt for username: '{payload.username}'"
        )
        db.add(failed_audit)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT Bearer Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.username,
        role=user.role,
        subsidiary=user.subsidiary or "CIL HQ",
        expires_delta=access_token_expires
    )

    # Log successful login event
    success_audit = AuditLog(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        details=f"User '{user.username}' (Role: {user.role}, Subsidiary: {user.subsidiary}) authenticated successfully."
    )
    db.add(success_audit)
    db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db)
):
    """
    Public User Registration Endpoint.
    Enforces safe non-privileged role ('Analyst'), hashes password with bcrypt,
    checks for unique username/email, writes audit log, and issues JWT bearer token.
    """
    cleaned_username = payload.username.strip() if payload.username else ""
    if not cleaned_username or len(cleaned_username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters long."
        )
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    # Check for existing username
    existing_user = db.query(User).filter(User.username == cleaned_username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered."
        )

    # Check for existing email if provided
    cleaned_email = payload.email.strip() if payload.email and payload.email.strip() else None
    if cleaned_email:
        existing_email = db.query(User).filter(User.email == cleaned_email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered."
            )

    # Hash password safely
    hashed_pwd = get_password_hash(payload.password)

    # Create new user with safe non-privileged role ('Analyst')
    new_user = User(
        username=cleaned_username,
        hashed_password=hashed_pwd,
        role="Analyst",  # Enforce non-privileged role for public registration
        subsidiary=payload.subsidiary.strip() if payload.subsidiary and payload.subsidiary.strip() else "CIL HQ",
        full_name=payload.full_name.strip() if payload.full_name and payload.full_name.strip() else None,
        email=cleaned_email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record registration audit log
    audit_entry = AuditLog(
        user_id=new_user.id,
        action="USER_SIGNUP",
        details=f"New user registered: '{new_user.username}' (Role: {new_user.role}, Subsidiary: {new_user.subsidiary})"
    )
    db.add(audit_entry)
    db.commit()

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=new_user.username,
        role=new_user.role,
        subsidiary=new_user.subsidiary or "CIL HQ",
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile information for currently authenticated user."""
    return UserResponse.model_validate(current_user)


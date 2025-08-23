"""
Authentication API Routes
Handles user registration, login, and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from datetime import datetime

from ..db import SessionLocal
from .. import models
from ..auth import (
    auth_manager, authenticate_user, create_user_tokens, 
    get_current_user, get_admin_user
)

router = APIRouter(tags=["authentication"])
security = HTTPBearer()

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "citizen"  # Default role

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    trust_score: float
    created_at: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=TokenResponse)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role
    valid_roles = ["citizen", "inspector", "admin"]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )
    
    # Create new user
    user = models.User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=auth_manager.hash_password(user_data.password),
        role=user_data.role,
        trust_score=1.0,  # Default trust score
        created_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate tokens
    tokens = create_user_tokens(user)
    
    return {
        **tokens,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "trust_score": user.trust_score
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return tokens"""
    
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Generate tokens
    tokens = create_user_tokens(user)
    
    return {
        **tokens,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "trust_score": user.trust_score
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        trust_score=current_user.trust_score,
        created_at=current_user.created_at
    )

@router.post("/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    
    try:
        payload = auth_manager.verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Generate new access token
        token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role
        }
        new_access_token = auth_manager.create_access_token(token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0, 
    limit: int = 100,
    admin_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            trust_score=user.trust_score,
            created_at=user.created_at
        )
        for user in users
    ]

@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: str,
    admin_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    
    valid_roles = ["citizen", "inspector", "admin"]
    if new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = new_role
    db.commit()
    
    return {"message": f"User role updated to {new_role}"}

# Demo user creation endpoint (remove in production)
@router.post("/create-demo-users")
async def create_demo_users(db: Session = Depends(get_db)):
    """Create demo users for testing (remove in production)"""
    
    demo_users = [
        {
            "email": "admin@billboardsentinel.com",
            "password": "admin123",
            "full_name": "System Administrator",
            "role": "admin"
        },
        {
            "email": "inspector@chandigarh.gov.in",
            "password": "inspector123", 
            "full_name": "Municipal Inspector",
            "role": "inspector"
        },
        {
            "email": "citizen@example.com",
            "password": "citizen123",
            "full_name": "John Citizen",
            "role": "citizen"
        }
    ]
    
    created_users = []
    for user_data in demo_users:
        # Check if user already exists
        existing = db.query(models.User).filter(models.User.email == user_data["email"]).first()
        if existing:
            continue
            
        user = models.User(
            id=str(uuid.uuid4()),
            email=user_data["email"],
            full_name=user_data["full_name"],
            password_hash=auth_manager.hash_password(user_data["password"]),
            role=user_data["role"],
            trust_score=1.0,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        created_users.append(user_data["email"])
    
    db.commit()
    
    return {
        "message": f"Created {len(created_users)} demo users",
        "users": created_users
    }

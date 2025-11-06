# backend/routers/users.py

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
# Import ONLY the necessary CRUD functions
from crud import get_user_by_email, create_user 
from schemas import User, UserCreate, Token # Removed TokenData as it's not used here
from security import get_password_hash, verify_password, create_access_token
# Note: Removed "from models import user as user_models" and "from config import settings" 
# as they are not needed directly in the router now that CRUD and Security handle them.

router = APIRouter(prefix="/users", tags=["Users & Auth"])

# --- Registration Endpoint (Uses crud.create_user) ---
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Registers a new user and hashes the password."""
    # 1. Check for existing user using CRUD
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Hash password using security
    hashed_password = get_password_hash(user.password)
    
    # 3. Create user using CRUD (passing the hashed password)
    return create_user(db, user=user, hashed_password=hashed_password)

# --- Login/Token Endpoint (Uses crud.get_user_by_email and security functions) ---
@router.post("/token", response_model=Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    """Authenticates the user and returns a JWT access token."""
    # 1. Retrieve user using CRUD
    user = get_user_by_email(db, email=form_data.username)
    
    # 2. Verify user and password using security
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Create the JWT using security
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
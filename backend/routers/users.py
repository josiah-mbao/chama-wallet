# backend/routers/users.py

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from backend.database import get_db
# Import ONLY the necessary CRUD functions
from backend.crud import get_user_by_email, create_user
from backend.schemas import User, UserCreate, Token  # Removed TokenData as it's not used here
from backend.security import get_password_hash, verify_password, create_access_token, get_current_user
from backend.exceptions import DuplicateResourceError, AuthenticationError
# Note: Removed "from models import user as user_models" and "from config import settings"
# as they are not needed directly in the router now that CRUD and Security handle them.

router = APIRouter(tags=["Users & Auth"])

# --- Registration Endpoint (Uses crud.create_user) ---
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Registers a new user and hashes the password."""
    # 1. Check for existing user using CRUD
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise DuplicateResourceError("User", f"Email {user.email} already registered")

    return create_user(db, user=user)


# --- Login/Token Endpoint (Uses crud.get_user_by_email and security functions) ---
@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    """Authenticates the user and returns a JWT access token."""
    # 1. Retrieve user using CRUD
    user = get_user_by_email(db, email=form_data.username)

    # 2. Verify user and password using security
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError("Incorrect username or password")

    # 3. Create the JWT using security
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# Example protected endpoint (return current user's public schema)
@router.get("/me", response_model=User)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

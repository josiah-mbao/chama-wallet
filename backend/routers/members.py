# backend/routers/members.py

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db

# Import CRUD functions (including new contribution function)
from crud import get_members, create_member, create_contribution
# Import Pydantic schemas required for request/response bodies
from schemas import Member, MemberCreate, Contribution, ContributionCreate 
from security import get_current_user_email # For JWT Auth Dependency

router = APIRouter(
    prefix="/members", 
    tags=["Members"],
    # Protect all routes in this router with JWT authentication
    dependencies=[Depends(get_current_user_email)] 
)

# --- Member Endpoints ---

# 1. Get All Members (Uses crud.get_members)
@router.get("/", response_model=List[Member])
def read_members_endpoint(db: Annotated[Session, Depends(get_db)]):
    """Retrieves a list of all members."""
    return get_members(db)

# 2. Create a Member (Uses crud.create_member)
@router.post("/", response_model=Member, status_code=status.HTTP_201_CREATED)
def add_member(member: MemberCreate, db: Annotated[Session, Depends(get_db)]):
    """Creates a new member account."""
    # Check for existing member (optional, but good practice)
    # The users router handles primary auth email check, but a member check here is possible too.
    return create_member(db, member)

# --- Contribution Endpoints (Assuming you want to keep them here for now) ---

@router.post("/contributions", response_model=Contribution, status_code=status.HTTP_201_CREATED)
def add_contribution(contribution: ContributionCreate, db: Annotated[Session, Depends(get_db)]):
    """Records a new contribution for a member."""
    return create_contribution(db, contribution)
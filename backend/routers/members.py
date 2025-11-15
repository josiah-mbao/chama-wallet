# backend/routers/members.py

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import get_members, create_member, create_contribution
from backend.schemas import Membership, Contribution, ContributionCreate
from backend.security import get_current_user
from backend.models.user import User  # Needed to look up user by email

router = APIRouter(
    prefix="/members",
    tags=["Members"],
)

# --- Get all members of a Chama ---
@router.get("/{chama_id}", response_model=List[Membership])
def read_members(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user_email: str = Depends(get_current_user)
):
    """
    List all members in a specific Chama.
    Requires authentication and membership check.
    """
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Optional: enforce that only members can list members
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.chama_id == chama_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this Chama")
    
    return get_members(db, chama_id=chama_id)

# --- Add the current user to a Chama ---
@router.post("/{chama_id}", response_model=Membership, status_code=status.HTTP_201_CREATED)
def join_chama(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user_email: str = Depends(get_current_user)
):
    """
    Add the current user to the Chama as a 'member'.
    """
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent duplicate memberships
    existing = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.chama_id == chama_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    
    return create_member(db, user.id, chama_id, role="member")

# --- Record a contribution ---
@router.post("/{chama_id}/contributions", response_model=Contribution, status_code=status.HTTP_201_CREATED)
def add_contribution(
    chama_id: int,
    contribution: ContributionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user_email: str = Depends(get_current_user)
):
    """
    Record a new contribution for the current user in a Chama.
    Requires membership check.
    """
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.chama_id == chama_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of this Chama")
    
    return create_contribution(db, user.id, chama_id, contribution.amount)

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import get_members, create_member, create_contribution
from backend.schemas import Membership, Contribution, ContributionCreate
from backend.security import get_current_user, require_role
from backend.models.user import User, UserRole

router = APIRouter(
    prefix="/members",
    tags=["Members"],
)

# --- Get all members of a Chama ---
@router.get("/{chama_id}", response_model=List[Membership])
def read_members(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(require_role(UserRole.owner, UserRole.treasurer, UserRole.member))
):
    """
    List all members in a specific Chama.
    Only members can list members.
    """
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
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
    current_user: User = Depends(require_role(UserRole.owner, UserRole.treasurer, UserRole.member))
):
    """
    Add the current user to the Chama as a 'member'.
    """
    # Prevent duplicate memberships
    existing = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.chama_id == chama_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    
    return create_member(db, current_user.id, chama_id, role="member")


# --- Record a contribution ---
@router.post("/{chama_id}/contributions", response_model=Contribution, status_code=status.HTTP_201_CREATED)
def add_contribution(
    chama_id: int,
    contribution: ContributionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(require_role(UserRole.owner, UserRole.treasurer))
):
    """
    Record a new contribution for the current user in a Chama.
    Only treasurers or owners can add contributions.
    """
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.chama_id == chama_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of this Chama")
    
    return create_contribution(db, current_user.id, chama_id, contribution.amount)


@router.post("/{chama_id}/add-member")
def add_member(
    chama_id: int,
    member_email: str,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(chama_id, [MembershipRole.owner]))
):
    # Only owner can reach here
    return create_member(db, chama_id, member_email)


@router.post("/{chama_id}/add-contribution")
def add_contribution(
    chama_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_role(chama_id, [MembershipRole.owner, MembershipRole.treasurer]))
):
    return create_contribution(db, chama_id, membership.user_id, contribution)

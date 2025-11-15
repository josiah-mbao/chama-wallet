from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import get_members, create_member, create_contribution
from backend.schemas import Membership, Contribution, ContributionCreate
from backend.security import get_current_user, require_chama_role
from backend.models.user import User
from backend.models.membership import MembershipRole

router = APIRouter(
    prefix="/members",
    tags=["Members"],
)

# --- Helper to bind allowed roles at runtime ---
def require_chama_role_runtime(allowed_roles: list[MembershipRole]):
    """
    Returns a dependency function that resolves the current user's membership
    with the given allowed_roles in the Chama identified by the path param `chama_id`.
    """
    def dependency(
        chama_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        return require_chama_role(chama_id, allowed_roles)(current_user=current_user, db=db)
    return dependency


# --- Get all members of a Chama ---
@router.get("/{chama_id}", response_model=List[Membership])
def read_members(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    membership: Membership = Depends(require_chama_role_runtime([
        MembershipRole.owner,
        MembershipRole.treasurer,
        MembershipRole.member
    ]))
):
    """
    List all members in a specific Chama.
    Only members can list members.
    """
    return get_members(db, chama_id=chama_id)


# --- Add the current user to a Chama ---
@router.post("/{chama_id}", response_model=Membership, status_code=status.HTTP_201_CREATED)
def join_chama(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Add the current user to the Chama as a 'member'.
    """
    existing = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.chama_id == chama_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    
    return create_member(db, current_user.id, chama_id, role="member")


# --- Record a contribution (Owner/Treasurer) ---
@router.post("/{chama_id}/contributions", response_model=Contribution, status_code=status.HTTP_201_CREATED)
def add_contribution(
    chama_id: int,
    contribution: ContributionCreate,
    db: Annotated[Session, Depends(get_db)],
    membership: Membership = Depends(require_chama_role_runtime([
        MembershipRole.owner,
        MembershipRole.treasurer
    ]))
):
    """
    Record a new contribution for the current user in a Chama.
    Only treasurers or owners can add contributions.
    """
    return create_contribution(db, membership.user_id, chama_id, contribution.amount)


# --- Owner-only: Add member ---
@router.post("/{chama_id}/add-member")
def add_member(
    chama_id: int,
    member_email: str,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_chama_role_runtime([MembershipRole.owner]))
):
    """
    Only owner can add another member to the Chama.
    """
    return create_member(db, chama_id, member_email)


# --- Owner/Treasurer-only: Add contribution for another user ---
@router.post("/{chama_id}/add-contribution")
def add_contribution_endpoint(
    chama_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_chama_role_runtime([
        MembershipRole.owner,
        MembershipRole.treasurer
    ]))
):
    """
    Only owner or treasurer can record contributions for other users.
    """
    return create_contribution(db, membership.user_id, chama_id, contribution)
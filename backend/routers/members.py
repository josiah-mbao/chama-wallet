# backend/routers/members.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import get_members, create_member, create_contribution, get_user_by_email
from backend.schemas import Membership, Contribution, ContributionCreate, AddMemberRequest
from backend.security import get_current_user, require_chama_role
from backend.models.user import User
from backend.models.membership import Membership as MembershipModel, MembershipRole
from backend.exceptions import AlreadyMemberError, ResourceNotFoundError

router = APIRouter(
    tags=["Members"],
)

# --- Helper to bind allowed roles at runtime ---
def require_chama_role_runtime(allowed_roles: list[MembershipRole]):
    def dependency(
        chama_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        return require_chama_role(chama_id, allowed_roles)(current_user=current_user, db=db)
    return dependency

# --- Get all members of a Chama ---
@router.get("/members", response_model=List[Membership])
def read_members(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    membership: MembershipModel = Depends(require_chama_role_runtime([
        MembershipRole.owner,
        MembershipRole.treasurer,
        MembershipRole.member
    ]))
):
    """
    List all members in a specific Chama.
    Only members can list members.
    """
    members = get_members(db, chama_id=chama_id)
    # Convert to schema with chama_id
    return [
        Membership(user_id=m.user_id, chama_id=m.chama_id, role=m.role)
        for m in members
    ]

# --- Join a Chama ---
@router.post("/join", response_model=Membership, status_code=status.HTTP_201_CREATED)
def join_chama(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Add the current user to the Chama as a 'member'.
    """
    existing = db.query(MembershipModel).filter(
        MembershipModel.user_id == current_user.id,
        MembershipModel.chama_id == chama_id
    ).first()
    if existing:
        raise AlreadyMemberError()
    
    new_member = create_member(db, user_id=current_user.id, chama_id=chama_id, role="member")
    return Membership(user_id=new_member.user_id, chama_id=new_member.chama_id, role=new_member.role)

# --- Add member (Owner only) ---
@router.post("/members", response_model=Membership, status_code=status.HTTP_201_CREATED)
def add_member_by_owner(
    chama_id: int,
    request_data: AddMemberRequest,
    db: Session = Depends(get_db),
    membership: MembershipModel = Depends(require_chama_role_runtime([MembershipRole.owner]))
):
    """
    Only owner can add another member to the Chama.
    """
    user = get_user_by_email(db, request_data.member_email)
    if not user:
        raise ResourceNotFoundError("User", request_data.member_email)

    # Check if already a member
    existing = db.query(MembershipModel).filter(
        MembershipModel.user_id == user.id,
        MembershipModel.chama_id == chama_id
    ).first()
    if existing:
        raise AlreadyMemberError()

    new_member = create_member(db, user_id=user.id, chama_id=chama_id, role=user.role.value)
    return Membership(user_id=new_member.user_id, chama_id=new_member.chama_id, role=new_member.role)

# --- Add contribution (Treasurer/Owner) ---
@router.post("/contributions", response_model=Contribution, status_code=status.HTTP_201_CREATED)
def add_contribution(
    chama_id: int,
    contribution: ContributionCreate,
    db: Annotated[Session, Depends(get_db)],
    membership: MembershipModel = Depends(require_chama_role_runtime([
        MembershipRole.owner,
        MembershipRole.treasurer
    ]))
):
    """
    Record a new contribution for the current user in a Chama.
    Only treasurers or owners can add contributions.
    """
    new_contribution = create_contribution(db, membership_id=membership.id, amount=contribution.amount)
    return new_contribution

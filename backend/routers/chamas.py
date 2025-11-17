# backend/routers/chamas.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import create_chama, get_user_chamas, get_chama
from backend.schemas import Chama, ChamaCreate, ChamaWithMembers, Membership
from backend.security import get_current_user
from backend.models.user import User
from backend.models.membership import Membership as MembershipModel

router = APIRouter(
    tags=["Chamas"],
)

# --- Create a new Chama ---
@router.post("/", response_model=ChamaWithMembers, status_code=status.HTTP_201_CREATED)
def create_new_chama(
    chama: ChamaCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Chama with the current user as owner.
    """
    new_chama = create_chama(db=db, chama=chama, owner_id=current_user.id)
    # Build memberships for response - include chama_id
    return ChamaWithMembers(
        id=new_chama.id,
        name=new_chama.name,
        description=new_chama.description,
        created_at=new_chama.created_at,
        created_by_user_id=new_chama.created_by_user_id,
        memberships=[Membership(user_id=current_user.id, chama_id=new_chama.id, role="owner")]
    )

# --- Get all Chamas for current user ---
@router.get("/", response_model=List[ChamaWithMembers])
def list_user_chamas(
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    List all Chamas where the current user is a member.
    """
    chamas = get_user_chamas(db, user_id=current_user.id)
    # Attach memberships to each Chama
    chamas_with_members = []
    for chama in chamas:
        memberships = [
            Membership(user_id=m.user_id, chama_id=m.chama_id, role=m.role)
            for m in db.query(MembershipModel).filter(MembershipModel.chama_id == chama.id).all()
        ]
        chamas_with_members.append(
            ChamaWithMembers(
                id=chama.id,
                name=chama.name,
                description=chama.description,
                created_at=chama.created_at,
                created_by_user_id=chama.created_by_user_id,
                memberships=memberships
            )
        )
    return chamas_with_members

# --- Get specific Chama details ---
@router.get("/{chama_id}", response_model=ChamaWithMembers)
def get_chama_details(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific Chama. User must be a member.
    """
    chama = get_chama(db, chama_id=chama_id)
    if not chama:
        raise HTTPException(status_code=404, detail="Chama not found")
    
    # Check if user is a member of this chama
    membership = db.query(MembershipModel).filter(
        MembershipModel.chama_id == chama_id,
        MembershipModel.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this chama")
    
    # Populate memberships for response
    memberships = [
        Membership(user_id=m.user_id, chama_id=m.chama_id, role=m.role)
        for m in db.query(MembershipModel).filter(MembershipModel.chama_id == chama.id).all()
    ]
    return ChamaWithMembers(
        id=chama.id,
        name=chama.name,
        description=chama.description,
        created_at=chama.created_at,
        created_by_user_id=chama.created_by_user_id,
        memberships=memberships
    )

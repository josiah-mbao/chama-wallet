from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import get_current_user, require_role
from backend.schemas import Chama, ChamaCreate, ChamaWithMembers
from backend.models.membership import Membership
from backend.models.user import UserRole, User
import backend.crud as crud

router = APIRouter(
    prefix="/chamas",
    tags=["Chamas"],
)

# --- Create a new Chama (Only owners can create) ---
@router.post("/", response_model=ChamaWithMembers, status_code=status.HTTP_201_CREATED)
def create_chama_endpoint(
    chama: ChamaCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.owner))
):
    """
    Create a new Chama.
    Only owners can create Chamas.
    The creator is automatically added as 'owner'.
    """
    db_chama = crud.create_chama(db=db, chama=chama, creator_id=current_user.id)
    memberships = crud.get_members(db, chama_id=db_chama.id)
    
    return ChamaWithMembers(
        id=db_chama.id,
        name=db_chama.name,
        description=db_chama.description,
        created_at=db_chama.created_at,
        created_by_user_id=db_chama.created_by_user_id,
        memberships=memberships
    )


# --- List Chamas the user is part of ---
@router.get("/", response_model=List[ChamaWithMembers])
def list_user_chamas_endpoint(
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(UserRole.owner, UserRole.treasurer, UserRole.member))
):
    """
    List all Chamas the authenticated user is a member of.
    """
    chamas = crud.get_chamas_for_user(db, user_id=current_user.id)
    
    result = []
    for chama in chamas:
        memberships = crud.get_members(db, chama_id=chama.id)
        result.append(ChamaWithMembers(
            id=chama.id,
            name=chama.name,
            description=chama.description,
            created_at=chama.created_at,
            created_by_user_id=chama.created_by_user_id,
            memberships=memberships
        ))
    return result


# --- Get details of a single Chama ---
@router.get("/{chama_id}", response_model=ChamaWithMembers)
def get_chama_details_endpoint(
    chama_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.owner, UserRole.treasurer, UserRole.member))
):
    """
    Get Chama details by ID.
    Only members can view the Chama.
    """
    chama = crud.get_chama_by_id(db, chama_id=chama_id)
    if chama is None:
        raise HTTPException(status_code=404, detail="Chama not found")
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.chama_id == chama_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of this Chama")
    
    memberships = crud.get_members(db, chama_id=chama_id)
    
    return ChamaWithMembers(
        id=chama.id,
        name=chama.name,
        description=chama.description,
        created_at=chama.created_at,
        created_by_user_id=chama.created_by_user_id,
        memberships=memberships
    )
# Note: Additional endpoints for updating or deleting Chamas can be added similarly,
# with appropriate role checks using the require_role dependency.

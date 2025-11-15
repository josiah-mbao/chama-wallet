# File: backend/routers/chamas.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import get_current_user
from backend.schemas import Chama, ChamaCreate, ChamaWithMembers, User
from backend.models.membership import Membership
import backend.crud

router = APIRouter(
    prefix="/chamas",
    tags=["Chamas"],
    # All routes require authentication
    dependencies=[Depends(get_current_user)]
)

# --- Create a new Chama ---
@router.post("/", response_model=ChamaWithMembers, status_code=status.HTTP_201_CREATED)
def create_chama_endpoint(
    chama: ChamaCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Chama.
    The creator is automatically added as 'admin'.
    Returns the Chama along with its members.
    """
    db_chama = crud.create_chama(db=db, chama=chama, creator_id=current_user.id)
    
    # Fetch memberships for the newly created Chama
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
    current_user: User = Depends(get_current_user)
):
    """
    List all Chamas the authenticated user is a member of.
    Returns Chamas with memberships.
    """
    chamas = crud.get_chamas_for_user(db, user_id=current_user.id)
    
    # Include memberships for each Chama
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
    current_user: User = Depends(get_current_user)
):
    """
    Get Chama details by ID.
    Only members can view the Chama.
    """
    # Check Chama exists
    chama = crud.get_chama_by_id(db, chama_id=chama_id)
    if chama is None:
        raise HTTPException(status_code=404, detail="Chama not found")
    
    # Ensure current_user is a member
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.chama_id == chama_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of this Chama")
    
    # Fetch all memberships for this Chama
    memberships = crud.get_members(db, chama_id=chama_id)
    
    return ChamaWithMembers(
        id=chama.id,
        name=chama.name,
        description=chama.description,
        created_at=chama.created_at,
        created_by_user_id=chama.created_by_user_id,
        memberships=memberships
    )

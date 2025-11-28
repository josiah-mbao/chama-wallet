# backend/crud.py

from sqlalchemy.orm import Session
from typing import Optional, List
from backend.models.user import User
from backend.models.chama import Chama
from backend.models.membership import Membership
from backend.models.contribution import Contribution
from backend.schemas import UserCreate, ChamaCreate
from backend.security import get_password_hash

# --- User CRUD ---

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Chama CRUD ---

def create_chama(db: Session, chama: ChamaCreate, owner_id: int) -> Chama:
    db_chama = Chama(**chama.model_dump(), created_by_user_id=owner_id)
    db.add(db_chama)
    db.commit()
    db.refresh(db_chama)

    # Set up tenant database schema for the new chama
    from backend.schema_management import setup_tenant_database
    setup_tenant_database(db_chama.id)

    # Auto-add owner as member with owner role
    membership = Membership(user_id=owner_id, chama_id=db_chama.id, role="owner")
    db.add(membership)
    db.commit()

    return db_chama

def get_chama_by_id(db: Session, chama_id: int) -> Optional[Chama]:
    return db.query(Chama).filter(Chama.id == chama_id).first()

def get_user_chamas(db: Session, user_id: int) -> List[Chama]:
    return db.query(Chama).join(Membership).filter(Membership.user_id == user_id).all()

def get_chama(db: Session, chama_id: int):
    return get_chama_by_id(db, chama_id)

# --- Membership CRUD ---

def get_members(db: Session, chama_id: Optional[int] = None) -> List[Membership]:
    query = db.query(Membership)
    if chama_id:
        query = query.filter(Membership.chama_id == chama_id)
    return query.all()

def create_member(db: Session, user_id: int, chama_id: int, role: str = "member") -> Membership:
    db_membership = Membership(user_id=user_id, chama_id=chama_id, role=role)
    db.add(db_membership)
    db.commit()
    db.refresh(db_membership)
    return db_membership

# --- Contribution CRUD ---

def create_contribution(db: Session, membership_id: int, amount: float) -> Contribution:
    db_contribution = Contribution(membership_id=membership_id, amount=amount)
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    return db_contribution

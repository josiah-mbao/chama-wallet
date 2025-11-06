# backend/crud.py

from sqlalchemy.orm import Session
from typing import Optional

# Import model modules
from models import member as member_models
from models import user as user_models
from models import contribution as contribution_models

# Import schemas
from schemas import MemberCreate, ContributionCreate, UserCreate 

# --- User CRUD Functions (For Authentication) ---

def get_user_by_email(db: Session, email: str) -> Optional[user_models.User]:
    """Retrieves a User object by email address."""
    return db.query(user_models.User).filter(user_models.User.email == email).first()

def create_user(db: Session, user: UserCreate, hashed_password: str) -> user_models.User:
    """Creates a new User account in the database."""
    db_user = user_models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Member CRUD Functions ---

def get_members(db: Session) -> list[member_models.Member]:
    """Retrieves all members."""
    return db.query(member_models.Member).all()

def create_member(db: Session, member: MemberCreate) -> member_models.Member:
    """Creates a new member."""
    db_member = member_models.Member(name=member.name, email=member.email)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


# --- Contribution CRUD Functions ---

def create_contribution(db: Session, contribution: ContributionCreate) -> contribution_models.Contribution:
    """Creates a new contribution."""
    db_contribution = contribution_models.Contribution(**contribution.model_dump())
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    return db_contribution
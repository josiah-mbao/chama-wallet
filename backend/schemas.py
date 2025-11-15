# backend/schemas.py

from pydantic import BaseModel, ConfigDict, EmailStr
from backend.models.user import UserRole
from typing import List, Optional
from datetime import datetime

# --- JWT Utility Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.member

class User(UserBase):
    id: int
    is_active: bool = True
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

# --- Chama Schemas ---
class ChamaBase(BaseModel):
    name: str
    description: Optional[str] = None

class ChamaCreate(ChamaBase):
    pass  # JWT provides creator_id

class Chama(ChamaBase):
    id: int
    created_at: datetime
    created_by_user_id: int
    model_config = ConfigDict(from_attributes=True)

# Extended Chama for listing with members
class Membership(BaseModel):
    user_id: int
    role: str
    model_config = ConfigDict(from_attributes=True)

class ChamaWithMembers(Chama):
    memberships: List[Membership] = []

# --- Contribution Schemas ---
class ContributionBase(BaseModel):
    amount: float

class ContributionCreate(ContributionBase):
    pass  # user_id and chama_id derived from JWT and route

class Contribution(ContributionBase):
    id: int
    created_at: datetime
    user_id: int
    chama_id: int
    model_config = ConfigDict(from_attributes=True)

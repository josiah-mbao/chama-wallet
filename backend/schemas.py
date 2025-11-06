# backend/schemas.py

from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- Contribution Schemas ---
class ContributionBase(BaseModel):
    amount: float

class ContributionCreate(ContributionBase):
    member_id: int

class Contribution(ContributionBase):
    id: int
    member_id: int

    model_config = ConfigDict(from_attributes=True)

# --- Member Schemas ---
class MemberBase(BaseModel):
    name: str
    email: str

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    id: int
    contributions: List[Contribution] = []

    model_config = ConfigDict(from_attributes=True)

# --- User Schemas ---
class UserCreate(BaseModel):
    email: str
    password: str

class User(BaseModel):
    email: str
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# --- Token Schemas (Required for JWT) ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
from pydantic import BaseModel
from typing import List

class ContributionBase(BaseModel):
    amount: float

class ContributionCreate(ContributionBase):
    member_id: int

class Contribution(ContributionBase):
    id: int
    member_id: int

    class Config:
        orm_mode = True

class MemberBase(BaseModel):
    name: str
    email: str

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    id: int
    contributions: List[Contribtion] = []

    class Config:
        orm_mode = True
